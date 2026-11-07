#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build compact Mala USB archives from reviewed local files."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import stat
import sys
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'installer'))
import catalog as policy
from transaction import canonical

PREFIXES = {'mala': 'mala-hector'}
EXCLUDE = {'.git', 'build', 'dist', 'artifacts', '__pycache__'}
RUNTIME = ('install.py', 'installer/transaction.py', 'installer/catalog.py')


def usb_source_files(source):
    """Keep complete code/runtime artwork while omitting optional documentation images."""
    image_suffixes = {'.png', '.jpg', '.jpeg', '.webp', '.gif'}
    return {name: raw for name, raw in source.items()
            if not (name.startswith('docs/images/') and Path(name).suffix.lower() in image_suffixes)}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def source_files():
    result = {}
    for path in sorted(ROOT.rglob('*')):
        relative = path.relative_to(ROOT)
        if set(relative.parts) & EXCLUDE or path.suffix == '.pyc':
            continue
        if path.is_symlink():
            raise ValueError('Symlink in public source')
        if path.is_file():
            result[relative.as_posix()] = path.read_bytes()
    return result


def zip_bytes(files):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, raw in sorted(files.items()):
            info = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(info, raw)
    return stream.getvalue()


def tar_bytes(files, prefix):
    stream = io.BytesIO()
    with gzip.GzipFile(fileobj=stream, mode='wb', filename='', mtime=0, compresslevel=9) as zipped:
        with tarfile.open(fileobj=zipped, mode='w', format=tarfile.PAX_FORMAT) as archive:
            for name, raw in sorted(files.items()):
                info = tarfile.TarInfo(prefix + '/' + name)
                info.size, info.mode, info.mtime = len(raw), 0o644, 0
                archive.addfile(info, io.BytesIO(raw))
    return stream.getvalue()


def own_payload(component, payload_root):
    if component != 'mala':
        raise ValueError('This repository packages Mala only')
    if payload_root is not None:
        files = {path.relative_to(payload_root).as_posix(): path.read_bytes()
                 for path in payload_root.rglob('*')
                 if path.is_file() and '__pycache__' not in path.parts}
    else:
        bundle = 'mala.lv2'
        library = 'mala.so'
        files = {}
        for folder, prefix in [('ui', 'home/debian/UI/'), ('bundle', 'usr/lib/lv2/' + bundle + '/')]:
            for path in (ROOT / folder).rglob('*'):
                if path.is_file() and '__pycache__' not in path.parts:
                    files[prefix + path.relative_to(ROOT / folder).as_posix()] = path.read_bytes()
        files['usr/lib/lv2/' + bundle + '/' + library] = (ROOT / 'artifacts' / bundle / library).read_bytes()
    expected = json.loads((ROOT / 'provenance/companion-payloads.json').read_text())[component]
    if {path: sha(raw) for path, raw in files.items()} != expected:
        raise ValueError('Component payload differs from the reviewed exact inventory')
    return files


