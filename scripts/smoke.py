#!/usr/bin/env python3
"""Image hardening smoke test.

Runs each built image under the production runtime restrictions and checks only its
intrinsic security claims: the fixed non-root identity, that it starts with a
read-only root and no capabilities, and its FIPS build posture. OpenBao also starts
sealed on its own storage. No OIDC provider, database, upstream, application traffic,
or HTTP routing is involved.
"""
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

image_name = sys.argv[1]
image = sys.argv[2] if len(sys.argv) > 2 else 'kreutzmann-img/' + image_name + ':local'
expected_user = '1000:1000' if image_name == 'keycloak' else '65532:65532'
lock = json.loads((Path(__file__).resolve().parents[1] / 'dependencies.lock.json').read_text())
OPENBAO_CONFIG = '''
storage "raft" {
  path    = "/openbao/data"
  node_id = "smoke"
}
listener "tcp" {
  address     = "127.0.0.1:8200"
  tls_disable = true
}
api_addr     = "http://127.0.0.1:8200"
cluster_addr = "http://127.0.0.1:8201"
'''


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
    module = lock['go_fips_module']
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
    print(f'{image_name} built with GOFIPS140={module}, CGO disabled, and no OpenPGP.')

if image_name == 'openbao':
    assert lock['openbao']['version'] in version, version
    tags = [t for line in info.splitlines() if line.startswith('\tbuild\t-tags=')
            for t in line.split('=', 1)[1].split(',')]
    assert 'ui' not in tags, 'Built with the ui tag: the web UI must stay out'
    # The default command serves the mounted configuration and starts sealed, with
    # integrated storage on a fresh volume, under the same restrictions.
    with tempfile.TemporaryDirectory() as directory:
        config = Path(directory)
        config.chmod(0o755)
        (config / 'smoke.hcl').write_text(OPENBAO_CONFIG)
        (config / 'smoke.hcl').chmod(0o644)
        server = docker('run', '-d', *restrictions,
                        '-v', f'{config}:/openbao/config:ro', '-v', '/openbao/data', image)
        try:
            for _ in range(30):
                status = subprocess.run(
                    ['docker', 'exec', server, '/usr/bin/bao', 'status', '-format=json',
                     '-address=http://127.0.0.1:8200'], capture_output=True, text=True)
                if status.returncode == 2:
                    break
                time.sleep(1)
            logs = subprocess.run(['docker', 'logs', server], capture_output=True, text=True)
            assert status.returncode == 2, logs.stdout + logs.stderr
            state = json.loads(status.stdout)
            assert state['sealed'] and not state['initialized'], state
        finally:
            subprocess.run(['docker', 'rm', '-f', '-v', server], capture_output=True)
    print('OpenBao starts sealed on integrated storage, with no web UI compiled in.')
