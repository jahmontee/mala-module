#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Create reproducible source, USB install and USB rollback archives."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import stat
import struct
import tarfile
import zipfile

ROOT=Path(__file__).resolve().parents[1]
EXCLUDE={'.git','build','dist','artifacts','__pycache__'}


def sha(raw):return hashlib.sha256(raw).hexdigest()


def source_files():
    result={}
    for p in sorted(ROOT.rglob('*')):
        relative=p.relative_to(ROOT)
        if set(relative.parts)&EXCLUDE or p.suffix=='.pyc':continue
        if p.is_symlink():raise ValueError('No symlinks in public archive')
        if p.is_file():result[str(relative)]=p.read_bytes()
    return result


def payload(arm):
    raw=arm.read_bytes()
    if raw[:6]!=b'\x7fELF\x02\x01' or struct.unpack_from('<H',raw,18)[0]!=183:
        raise ValueError('An AArch64 little-endian 64-bit plugin is required')
    release=json.loads((ROOT/'release.json').read_text())
    if sha(raw)!=release['accepted_arm_plugin_sha256']:
        raise ValueError('The public candidate must use the accepted ARM plugin; custom builds need a new reviewed release identity')
    files={}
    for base,prefix in [(ROOT/'integration/firmware407','home/debian/UI/'),
                        (ROOT/'ui','home/debian/UI/'),(ROOT/'bundle','usr/lib/lv2/mala.lv2/')]:
        for p in base.rglob('*'):
            if p.is_file():files[prefix+str(p.relative_to(base))]=p.read_bytes()
    files['usr/lib/lv2/mala.lv2/mala.so']=raw
    manifest={k:release[k] for k in ['version','hardware','firmware','architecture','sample_rate','ports','plugin_uri','guards']}
    manifest.update(schema='mala-hector/public-beta/1',files=[dict(path=n,size=len(b),sha256=sha(b),
        before_sha256=release['stock_sha256'].get(n)) for n,b in sorted(files.items())],
        require_absent=['home/debian/UI/qml/mala','usr/lib/lv2/mala.lv2'])
    assert len(files)==34
    return manifest,files


def debug_entry(action,tools):
    checks=''.join("printf '%s  %s\\n' '"+sha(tools[n])+"' '"+n+"' | /usr/bin/sha256sum --check --status\n" for n in ['install.py','installer/transaction.py'])
    return ('''#!/bin/bash
set -eu
umask 077
case "$(uname -m)" in aarch64|arm64) ;; *) echo 'Hector required'; exit 1 ;; esac
/usr/bin/mountpoint -q /usb_flash
cd /usb_flash/mala
exec >> /usb_flash/MALA-LAUNCHER.log 2>&1
'''+checks+"/usr/bin/python3 -I -B -u /usb_flash/mala/install.py --usb "+action+"\n").encode()


def zip_bytes(files):
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for name,raw in sorted(files.items()):
            info=zipfile.ZipInfo(name,(2026,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            info.create_system=3;info.external_attr=(stat.S_IFREG|0o644)<<16
            archive.writestr(info,raw)
    return stream.getvalue()


def tar_bytes(files,prefix):
    stream=io.BytesIO()
    with gzip.GzipFile(fileobj=stream,mode='wb',filename='',mtime=0,compresslevel=9) as gz:
        with tarfile.open(fileobj=gz,mode='w',format=tarfile.PAX_FORMAT) as archive:
            for name,raw in sorted(files.items()):
                info=tarfile.TarInfo(prefix+'/'+name);info.size=len(raw);info.mode=0o644;info.mtime=0
                archive.addfile(info,io.BytesIO(raw))
    return stream.getvalue()


def package(arm,out):
    out.mkdir(parents=True,exist_ok=True)
    from audit import audit
    audit()
    src=source_files();manifest,files=payload(arm)
    version=manifest['version'];prefix='mala-hector-'+version
    tools={n:src[n] for n in ['install.py','installer/transaction.py']}
    tools['manifest.json']=(json.dumps(manifest,indent=2,sort_keys=True)+'\n').encode()
    for action in ['install','rollback']:
        content={'mala/'+n:b for n,b in tools.items()}
        if action=='install':content.update({'mala/payload/'+n:b for n,b in files.items()})
        content['debug.sh']=debug_entry(action,tools)
        content['READ-ME-FIRST.txt']=src['docs/USB-'+('INSTALL' if action=='install' else 'ROLLBACK')+'.md']
        content['mala/COPYING']=src['COPYING']
        content.update({'mala/source/'+n:b for n,b in src.items()})
        content['mala/SHA256SUMS']=(''.join(sha(b)+'  '+n+'\n' for n,b in sorted(content.items()))).encode()
        (out/(prefix+'-usb-'+action+'.zip')).write_bytes(zip_bytes(content))
    (out/(prefix+'-source.tar.gz')).write_bytes(tar_bytes(src,prefix))
    (out/'SHA256SUMS').write_text(''.join(sha(p.read_bytes())+'  '+p.name+'\n' for p in sorted(out.iterdir()) if p.is_file() and p.name!='SHA256SUMS'))
    print(json.dumps(dict(version=version,files=34,archives=[p.name for p in sorted(out.iterdir())]),indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--arm-plugin',type=Path,default=ROOT/'artifacts/mala.lv2/mala.so')
    p.add_argument('--output',type=Path,default=ROOT/'dist')
    a=p.parse_args();package(a.arm_plugin.resolve(),a.output.resolve())
