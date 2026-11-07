#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Review-time catalog generation. Reads local source and the accepted ARM plugin."""
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def generate():
    legacy = json.loads((ROOT / 'provenance/legacy-component-catalog.json').read_text())
    release = json.loads((ROOT / 'release.json').read_text())
    own = {}
    for folder, prefix in [('ui', 'home/debian/UI/'), ('bundle', 'usr/lib/lv2/mala.lv2/')]:
        for path in (ROOT / folder).rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts:
                own[prefix + path.relative_to(ROOT / folder).as_posix()] = path.read_bytes()
    arm = (ROOT / 'artifacts/mala.lv2/mala.so').read_bytes()
    if sha(arm) != release['accepted_arm_plugin_sha256']:
        raise ValueError('Reviewed ARM binary required')
    own['usr/lib/lv2/mala.lv2/mala.so'] = arm
    catalog = copy.deepcopy(legacy)
    catalog['schema'] = 'hector-community/catalog/2'
    catalog['components']['mala']['version'] = release['version']
    catalog['paths'] = sorted(set(legacy['paths']) | set(own))
    catalog['states'] = {}
    for key, original in legacy['states'].items():
        row = copy.deepcopy(original)
        row['files'].update({path: None for path in set(own) - set(row['files'])})
        if 'mala' in row['components']:
            row['mala_version'] = '0.1.0-beta.6'
            catalog['states'][key + '~mala-beta6'] = copy.deepcopy(row)
            row['mala_version'] = release['version']
            row['files'].update({path: sha(raw) for path, raw in own.items()})
        catalog['states'][key] = row
    for raw in own.values():
        catalog['artifacts'][sha(raw)] = dict(mode=0o644, size=len(raw))
    old_digest = sha(json.dumps(legacy, sort_keys=True, separators=(',', ':')).encode())
    catalog['legacy_catalogs'] = {old_digest: dict(
        components=legacy['components'],
        states={key: key + ('~mala-beta6' if 'mala' in row['components'] else '')
                for key, row in legacy['states'].items()})}
    write(ROOT / 'provenance/component-catalog.json', catalog)
    companions = json.loads((ROOT / 'provenance/companion-payloads.json').read_text())
    companions['mala'] = {path: sha(raw) for path, raw in sorted(own.items())}
    write(ROOT / 'provenance/companion-payloads.json', companions)
    # The transaction engine accepts only this enumerated file scope.
    path = ROOT / 'installer/transaction.py'
    source = path.read_text()
    start = source.index('ALLOWED_TARGETS = ')
    end = source.index('\n\ndef valid_hash', start)
    source = source[:start] + 'ALLOWED_TARGETS = ' + repr(tuple(catalog['paths'])) + '\n' + source[end:]
    path.write_text(source)
    print(json.dumps(dict(states=len(catalog['states']), mala_files=len(own),
                          accepted_legacy_catalog=old_digest)))


if __name__ == '__main__':
    generate()
