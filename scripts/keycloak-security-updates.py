"""Apply checksum-pinned security updates before Keycloak augmentation."""
import hashlib
import json
from pathlib import Path
import urllib.request

lock = json.loads(Path('/tmp/dependencies.lock.json').read_text())
libraries = Path('/opt/keycloak/lib/lib/main')
for update in lock['keycloak_security_updates']:
    target = libraries / update['file']
    if not target.is_file():
        raise RuntimeError(f'Upstream library changed; review security pin: {target.name}')
    with urllib.request.urlopen(update['url'], timeout=120) as response:
        data = response.read()
    if hashlib.sha256(data).hexdigest() != update['sha256']:
        raise RuntimeError(f'Checksum mismatch: {target.name}')
    replacement = libraries / update.get('replacement_file', update['file'])
    replacement.write_bytes(data)
    if replacement != target:
        target.unlink()
        # Keycloak's prebuilt Quarkus app model retains the upstream path during
        # augmentation, while scanners use the real JAR name to identify its version.
        target.symlink_to(replacement.name)
