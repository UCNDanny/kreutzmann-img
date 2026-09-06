#!/usr/bin/env python3
"""Image hardening smoke test.

Runs each built image under the production runtime restrictions and checks only its
intrinsic security claims: the fixed non-root identity, that it starts with a
read-only root and no capabilities, and its FIPS build posture. No OIDC provider,
database, upstream, application traffic, or HTTP routing is involved.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

image_name = sys.argv[1]
image = sys.argv[2] if len(sys.argv) > 2 else 'kreutzmann-img/' + image_name + ':local'
expected_user = '65532:65532' if image_name == 'oauth2-proxy' else '1000:1000'


def docker(*args):
    return subprocess.check_output(['docker', *args], text=True).strip()


# 1. Fixed unprivileged identity, baked into the image config.
actual_user = json.loads(docker('image', 'inspect', image))[0]['Config']['User']
assert actual_user == expected_user, f'expected USER {expected_user}, got {actual_user!r}'

# 2. Starts with a read-only root, no Linux capabilities, no privilege escalation,
#    and only the small owned tmpfs it declares.
owner, group = expected_user.split(':')
restrictions = [
    '--read-only', '--cap-drop=ALL', '--security-opt=no-new-privileges:true',
    '--pids-limit=512', '--memory=2g',
    '--tmpfs', f'/tmp:rw,noexec,nosuid,nodev,size=128m,uid={owner},gid={group}',
]
version = docker('run', '--rm', *restrictions, image, '--version')
assert version
print(version)

# 3. FIPS build posture.
if image_name == 'keycloak':
    config = docker('run', '--rm', *restrictions, image, 'show-config')
    assert 'fips' in config and 'postgres' in config, config
    started = subprocess.run(
        ['docker', 'run', '--rm', *restrictions,
         '--tmpfs', '/opt/keycloak/data:rw,noexec,nosuid,nodev,size=128m,uid=1000,gid=1000',
         '-e', 'KC_HTTP_ENABLED=true', '-e', 'KC_PROXY_HEADERS=xforwarded',
         '-e', 'KC_HOSTNAME=https://auth.example.com',
         '-e', 'KC_DB_URL=jdbc:postgresql://127.0.0.1:1/keycloak',
         image, 'start', '--optimized'],
        capture_output=True, text=True, timeout=120)
    output = started.stdout + started.stderr
    # Strict BCFIPS must reach approved mode before the expected unreachable-database exit.
    assert 'Approved Mode' in output, output
    assert started.returncode != 0 and 'Failed to obtain JDBC connection' in output, output
    print('Keycloak reaches BCFIPS Approved Mode under the runtime restrictions.')
else:
    module = json.loads(
        (Path(__file__).resolve().parents[1] / 'dependencies.lock.json').read_text()
    )['go_fips_module']
    container = docker('create', image)
    try:
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            for name in ('build-info.txt', 'packages.txt'):
                subprocess.run(
                    ['docker', 'cp', f'{container}:/usr/share/ourimageshardened/{name}', str(work)],
                    check=True)
            info = (work / 'build-info.txt').read_text()
            assert f'GOFIPS140={module}' in info and 'CGO_ENABLED=0' in info, info
            packages = (work / 'packages.txt').read_text().splitlines()
            assert packages and not any(
                p == 'golang.org/x/crypto/openpgp' or p.startswith('golang.org/x/crypto/openpgp/')
                for p in packages), 'OpenPGP present; the GO-2026-5932 exclusion no longer applies'
    finally:
        docker('rm', container)
    print(f'Gateway built with GOFIPS140={module}, CGO disabled, and no OpenPGP.')
