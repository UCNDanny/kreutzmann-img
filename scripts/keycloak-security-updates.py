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
    # Quarkus's distribution classpath refers to these paths. Replace the bytes
    # before augmentation; each JAR retains its genuine Maven/version metadata.
    target.write_bytes(data)