def package(component, output, payload_root=None):
    if component != 'mala':
        raise ValueError('This repository packages Mala only')
    if output.exists():
        raise ValueError('Choose a fresh output folder')
    release = json.loads((ROOT / 'release.json').read_text())
    if component == 'mala' and release['version'] != '0.2.0-beta.1':
        raise ValueError('This reviewed packager requires the distinct v2 identity')
    catalog = policy.load(ROOT / 'provenance/component-catalog.json')
    files = own_payload(component, payload_root)
    blobs = {sha(raw): raw for raw in files.values()}
    for state, row in json.loads((ROOT / 'provenance/host-compositions.json').read_text())['states'].items():
        for path, expected in row['files'].items():
            raw = (ROOT / 'integration/hosts' / state / path.removeprefix('home/debian/UI/')).read_bytes()
            if sha(raw) != expected:
                raise ValueError('Changed shared host composition')
            blobs[expected] = raw
    info = dict(schema='hector-community/usb-kit/1', component=component,
                version=catalog['components'][component]['version'], compatibility_revision=2,
                catalog_sha256=sha(canonical(catalog)))
    source = source_files()
    usb_source = usb_source_files(source)
    package_revision = release['package_revision']
    if package_revision != 'slim.1':
        raise ValueError('This reviewed packager requires packaging revision slim.1')
    common = {name: source[name] for name in RUNTIME}
    common['kit.json'] = (json.dumps(info, indent=2) + '\n').encode()
    common['catalog.json'] = source['provenance/component-catalog.json']
    base = PREFIXES[component] + '-' + info['version'] + '-compat.2-' + package_revision
    artifacts = {}
    for action in ('install', 'rollback'):
        needed = set()
        for state in catalog['states']:
            transition = policy.transition(catalog, state, component, action)
            if transition is not None:
                needed.update(row['sha256'] for row in transition['files'] if row['sha256'] is not None)
        if needed - set(blobs):
            raise ValueError('Missing transition payloads: ' + str(sorted(needed - set(blobs))))
        content = {component + '/' + name: raw for name, raw in common.items()}
        content.update({component + '/blobs/' + value: blobs[value] for value in needed})
        content.update({component + '/source/' + name: raw for name, raw in usb_source.items()})
        content['READ-ME-FIRST.txt'] = source['docs/USB-' + action.upper() + '.md']
        checks = ''.join("printf '%s  %s\\n' '" + sha(raw) + "' '" + component + '/' + name
                         + "' | /usr/bin/sha256sum --check --status\n" for name, raw in sorted(common.items()))
        launcher = '''#!/bin/bash
set -eu
umask 077
case "$(uname -m)" in aarch64|arm64) ;; *) echo 'Hector required'; exit 1 ;; esac
/usr/bin/mountpoint -q /usb_flash
cd /usb_flash
exec >> /usb_flash/COMMUNITY-LAUNCHER.log 2>&1
'''
        content['debug.sh'] = (launcher + checks + '/usr/bin/python3 -I -B -u /usb_flash/'
                               + component + '/install.py --usb ' + action + '\n').encode()
        content[component + '/SHA256SUMS'] = ''.join(sha(raw) + '  ' + name + '\n'
                                                    for name, raw in sorted(content.items())).encode()
        artifacts[base + '-usb-' + action + '.zip'] = zip_bytes(content)
    artifacts[base + '-source.tar.gz'] = tar_bytes(source, base)
    output.mkdir(parents=True)
    for name, raw in artifacts.items():
        (output / name).write_bytes(raw)
    (output / 'SHA256SUMS').write_text(''.join(sha(raw) + '  ' + name + '\n'
                                             for name, raw in sorted(artifacts.items())))
    result = dict(status='experimental-local-candidate', component=component, version=info['version'],
                  compatibility_revision=2, package_revision=package_revision,
                  source_files=len(source), usb_source_files=len(usb_source), component_files=len(files),
                  recognized_states=len(catalog['states']), public_usb_hardware_tested=False,
                  published=False, public_source_sha256={name: sha(raw) for name, raw in source.items()},
                  usb_source_sha256={name: sha(raw) for name, raw in usb_source.items()},
                  omitted_optional_documentation_images=sorted(set(source) - set(usb_source)),
                  outputs={name: dict(size=len(raw), sha256=sha(raw)) for name, raw in artifacts.items()})
    (output / 'RESULT.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: value for key, value in result.items()
                      if key not in ('public_source_sha256', 'usb_source_sha256')}, indent=2))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--component', choices=sorted(PREFIXES),
                        default=json.loads((ROOT / 'release.json').read_text()).get('component', 'mala'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--payload-root', type=Path)
    args = parser.parse_args()
    package(args.component, args.output.resolve(), args.payload_root.resolve() if args.payload_root else None)


if __name__ == '__main__':
    main()
