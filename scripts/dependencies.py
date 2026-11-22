#!/usr/bin/env python3
"""Refresh reviewed build inputs. Network access is only needed for --update."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / 'dependencies.lock.json'
IMAGES = ('oauth2-proxy', 'keycloak', 'openbao')

def sync_base_defaults(lock):
    for image in IMAGES:
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

def latest_go_module(module, current):
    # "@latest" can point at an abandoned release line the maintainers chose not to
    # patch (e.g. grpc-go skipped fixing 1.84.x and told users to move to 1.85+), so
    # walk stable versions newest-first and skip any OSV still flags as vulnerable.
    versions = [v for v in fetch(f'https://proxy.golang.org/{module}/@v/list').decode().split()
               if re.fullmatch(r'v\d+\.\d+\.\d+', v)]
    versions.sort(key=lambda v: tuple(int(part) for part in v[1:].split('.')), reverse=True)
    for version in versions:
        if semver(version) < semver(current):
            break
        if not osv_affected(module, version):
            return version
    raise ValueError(f'No unaffected stable version at or above {current} found for {module}')

def go_source(lock, key, repo):
    """Lock the newest stable release's source archive; return the Go minor its go.mod requires."""
    tag = stable(repo)['tag_name']
    if is_newer(tag, lock[key]['version']):
        commit = api(f'repos/{repo}/commits/{tag}')['sha']
        url = f'https://codeload.github.com/{repo}/tar.gz/{commit}'
        # Hash the exact source archive that BuildKit will download.
        lock[key] = {'version': tag.lstrip('v'), 'commit': commit,
                     'url': url, 'sha256': hashlib.sha256(fetch(url)).hexdigest()}
    go_mod = fetch(f'https://raw.githubusercontent.com/{repo}/{lock[key]["commit"]}/go.mod').decode()
    return re.search(r'^go (\d+\.\d+)', go_mod, re.M).group(1)

# Runs in the Debian resolver image: apt verifies the signed trixie, trixie-updates and
# trixie-security indexes and prints each newer package's file name and SHA-256.
APT_NEWER = r'''
set -eu
native=$(dpkg --print-architecture)
for arch in amd64 arm64; do [ "$arch" = "$native" ] || dpkg --add-architecture "$arch"; done
apt-get update -qq >/dev/null
while read -r package arch base; do
  spec=$package; [ "$arch" = all ] || spec=$package:$arch
  candidate=$(apt-cache policy "$spec" | awk '/Candidate:/ {print $2}')
  if dpkg --compare-versions "$candidate" gt "$base"; then
    echo "$package $base $candidate $(apt-get download --print-uris "$spec=$candidate" | cut -d' ' -f2,4)"
  fi
done
'''

def base_packages(image, platform):
    """Map each Debian package in a distroless image to its (version, architecture)."""
    # Docker cannot hold two platforms under one index digest, so pull the platform's own manifest.
    index = json.loads(subprocess.check_output(['docker', 'buildx', 'imagetools', 'inspect', image, '--raw']))
    os_name, arch = platform.split('/')
    digest = next(m['digest'] for m in index['manifests']
                  if m['platform']['os'] == os_name and m['platform']['architecture'] == arch)
    image = image.split('@')[0] + '@' + digest
    container = subprocess.check_output(['docker', 'create', '--platform', platform, image, 'x'], text=True).strip()
    try:
        archive = subprocess.check_output(['docker', 'cp', f'{container}:/var/lib/dpkg/status.d', '-'])
    finally:
        subprocess.run(['docker', 'rm', container], check=True, capture_output=True)
    packages = {}
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        for member in tar.getmembers():
            if member.isfile() and not member.name.endswith('.md5sums'):
                control = dict(line.split(': ', 1) for line in tar.extractfile(member).read().decode().splitlines()
                               if ': ' in line and not line.startswith(' '))
                packages[control['Package']] = (control['Version'], control['Architecture'])
    return packages

def snapshot_url(package, version, name):
    # Pool files vanish once superseded; snapshot.debian.org keeps every published file.
    info = json.loads(fetch(f'https://snapshot.debian.org/mr/binary/{package}/'
                            f'{urllib.parse.quote(version, safe="")}/binfiles?fileinfo=1'))
    for files in info['fileinfo'].values():
        for file in files:
            if file['name'] == name and file['archive_name'] in ('debian', 'debian-security'):
                return (f'https://snapshot.debian.org/archive/{file["archive_name"]}/'
                        f'{file["first_seen"]}{file["path"]}/{name}')
    raise ValueError(f'{name} is not on snapshot.debian.org yet')

