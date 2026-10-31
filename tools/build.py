#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build Mala from the complete, locked public source subset. No installation."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def build(output, compiler='g++'):
    if output.exists():
        raise ValueError('Use a fresh build output directory')
    for row in json.loads((ROOT/'provenance/source-lock.json').read_text())['files']:
        raw=(ROOT/row['path']).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=row['sha256']:
            raise ValueError('Vendored source differs: '+row['path'])
    output.mkdir(parents=True)
    bundle=output/'mala.lv2';bundle.mkdir()
    for p in (ROOT/'bundle').iterdir():
        shutil.copyfile(p,bundle/p.name)
    core=[ROOT/('vendor/beads/dsp/'+n+'.cc') for n in
          ['processor','mu_law','delay_clock','delay_controller','trigger_generator','synth']]
    core += [ROOT/'vendor/beads/resources.cc',ROOT/'vendor/stmlib/dsp/units.cc',
             ROOT/'vendor/beads/gain_control.cc',ROOT/'build-support/overlay/stmlib/utils/random.cc']
    args=[compiler,'-std=gnu++17','-O2','-DTEST','-include','cstdio','-fno-fast-math','-fPIC','-fvisibility=hidden',
          '-I'+str(ROOT/'build-support/overlay'),'-I'+str(ROOT/'vendor/lv2-headers'),
          '-I'+str(ROOT/'vendor'),'-shared',str(ROOT/'src/dsp/mala.cpp')]
    args += [str(p) for p in core] + ['-o',str(bundle/'mala.so')]
    if 'aarch64' in Path(compiler).name:
        args[1:1]=['-march=armv8-a','-mtune=generic']
    p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,universal_newlines=True)
    (output/'compiler.log').write_text(p.stdout)
    if p.returncode:
        raise RuntimeError(p.stdout[-5000:])
    report=dict(compiler=compiler,sha256=hashlib.sha256((bundle/'mala.so').read_bytes()).hexdigest(),
                version=json.loads((ROOT/'release.json').read_text())['version'])
    (output/'build.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))
    return bundle


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=ROOT/'build/native')
    p.add_argument('--compiler',default=os.environ.get('CXX','g++'))
    a=p.parse_args();build(a.output.resolve(),a.compiler)
