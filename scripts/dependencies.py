#!/usr/bin/env python3
"""Refresh reviewed build inputs. Network access is only needed for --update."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / 'dependencies.lock.json'

def sync_base_defaults(lock):
    for image in ('keycloak', 'oauth2-proxy'):
        path = ROOT / ('Dockerfile.' + image)
        source = path.read_text()
        for name, ref in lock['bases'].items():
            source = re.sub(r'^ARG ' + name.upper() + r'_IMAGE(?:=[^\n]*)?$',
                            lambda match: f'ARG {name.upper()}_IMAGE={ref}', source, flags=re.M)
        path.write_text(source)

def fetch(url):
    headers = {'User-Agent': 'ourimageshardened', 'Accept': 'application/vnd.github+json'}
    if url.startswith('https://api.github.com/') and os.getenv('GH_TOKEN'):
        headers['Authorization'] = 'Bearer ' + os.environ['GH_TOKEN']
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=120) as response:
        return response.read()

def api(path):
    return json.loads(fetch('https://api.github.com/' + path))

def stable(repo):
    release = api(f'repos/{repo}/releases/latest')
    tag = release['tag_name']
    if release['prerelease'] or release['draft'] or not re.fullmatch(r'v?\d+\.\d+\.\d+', tag):
        raise ValueError(f'Not a stable semantic version: {tag}')
    return release

def semver(version):
    return tuple(int(part) for part in version.lstrip('v').split('.'))

def is_newer(candidate, current):
    # Upstream sources (a repo's "latest" release, a dependency version pinned in someone
    # else's pom.xml, ...) can point at something no newer than, or older than, what we
    # already have locked. Never let that overwrite a pinned version as a "downgrade".
    return semver(candidate) > semver(current)

def digest_image(ref):
    result = subprocess.check_output(['docker', 'buildx', 'imagetools', 'inspect', ref,
                                      '--format', '{{.Manifest.Digest}}'], text=True).strip()
    if not re.fullmatch(r'sha256:[0-9a-f]{64}', result):
        raise ValueError(f'Invalid image digest for {ref}')
    return ref + '@' + result

def osv_affected(module, version):
    body = json.dumps({'version': version, 'package': {'name': module, 'ecosystem': 'Go'}}).encode()
    request = urllib.request.Request('https://api.osv.dev/v1/query', data=body,
                                     headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=30) as response:
        return bool(json.loads(response.read()).get('vulns'))

def latest_go_module(module):
    # "@latest" can point at an abandoned release line the maintainers chose not to
    # patch (e.g. grpc-go skipped fixing 1.84.x and told users to move to 1.85+), so
    # walk stable versions newest-first and skip any OSV still flags as vulnerable.
    versions = [v for v in fetch(f'https://proxy.golang.org/{module}/@v/list').decode().split()
               if re.fullmatch(r'v\d+\.\d+\.\d+', v)]
    versions.sort(key=lambda v: tuple(int(part) for part in v[1:].split('.')), reverse=True)
    for version in versions:
        if not osv_affected(module, version):
            return version
    raise ValueError(f'No unaffected stable version found for {module}')

def update():
    lock = json.loads(LOCK.read_text())
    lock['go_security_updates']['grpc'] = latest_go_module('google.golang.org/grpc')
    release = stable('oauth2-proxy/oauth2-proxy')
    tag = release['tag_name']
    if is_newer(tag, lock['oauth2_proxy']['version']):
        commit = api(f'repos/oauth2-proxy/oauth2-proxy/commits/{tag}')['sha']
        url = f'https://codeload.github.com/oauth2-proxy/oauth2-proxy/tar.gz/{commit}'
        # Hash the exact source archive that BuildKit will download.
        lock['oauth2_proxy'] = {'version': tag.lstrip('v'), 'commit': commit,
                               'url': url, 'sha256': hashlib.sha256(fetch(url)).hexdigest()}
    commit = lock['oauth2_proxy']['commit']
    go_mod = fetch(f'https://raw.githubusercontent.com/oauth2-proxy/oauth2-proxy/{commit}/go.mod').decode()
    required = re.search(r'^go (\d+\.\d+)', go_mod, re.M).group(1)
    go_releases = json.loads(fetch('https://go.dev/dl/?mode=json'))
    go_version = next(r['version'][2:] for r in go_releases if r['stable'] and r['version'].startswith('go' + required + '.'))
    lock['bases']['go'] = digest_image(f'docker.io/library/golang:{go_version}-bookworm')
    release = stable('keycloak/keycloak')
    tag = release['tag_name']
    if is_newer(tag, lock['keycloak']['version']):
        asset = next(a for a in release['assets'] if a['name'] == f'keycloak-{tag}.tar.gz')
        checksum = asset.get('digest', '')
        if not re.fullmatch(r'sha256:[0-9a-f]{64}', checksum):
            raise ValueError('Keycloak release must provide an upstream SHA-256 asset digest')
        lock['keycloak'] = {'version': tag, 'url': asset['browser_download_url'], 'sha256': checksum[7:]}
    version = lock['keycloak']['version']
    pom = ET.fromstring(fetch(f'https://raw.githubusercontent.com/keycloak/keycloak/{version}/pom.xml'))
    ns = {'m': 'http://maven.apache.org/POM/4.0.0'}
    props = {e.tag.split('}')[-1]: e.text for e in pom.find('m:properties', ns)}
    providers = dict(lock['bcfips'])
    for artifact, prop in [('bc-fips', 'bouncycastle.bcfips.version'),
                           ('bctls-fips', 'bouncycastle.bctls-fips.version'),
                           ('bcpkix-fips', 'bouncycastle.pkixfips.version'),
                           ('bcutil-fips', 'bouncycastle.bcutilfips.version')]:
        v = props[prop]
        current = providers.get(artifact, {}).get('version')
        if current and not is_newer(v, current):
            continue
        url = f'https://repo.maven.apache.org/maven2/org/bouncycastle/{artifact}/{v}/{artifact}-{v}.jar'
        providers[artifact] = {'version': v, 'url': url, 'sha256': hashlib.sha256(fetch(url)).hexdigest()}
    lock['bcfips'] = providers
    for name in ('static', 'ubi', 'ca', 'java'):
        lock['bases'][name] = digest_image(lock['bases'][name].split('@')[0])
    # Cryptographic module version is deliberately reviewed manually, never switched to "latest".
    LOCK.write_text(json.dumps(lock, indent=2) + '\n')
    sync_base_defaults(lock)

def build_args(image):
    d = json.loads(LOCK.read_text())
    common = {'CA_IMAGE': d['bases']['ca']}
    if image == 'oauth2-proxy':
        o = d['oauth2_proxy']
        return common | {'GO_IMAGE': d['bases']['go'], 'STATIC_IMAGE': d['bases']['static'],
                         'VERSION': o['version'], 'SOURCE_URL': o['url'],
                         'CRYPTO_VERSION': d['go_security_updates']['crypto'],
                         'GRPC_VERSION': d['go_security_updates']['grpc'],
                         'SOURCE_SHA256': o['sha256'], 'GOFIPS140': d['go_fips_module']}
    k = d['keycloak']
    args = common | {'UBI_IMAGE': d['bases']['ubi'], 'JAVA_IMAGE': d['bases']['java'], 'VERSION': k['version'],
                     'SOURCE_URL': k['url'], 'SOURCE_SHA256': k['sha256']}
    for name, provider in d['bcfips'].items():
        key = name.replace('-', '_').upper()
        args[key + '_URL'] = provider['url']
        args[key + '_SHA256'] = provider['sha256']
    return args

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--update', action='store_true')
    parser.add_argument('--build', choices=['oauth2-proxy', 'keycloak'])
    parser.add_argument('--tag')
    parser.add_argument('--platform', default='linux/arm64' if os.uname().machine == 'arm64' else 'linux/amd64')
    args = parser.parse_args()
    if args.update:
        update()
    if args.build:
        command = ['docker', 'buildx', 'build', '--load', '--platform', args.platform,
                   '-f', str(ROOT / ('Dockerfile.' + args.build)), '-t', args.tag or ('kreutzmann-img/' + args.build + ':local')]
        for key, value in build_args(args.build).items():
            command += ['--build-arg', f'{key}={value}']
        subprocess.run(command + [str(ROOT)], check=True)