def debian_updates(image, resolver):
    """Lock the newest Debian release of every package the distroless base ships outdated."""
    updates = {}
    for arch in ('amd64', 'arm64'):
        query = ''.join(f'{package} {architecture} {version}\n' for package, (version, architecture)
                        in base_packages(image, 'linux/' + arch).items())
        output = subprocess.run(['docker', 'run', '--rm', '-i', resolver, 'sh', '-c', APT_NEWER],
                                input=query, text=True, capture_output=True, check=True).stdout
        for line in output.splitlines():
            package, base, version, name, checksum = line.split()
            entry = updates.setdefault(package, {'package': package, 'base_version': base,
                                                 'version': version, 'debs': {}})
            if (entry['base_version'], entry['version']) != (base, version):
                raise ValueError(f'{package} versions differ between architectures')
            entry['debs'][arch] = {'url': snapshot_url(package, version, name),
                                   'sha256': checksum.removeprefix('SHA256:')}
    for entry in updates.values():
        if set(entry['debs']) != {'amd64', 'arm64'}:
            raise ValueError(f'{entry["package"]} is outdated on only one architecture')
    return sorted(updates.values(), key=lambda entry: entry['package'])

def resolve():
    """Return the lock with the newest verified upstream inputs, without writing it."""
    lock = json.loads(LOCK.read_text())
    for key, module in {
        'crypto': 'golang.org/x/crypto',
        'grpc': 'google.golang.org/grpc',
        'net': 'golang.org/x/net',
        'jose': 'github.com/go-jose/go-jose/v4',
        'otel': 'go.opentelemetry.io/otel',
    }.items():
        lock['go_security_updates'][key] = latest_go_module(module, lock['go_security_updates'][key])
    scanner = stable('aquasecurity/trivy')['tag_name'].lstrip('v')
    if is_newer(scanner, lock['trivy_version']):
        lock['trivy_version'] = scanner
    # One Go toolchain builds every Go image: the newest patch of the highest minor they require.
    required = max((go_source(lock, 'oauth2_proxy', 'oauth2-proxy/oauth2-proxy'),
                    go_source(lock, 'openbao', 'openbao/openbao')), key=semver)
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
    for name in ('static', 'ubi', 'ca', 'java', 'debian'):
        lock['bases'][name] = digest_image(lock['bases'][name].split('@')[0])
    lock['debian_security_updates'] = debian_updates(lock['bases']['java'], lock['bases']['debian'])
    # Cryptographic module version is deliberately reviewed manually, never switched to "latest".
    return lock

def update():
    lock = resolve()
    LOCK.write_text(json.dumps(lock, indent=2) + '\n')
    sync_base_defaults(lock)

def build_args(image):
    d = json.loads(LOCK.read_text())
    common = {'CA_IMAGE': d['bases']['ca']}
    go = common | {'GO_IMAGE': d['bases']['go'], 'STATIC_IMAGE': d['bases']['static'],
                   'CRYPTO_VERSION': d['go_security_updates']['crypto'],
                   'GRPC_VERSION': d['go_security_updates']['grpc'],
                   'NET_VERSION': d['go_security_updates']['net'],
                   'GOFIPS140': d['go_fips_module']}
    if image == 'oauth2-proxy':
        o = d['oauth2_proxy']
        return go | {'VERSION': o['version'], 'SOURCE_URL': o['url'], 'SOURCE_SHA256': o['sha256']}
    if image == 'openbao':
        o = d['openbao']
        return go | {'VERSION': o['version'], 'COMMIT': o['commit'],
                     'SOURCE_URL': o['url'], 'SOURCE_SHA256': o['sha256'],
                     'JOSE_VERSION': d['go_security_updates']['jose'],
                     'OTEL_VERSION': d['go_security_updates']['otel']}
    args = common | {'UBI_IMAGE': d['bases']['ubi'], 'JAVA_IMAGE': d['bases']['java']}
    k = d['keycloak']
    args |= {'VERSION': k['version'], 'SOURCE_URL': k['url'], 'SOURCE_SHA256': k['sha256']}
    for name, provider in d['bcfips'].items():
        key = name.replace('-', '_').upper()
        args[key + '_URL'] = provider['url']
        args[key + '_SHA256'] = provider['sha256']
    return args

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--update', action='store_true')
    parser.add_argument('--build', choices=IMAGES)
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
