"""Stage checksum-pinned Debian security updates for the distroless runtime base.

Distroless has no package manager: a package is its files plus a status.d record
holding the package's control file. The fixed .deb is unpacked the same way into
/opt/debian-security-updates, which the runtime stage copies over its base.
"""
import hashlib
import io
import json
import os
from pathlib import Path
import tarfile
import urllib.request

lock = json.loads(Path('/tmp/dependencies.lock.json').read_text())
arch = os.environ['TARGETARCH']
base = Path('/tmp/base-status.d')
root = Path('/opt/debian-security-updates')
status = root / 'var/lib/dpkg/status.d'
status.mkdir(parents=True)

def ar_members(data):
    # A .deb is an ar archive: magic, then 60-byte headers each followed by an even-padded body.
    if data[:8] != b'!<arch>\n':
        raise RuntimeError('Not a Debian package archive')
    members, offset = {}, 8
    while offset < len(data):
        header = data[offset:offset + 60]
        size = int(header[48:58])
        members[header[:16].decode().strip().rstrip('/')] = data[offset + 60:offset + 60 + size]
        offset += 60 + size + size % 2
    return members

def field(control, name):
    return next(line.split(': ', 1)[1] for line in control.splitlines() if line.startswith(name + ': '))

def paths(md5sums):
    return {line.split(None, 1)[1] for line in md5sums.splitlines() if line.strip()}

for update in lock['debian_security_updates']:
    package = update['package']
    installed = base / package
    if not installed.is_file() or field(installed.read_text(), 'Version') != update['base_version']:
        raise RuntimeError(f'Runtime base changed {package}; review or remove its security update')
    deb = update['debs'][arch]
    with urllib.request.urlopen(deb['url'], timeout=120) as response:
        data = response.read()
    if hashlib.sha256(data).hexdigest() != deb['sha256']:
        raise RuntimeError(f'Checksum mismatch: {package} {arch}')
    members = ar_members(data)
    with tarfile.open(fileobj=io.BytesIO(members['control.tar.xz'])) as control_tar:
        control = control_tar.extractfile('./control').read().decode()
        md5sums = control_tar.extractfile('./md5sums').read().decode()
    if field(control, 'Package') != package or field(control, 'Version') != update['version']:
        raise RuntimeError(f'Package metadata does not match the lock: {package}')
    # Overlaying cannot delete files, so the update must ship exactly the installed file set.
    if paths(md5sums) != paths((base / (package + '.md5sums')).read_text()):
        raise RuntimeError(f'File list changed for {package}; overlay would leave stale files')
    with tarfile.open(fileobj=io.BytesIO(members['data.tar.xz'])) as data_tar:
        data_tar.extractall(root, filter='data')
    (status / package).write_text(control)
    (status / (package + '.md5sums')).write_text(md5sums)
