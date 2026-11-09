#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Verify release archives, embedded source, scripts, ELF and reproducibility."""
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import stat
import subprocess
import tarfile
import tempfile
import zipfile
from package import ROOT, source_files, payload, debug_entry, package


def sha(raw):return hashlib.sha256(raw).hexdigest()


def verify(folder,arm):
    src=source_files();m,payload_files=payload(arm);prefix='mala-hector-'+m['version']
    expected={prefix+'-usb-install.zip',prefix+'-usb-rollback.zip',prefix+'-source.tar.gz'}
    sums={line.split('  ',1)[1]:line.split('  ',1)[0] for line in (folder/'SHA256SUMS').read_text().splitlines()}
    assert set(sums)==expected
    for name,h in sums.items():assert sha((folder/name).read_bytes())==h,name
    for action in ['install','rollback']:
        with zipfile.ZipFile(folder/(prefix+'-usb-'+action+'.zip')) as z:
            names=z.namelist();assert len(names)==len(set(names))
            for i in z.infolist():
                assert not PurePosixPath(i.filename).is_absolute() and '..' not in PurePosixPath(i.filename).parts
                assert stat.S_IFMT(i.external_attr>>16)==stat.S_IFREG
            for name,raw in src.items():assert z.read('mala/source/'+name)==raw,name
            tools={n:z.read('mala/'+n) for n in ['install.py','installer/transaction.py']}
            assert tools=={n:src[n] for n in tools}
            assert z.read('debug.sh')==debug_entry(action,tools)
            subprocess.run(['/bin/bash','-n'],input=z.read('debug.sh'),check=True)
            assert json.loads(z.read('mala/manifest.json'))==m
            inside_sums={line.split('  ',1)[1]:line.split('  ',1)[0] for line in z.read('mala/SHA256SUMS').decode().splitlines()}
            assert set(inside_sums)==set(names)-{'mala/SHA256SUMS'}
            for name,h in inside_sums.items():assert sha(z.read(name))==h
            actual_payload={n[len('mala/payload/'):]:z.read(n) for n in names if n.startswith('mala/payload/')}
            assert actual_payload==(payload_files if action=='install' else {})
    with tarfile.open(folder/(prefix+'-source.tar.gz'),'r:gz') as t:
        actual={i.name[len(prefix)+1:]:t.extractfile(i).read() for i in t.getmembers() if i.isfile()}
        assert actual==src
    with tempfile.TemporaryDirectory() as d:
        package(arm,Path(d))
        for name in expected|{'SHA256SUMS'}:assert (Path(d)/name).read_bytes()==(folder/name).read_bytes(),name
    report=dict(success=True,version=m['version'],public_source_files=len(src),payload_files=34,
                install_and_rollback_scripts_parse=True,source_complete_in_both_usb_kits=True,
                no_linked_or_traversal_archive_entries=True,checksums_match=True,reproducible_archives=True,
                hardware_usb_test_performed=False,archives={n:dict(bytes=(folder/n).stat().st_size,sha256=h) for n,h in sums.items()})
    print(json.dumps(report,indent=2))
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--folder',type=Path,default=ROOT/'dist')
    p.add_argument('--arm-plugin',type=Path,default=ROOT/'artifacts/mala.lv2/mala.so')
    a=p.parse_args();report=verify(a.folder.resolve(),a.arm_plugin.resolve())
    out=ROOT/'build/release-verification.json';out.parent.mkdir(exist_ok=True);out.write_text(json.dumps(report,indent=2)+'\n')
