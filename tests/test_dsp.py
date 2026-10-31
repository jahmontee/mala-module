# SPDX-License-Identifier: MIT
"""Actual native source build, synthetic buffers, no audio devices."""
import ctypes
import json
import math
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src/dsp'))
from offline import Instance
BUNDLE=ROOT/'build/native/mala.lv2'
SPEC=json.loads((ROOT/'src/dsp/ports.json').read_text())


@unittest.skipUnless((BUNDLE/'mala.so').is_file(),'Build the native plugin with tools/build.py first')
class DSPTests(unittest.TestCase):
    def instance(self):
        p=Instance(BUNDLE,SPEC,128)
        p.set('input_stage',0);p.set('output_normalization',0);p.set('audio_connections',3);p.set('output_connections',3)
        return p
    def test_58_ports_and_rate_guard(self):
        self.assertEqual(len(SPEC),58);self.assertEqual(SPEC[57]['symbol'],'cv_input_units')
        p=self.instance()
        try:self.assertFalse(p.d.instantiate(p.dp,44100.,str(BUNDLE).encode(),p.features))
        finally:p.close()
    def test_four_qualities_finite_stereo_and_freeze_mode_protection(self):
        for quality in range(4):
            p=self.instance()
            try:
                p.set('quality',quality)
                for block in range(400):
                    for i in range(128):
                        p.buffers['left_in'][i]=.1*math.sin((block*128+i)*.03)
                        p.buffers['right_in'][i]=.07*math.sin((block*128+i)*.071)
                    p.run()
                    self.assertTrue(all(math.isfinite(p.buffers[k][i]) for k in ['left_out','right_out'] for i in range(128)))
                self.assertEqual(p.controls['active_quality'].value,quality)
                p.set('freeze',1);p.run();p.set('quality',(quality+1)%4);p.run()
                self.assertEqual(p.controls['active_quality'].value,quality)
                p.set('freeze',0);p.run();self.assertEqual(p.controls['active_quality'].value,(quality+1)%4)
            finally:p.close()
    def test_hector_x5_cv_equivalence(self):
        p,q=self.instance(),self.instance()
        try:
            for instance in [p,q]:
                instance.set('connections',63);instance.set('time_amount',.6);instance.set('size_amount',.3)
                instance.set('shape_amount',-.2);instance.set('pitch_amount',.7);instance.set('assign_destination',3)
            p.set('cv_input_units',1);q.set('cv_input_units',0)
            for block in range(400):
                for i in range(128):
                    for symbol in ['left_in','right_in']:
                        value=.1*math.sin((block*128+i)*.033)
                        p.buffers[symbol][i]=q.buffers[symbol][i]=value
                    for symbol in ['time_cv','size_cv','shape_cv','pitch_cv','density_cv','assign_cv']:
                        value=.05*math.sin((block*128+i)*.001)
                        p.buffers[symbol][i]=value;q.buffers[symbol][i]=ctypes.c_float(value).value*5
                p.run();q.run()
                for symbol in ['left_out','right_out']:
                    self.assertEqual(list(p.buffers[symbol][:128]),list(q.buffers[symbol][:128]))
        finally:p.close();q.close()


if __name__=='__main__':unittest.main()
