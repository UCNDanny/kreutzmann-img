#!/usr/bin/env python3
"""Run the release workflow's checks locally before any commit or pull request.

Every image is built, smoke-tested and gated on every platform, not only the image a
change touches: a fix published upstream since the last release turns an untouched
image's unfixed finding into a fixable one, and the gate then blocks the whole release.

Usage: preflight.py [--platform linux/arm64] [--image keycloak]
"""
import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import dependencies

ROOT = Path(__file__).resolve().parents[1]
# Same settings as the gate in release.yml.
GATE = ['trivy', 'image', '--quiet', '--scanners', 'vuln', '--ignore-unfixed',
        '--severity', 'UNKNOWN,LOW,MEDIUM,HIGH,CRITICAL', '--exit-code', '1', '--format', 'table']


def run(command, env=None):
    print('\n$ ' + ' '.join(command), flush=True)
    return subprocess.run(command, cwd=ROOT, env=env).returncode == 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--platform', action='append', choices=('linux/amd64', 'linux/arm64'))
    parser.add_argument('--image', action='append', choices=dependencies.IMAGES)
    args = parser.parse_args()
    images = args.image or dependencies.IMAGES
    memory = int(subprocess.check_output(['docker', 'info', '--format', '{{.MemTotal}}'], text=True))
    if 'openbao' in images and memory < 7 * 2**30:
        sys.exit(f'Docker has {memory / 2**30:.1f} GiB of memory; compiling OpenBao needs more '
                 '(8 GB recommended). Raise it under Docker Desktop > Settings > Resources.')
    failures = []
    if not run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests']):
        failures.append('unit tests')
    with tempfile.TemporaryDirectory() as docker_config:
        # Trivy fetches its public database anonymously, without the login keychain.
        trivy_env = os.environ | {'DOCKER_CONFIG': docker_config}
        for image in images:
            for platform in args.platform or ('linux/arm64', 'linux/amd64'):
                tag = f'kreutzmann-img/{image}:{platform.split("/")[1]}'
                step = f'{image} {platform}'
                if not run([sys.executable, 'scripts/dependencies.py', '--build', image,
                            '--platform', platform, '--tag', tag]):
                    failures.append(f'{step}: build')
                    continue
                if not run([sys.executable, 'scripts/smoke.py', image, tag]):
                    failures.append(f'{step}: smoke test')
                ignore = ROOT / f'.trivyignore-{image}.yaml'
                if not run(GATE + (['--ignorefile', str(ignore)] if ignore.exists() else []) + [tag],
                           env=trivy_env):
                    failures.append(f'{step}: vulnerability gate')
    print('\nPreflight ' + ('failed:\n- ' + '\n- '.join(failures) if failures else 'passed.'))
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
