# SPDX-License-Identifier: MIT
"""Fresh-add defaults must never reset restored or reopened Mala instances."""
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'ui'))
try:
    from PySide2.QtCore import QCoreApplication
    from mala_407 import MalaHub,Control,SPEC,INPUTS,PANEL,KnobResponse,FRESH_KNOB_DEFAULTS
except ImportError:
    QCoreApplication=None

@unittest.skipIf(QCoreApplication is None,'Qt5 development runtime required')
class FreshDefaultsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QCoreApplication.instance() or QCoreApplication([])
    def setUp(self):
        self.effects={};self.writes=[];self.loading=SimpleNamespace(value=False)
        parent=self
        class Knobs:
            def ui_knob_change(self,name,symbol,value):
                parent.writes.append((name,symbol,value));parent.effects[name]['controls'][symbol].update(value)
        self.knobs=Knobs()
        self.hub=MalaHub(self.effects,{},self.knobs,SimpleNamespace(set_broadcast=lambda *a:None),self.loading,hardware='hector')
    def add(self,name='/main/mala1',fresh=False,saved=None):
        record=dict(effect_type='mala',enabled=SimpleNamespace(value=True),
            controls={s:Control(p,None) for s,p in SPEC.items() if s in INPUTS},
            broadcast_ports={s:Control(p,None) for s,p in SPEC.items() if s not in INPUTS})
        for s,v in (saved or {}).items():record['controls'][s].update(v)
        self.effects[name]=record
        if fresh:self.hub.expect_new(name)
        self.hub.created(name)
        return record
    def values(self,name='/main/mala1'):
        return {s:self.effects[name]['controls'][s].value for s in PANEL}
    def test_new_add_initializes_all_twelve_knobs_once(self):
        self.add(fresh=True);self.hub.flush()
        expected=dict(time=.5,size=.5,shape=.5,pitch=0.,density=.5,time_amount=0.,size_amount=0.,shape_amount=0.,pitch_amount=0.,feedback=0.,mix=.5,reverb=0.)
        self.assertEqual(self.values(),expected)
        self.assertEqual(set(expected),set(PANEL))
        self.assertEqual(self.effects['/main/mala1']['controls']['panel_response'].value,1)
        count=len(self.writes);self.hub.flush();self.assertEqual(len(self.writes),count)
    def test_existing_instance_and_other_module_unchanged(self):
        saved=dict(time=.13,size=.77,shape=.22,pitch=7.,density=.81,time_amount=.4,size_amount=-.2,shape_amount=.9,pitch_amount=-.7,feedback=.31,mix=.92,reverb=.64)
        self.add(saved=saved);self.add('/main/mala2',fresh=True);self.hub.flush()
        self.assertEqual(self.values(),saved)
        self.assertFalse(any(n=='/main/mala1' and s in PANEL for n,s,v in self.writes))
    def test_preset_load_clears_pending_fresh_initialization(self):
        self.add(fresh=True);self.loading.value=True;self.hub.begin_load()
        saved=dict(feedback=.36,mix=.89,reverb=.28,time=.14,density=.91)
        self.add(saved=saved);before=self.values();self.hub.flush();self.assertFalse(self.writes)
        self.loading.value=False;self.hub.flush();self.assertEqual(self.values(),before)
        self.assertFalse(any(s in PANEL for n,s,v in self.writes))
    def test_deleted_pending_module_is_not_initialized(self):
        self.add(fresh=True);self.hub.retire('/main/mala1');self.effects.clear();self.hub.flush()
        self.assertFalse(self.writes)
    @unittest.skipUnless((ROOT/'build/native/mala.lv2/mala.so').exists(),'Build the native Mala lookup library')
    def test_real_knob_positions_and_reopen_preserves_edits(self):
        self.hub.response=KnobResponse(ROOT/'build/native/mala.lv2/mala.so')
        self.add(fresh=True);self.hub.flush();editor=self.hub.bridge('/main/mala1')
        for symbol in PANEL:
            self.assertAlmostEqual(editor.positions[symbol],0. if symbol in ['feedback','reverb'] else .5,delta=2/65536,msg=symbol)
        editor.change('time',.23);editor.change('mix',.78);editor.change('pitch',7)
        saved=self.values();self.writes.clear();self.hub.release(editor)
        self.hub.bridge('/main/mala1');self.hub.flush();self.assertEqual(self.values(),saved)
        self.assertFalse(any(s in PANEL for n,s,v in self.writes))
        self.hub.created('/main/mala1');self.hub.bridge('/main/mala1');self.hub.flush()
        self.assertEqual(self.values(),saved)
        self.assertFalse(any(s in PANEL for n,s,v in self.writes))

if __name__=='__main__':unittest.main()
