#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check the public export boundary and complete corresponding source."""
import hashlib
import json
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
EXCLUDE={'.git','build','dist','artifacts','__pycache__'}


def audit():
    required=['README.md','COPYING','LICENSE','CREDITS.md','CONTRIBUTING.md','install.py',
              'installer/transaction.py','docs/USB-INSTALL.md','docs/USB-ROLLBACK.md',
              'docs/KNOWN-LIMITATIONS.md','docs/LICENSING.md','docs/VALIDATION.md',
              'tools/build.py','tools/package.py','LICENSES/Qt-Slider-NOTICE.txt']
    for name in required:assert (ROOT/name).is_file(),name
    patterns=[rb'/home/(?!debian/)[A-Za-z0-9_.-]+/', rb'192\.168\.[0-9]+\.[0-9]+',
              rb'-----BEGIN [A-Z ]*PRIVATE KEY-----']
    release=json.loads((ROOT/'release.json').read_text())
    upstream_literals=set()
    for name,h in release['stock_sha256'].items():
        raw=(ROOT/'tests/fixtures/stock407'/name).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==h
        for pattern in patterns:upstream_literals.update(re.findall(pattern,raw))
    files=[]
    for p in ROOT.rglob('*'):
        relative=p.relative_to(ROOT)
        if set(relative.parts)&EXCLUDE or p.suffix=='.pyc':continue
        assert not p.is_symlink(),str(relative)
        if not p.is_file():continue
        assert p.suffix not in ['.so','.img','.xz','.deb','.key','.pem','.wav','.f32'],str(relative)
        raw=p.read_bytes()
        for pattern in patterns:
            assert all(m in upstream_literals for m in re.findall(pattern,raw)),'Private data pattern: '+str(relative)
        assert len(raw)<1024*1024,str(relative)
        files.append(str(relative))
    lock=json.loads((ROOT/'provenance/source-lock.json').read_text())
    for row in lock['files']:
        assert hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest()==row['sha256'],row['path']
    accepted=json.loads((ROOT/'provenance/accepted-build.json').read_text())
    for name,h in accepted['compiled_source_sha256'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==h,'Accepted binary/source mismatch: '+name
    assert 'Copyright (C) 2017 The Qt Company Ltd.' in (ROOT/'ui/qml/mala/Slider.qml').read_text()
    release=json.loads((ROOT/'release.json').read_text())
    for name,h in release['stock_sha256'].items():
        assert hashlib.sha256((ROOT/'tests/fixtures/stock407'/name).read_bytes()).hexdigest()==h
    assert b'v0.1.0-beta.6' in (ROOT/'ui/qml/mala/Editor.qml').read_bytes()
    print(json.dumps(dict(success=True,public_files=len(files),no_private_patterns=True,complete_source=True)))
    return files


if __name__=='__main__':audit()
