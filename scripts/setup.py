#!/usr/bin/env python3
"""Create a private local configuration without replacing existing credentials."""
import base64
import os
from pathlib import Path
import secrets

ROOT = Path(__file__).resolve().parents[1]


def main():
    target = ROOT / '.env'
    values = {
        'OAUTH2_PROXY_CLIENT_SECRET': secrets.token_hex(32),
        'OAUTH2_PROXY_COOKIE_SECRET': base64.urlsafe_b64encode(os.urandom(32)).decode(),
        'KC_BOOTSTRAP_ADMIN_PASSWORD': secrets.token_hex(24),
    }
    lines = []
    for line in (ROOT / '.env.example').read_text().splitlines():
        key, separator, _ = line.partition('=')
        lines.append(f'{key}={values[key]}' if separator and key in values else line)
    try:
        descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        print('Existing .env preserved; credentials were not changed.')
    else:
        with os.fdopen(descriptor, 'w') as output:
            output.write('\n'.join(lines) + '\n')
        print('Created .env with generated client, cookie, and bootstrap secrets.')
    print('Set public hostnames, realm issuer URL, client ID, access policy, and database credentials in .env.')
    print('Configure the client and matching secret in Keycloak separately; no realm is imported.')
    print('CA certificates are bundled and deployed automatically by the images.')
    print('Set upstream URLs reachable from your deployment, then run make build.')
    print('Run make identity first; run make gateway once the public realm issuer is reachable.')


if __name__ == '__main__':
    main()
