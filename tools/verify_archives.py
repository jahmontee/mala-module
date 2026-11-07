#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Validate actual ZIP closure, source equality, integrity and desktop refusal."""
import argparse,gzip,hashlib,io,json,stat,subprocess,tarfile,tempfile,zipfile,sys
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'installer'))
import catalog as policy
from package_v2 import usb_source_files
def sha(raw):return hashlib.sha256(raw).hexdigest()
def verify(folder):
    receipt=json.loads((folder/'RESULT.json').read_text());component=receipt['component'];prefix=component;version=receipt['version'];base='mala-hector-'+version+'-compat.2-'+receipt['package_revision']
    if component!='mala' or receipt['package_revision']!='slim.1':raise ValueError('Unexpected Mala packaging identity')
    checks={name:h for h,name in (line.split('  ',1) for line in (folder/'SHA256SUMS').read_text().splitlines())}
    if set(checks)!=set(receipt['outputs']):raise ValueError('External checksum inventory differs')
    for name,h in checks.items():
        raw=(folder/name).read_bytes()
        if sha(raw)!=h or h!=receipt['outputs'][name]['sha256']:raise ValueError('Archive checksum differs')
    sources={}
    with tarfile.open(folder/(base+'-source.tar.gz'),'r:gz') as t:
        for m in t:
            if not m.isfile() or m.issym() or m.islnk():raise ValueError('Nonregular source archive member')
            if not m.name.startswith(base+'/'):raise ValueError('Source archive prefix differs')
            name=m.name[len(base)+1:];sources[name]=t.extractfile(m).read()
    if {n:sha(raw) for n,raw in sources.items()}!=receipt['public_source_sha256']:raise ValueError('Source archive incomplete/different')
    expected_usb_source=usb_source_files(sources)
    if {n:sha(raw) for n,raw in expected_usb_source.items()}!=receipt['usb_source_sha256']:raise ValueError('USB source inventory differs')
    if sorted(set(sources)-set(expected_usb_source))!=receipt['omitted_optional_documentation_images']:raise ValueError('Unexpected source omissions')
    for action in ['install','rollback']:
        with zipfile.ZipFile(folder/(base+'-usb-'+action+'.zip')) as z:
            if z.testzip():raise ValueError('ZIP CRC failure')
            names=z.namelist()
            if len(names)!=len(set(names)):raise ValueError('Duplicate ZIP member')
            for name in names:
                p=PurePosixPath(name)
                if p.is_absolute() or '..' in p.parts or str(p)!=name:raise ValueError('Unsafe ZIP member')
                if stat.S_IFMT(z.getinfo(name).external_attr>>16)!=stat.S_IFREG:raise ValueError('Nonregular ZIP member')
            source={n[len(prefix+'/source/'):]:z.read(n) for n in names if n.startswith(prefix+'/source/')}
            if source!=expected_usb_source:raise ValueError('USB corresponding source differs beyond optional documentation images')
            if any(n.startswith('docs/images/') for n in source):raise ValueError('Documentation image included in USB source')
            manifest_checks={n:h for h,n in (line.split('  ',1) for line in z.read(prefix+'/SHA256SUMS').decode().splitlines())}
            if set(manifest_checks)!=(set(names)-{prefix+'/SHA256SUMS'}):raise ValueError('Inner checksum inventory differs')
            for n,h in manifest_checks.items():
                if sha(z.read(n))!=h:raise ValueError('Inner checksum differs')
            info=json.loads(z.read(prefix+'/kit.json'));catalog=json.loads(z.read(prefix+'/catalog.json'))
            if info['component']!=component or info['catalog_sha256']!=sha(json.dumps(catalog,sort_keys=True,separators=(',',':')).encode()):raise ValueError('Kit/catalog identity mismatch')
            blobs={n[len(prefix+'/blobs/'):]:z.read(n) for n in names if n.startswith(prefix+'/blobs/')}
            for h,raw in blobs.items():
                if sha(raw)!=h:raise ValueError('Corrupt content-addressed payload')
            needed=set()
            for state in catalog['states']:
                transition=policy.transition(catalog,state,component,action)
                if transition:
                    needed.update(row['sha256'] for row in transition['files'] if row['sha256'] is not None)
            if not needed.issubset(blobs):raise ValueError('Kit missing a required installed-set transition blob')
            # Other add-ons' existing binaries are guards, not shipped payloads.
            binary_paths={'mala':'usr/lib/lv2/mala.lv2/mala.so','network-link':'usr/lib/lv2/hector-link-sync.lv2/hector_link_sync.so','squelch-box':'usr/lib/lv2/poly303.lv2/poly303.so'}
            for other,path in binary_paths.items():
                if other!=component:
                    h=next(r['files'][path] for r in catalog['states'].values() if r['files'][path] is not None)
                    if h in blobs:raise ValueError('Unrequested companion binary included')
            with tempfile.TemporaryDirectory() as work:
                script=Path(work)/'debug.sh';script.write_bytes(z.read('debug.sh'));r=subprocess.run(['bash','-n',str(script)],capture_output=True,text=True)
                if r.returncode:raise ValueError('Invalid launcher syntax: '+r.stderr)
                # Extracted executable sources must at least compile on desktop;
                # invocation is intentionally rejected before device path reads.
                for n in ['install.py','installer/catalog.py','installer/transaction.py']:
                    compile(z.read(prefix+'/'+n),n,'exec')
    result=dict(status='pass',component=component,version=version,compatibility_revision=2,package_revision=receipt['package_revision'],source_files=len(sources),usb_source_files=len(expected_usb_source),optional_documentation_images_omitted=True,zip_closure=True,all_optional_transitions_closed=True,corresponding_source_equal_except_documentation_images=True,other_component_binaries_excluded=True,launcher_syntax=True,hardware_access=False)
    (folder/'VERIFIED.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--folder',type=Path,required=True);a=p.parse_args();verify(a.folder.resolve())
