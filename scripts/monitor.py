#!/usr/bin/env python3
"""Print a Markdown report of available updates and fixable vulnerabilities.

Usage: monitor.py IMAGE=TRIVY_JSON [...]
Prints nothing when there is nothing to act on.
"""
import json
from pathlib import Path
import sys

import dependencies

# Derived from a version change; listing them separately only adds noise.
DERIVED = ('url', 'sha256', 'commit')

def leaves(value, prefix=''):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from leaves(child, f'{prefix}.{key}' if prefix else key)
    else:
        yield prefix, value

def updates():
    current = dict(leaves(json.loads(dependencies.LOCK.read_text())))
    available = dict(leaves(dependencies.resolve()))
    return [(key, current.get(key), value) for key, value in available.items()
            if current.get(key) != value and key.rsplit('.', 1)[-1] not in DERIVED]

def findings(image, report):
    for result in json.loads(Path(report).read_text()).get('Results', []):
        for vuln in result.get('Vulnerabilities') or []:
            if vuln.get('FixedVersion'):
                yield (image, vuln['VulnerabilityID'], vuln['Severity'], vuln['PkgName'],
                       vuln['InstalledVersion'], vuln['FixedVersion'])

def table(header, rows):
    lines = ['| ' + ' | '.join(header) + ' |', '|' + ' --- |' * len(header)]
    lines += ['| ' + ' | '.join(f'`{cell}`' for cell in row) + ' |' for row in rows]
    return '\n'.join(lines)

def main(scans):
    sections = []
    if rows := updates():
        sections.append('## Upstream updates\n\n' + table(('Input', 'Locked', 'Available'), rows)
                        + '\n\nRun `python3 scripts/dependencies.py --update`, review the diff, and open a PR.')
    rows = sorted({row for scan in scans for row in findings(*scan.split('=', 1))})
    if rows:
        sections.append('## Fixable vulnerabilities in published `:latest` images\n\n'
                        + table(('Image', 'Vulnerability', 'Severity', 'Package', 'Installed', 'Fixed'), rows)
                        + '\n\nRefresh the affected base or pin the fix (`keycloak_security_updates` or '
                        '`debian_security_updates` in `dependencies.lock.json`), then release.')
    if sections:
        print('\n\n'.join(sections))

if __name__ == '__main__':
    main(sys.argv[1:])
