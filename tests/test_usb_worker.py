# SPDX-License-Identifier: MIT
"""Device worker orchestration with simulated services/mounts/reboot only."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import test_transaction as fixture
from transaction import Transaction, file_hash
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('mala_usb_entry',ROOT/'install.py')
entry=importlib.util.module_from_spec(spec);spec.loader.exec_module(entry)


class USBWorkerTests(fixture.TransactionTests):
    # Reuse setup helpers, not the parent's tests (they remain tested once below).
    def setUp(self):
        super().setUp()
        self.data=self.base/'data';self.data.mkdir()
        (self.data/'transactions').mkdir();(self.data/'operations').mkdir();(self.data/'key').write_bytes(self.key)
        self.token='a'*32;self.op=self.data/'operations'/self.token;self.op.mkdir()
        self.package=self.op/'package';self.package.mkdir()
        (self.package/'manifest.json').write_text(json.dumps(self.manifest))
        for name,raw in self.payload.items():
            p=self.package/'payload'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
        self.config=dict(id=self.token,action='install',identity='unit-fixture',boot='boot-fixture',usb_device=123,transaction=self.token)
        self.config_path=self.op/'operation.json';self.config_path.write_text(json.dumps(self.config))
        (self.data/'active.json').write_text(json.dumps(dict(operation=self.token)))
        self.events=[];self.failure=None;parent=self
        class FakeDevice:
            identity='unit-fixture';boot='boot-fixture';usb_device=123;readonly_pending_reboot=False
            def __init__(self):self.pause_files=[];self.readonly_calls=0
            def lock(self):return os.open(str(parent.data/'lock'),os.O_CREAT|os.O_RDWR,0o600)
            def baseline(self,manifest,payload):
                Transaction(parent.root,parent.store,parent.key).preflight(manifest,payload)
            def latest(self):
                marker=json.loads((parent.data/'latest.json').read_text())
                tx=Transaction(parent.root,parent.data/'transactions'/marker['id'],parent.key);tx.load();return tx
            def pause(self):
                parent.events.append('pause');self.pause_files=['fixture']
                if parent.failure=='pause':raise RuntimeError('simulated pause failure')
            def writable(self):parent.events.append('rw')
            def readonly(self):
                self.readonly_calls+=1;parent.events.append('ro')
                if parent.failure=='ro' and self.readonly_calls==1:raise RuntimeError('simulated remount error')
            def report(self,status,detail):parent.events.append(('report',status))
            def reboot(self):parent.events.append('reboot')
            def resume_before_write(self,services):parent.events.append('resume')
            def retire_inactive_reservation(self,action):pass
        self.FakeDevice=FakeDevice
        self.patches=[patch.object(entry,'DATA',self.data),patch.object(entry,'LOWER',self.root),
                      patch.object(entry,'Device',FakeDevice),patch.object(entry,'protected',lambda *a:None),
                      patch.object(entry,'command',lambda *a,**k:'ActiveState=active\n')]
        for p in self.patches:p.start()
    def tearDown(self):
        for p in reversed(self.patches):p.stop()
        super().tearDown()
    def worker(self):entry.worker(self.config_path)
    def current(self):return self.FakeDevice().latest()
    def test_worker_install_and_rollback(self):
        self.worker();tx=self.current();self.assertEqual(tx.record['phase'],'committed');tx.verify_installed()
        self.assertEqual(self.events.count('reboot'),1);self.assertFalse((self.data/'active.json').exists())
        self.config['action']='rollback';self.config_path.write_text(json.dumps(self.config));(self.data/'active.json').write_text('{}')
        self.worker();self.assertEqual(self.current().record['phase'],'rolled-back');self.assertEqual(self.snapshot(),self.before)
        self.assertEqual(self.events.count('reboot'),2)
    def test_remount_failure_restores_and_reboots(self):
        self.failure='ro'
        with self.assertRaises(RuntimeError):self.worker()
        self.assertEqual(self.snapshot(),self.before);self.assertEqual(self.current().record['phase'],'rolled-back')
        self.assertEqual(self.events.count('reboot'),1)
    def test_pause_failure_never_attempts_firmware_write(self):
        self.failure='pause'
        with self.assertRaises(RuntimeError):self.worker()
        self.assertNotIn('rw',self.events);self.assertIn('resume',self.events);self.assertEqual(self.snapshot(),self.before)
    def test_worker_corrupt_usb_payload_never_pauses(self):
        p=next((self.package/'payload').rglob('show_widget.py'));p.write_bytes(b'broken')
        with self.assertRaises(ValueError):self.worker()
        self.assertNotIn('pause',self.events);self.assertEqual(self.snapshot(),self.before)
    def test_desktop_refused_before_hardware_metadata(self):
        with patch.object(entry.os,'geteuid',lambda:1000),patch.object(entry.Path,'read_bytes',side_effect=AssertionError('Device path read')):
            with self.assertRaises(ValueError):entry.hardware()
    def test_inactive_reservation_is_only_retired_for_rollback(self):
        d=object.__new__(entry.Device)
        # Device is patched in other cases; call the original class method below.
        with patch.object(entry,'command',lambda *a,**k:'ActiveState=inactive\n'):
            with self.assertRaises(ValueError):REAL_DEVICE.retire_inactive_reservation(d,'install')
            self.assertTrue((self.data/'active.json').exists())
            REAL_DEVICE.retire_inactive_reservation(d,'rollback')
            self.assertFalse((self.data/'active.json').exists())
    def test_active_reservation_never_interrupted(self):
        d=object.__new__(entry.Device)
        with self.assertRaises(ValueError):REAL_DEVICE.retire_inactive_reservation(d,'rollback')
        self.assertTrue((self.data/'active.json').exists())
    def test_existing_install_verification_does_not_repeat_worker(self):
        self.worker();before=self.snapshot();self.events=[]
        device=self.FakeDevice()
        with patch.object(entry,'Path',Path):
            # Visible firmware is simulated by the same fixture root, separately
            # from the production adapter's real mount checks.
            original_safe=entry.safe
            def visible_safe(root,name):return original_safe(self.root if root==Path('/') else root,name)
            with patch.object(entry,'safe',visible_safe):entry.launch(device,self.package,'install')
        self.assertEqual(self.snapshot(),before);self.assertNotIn('pause',self.events);self.assertNotIn('reboot',self.events)
        self.assertIn(('report','INSTALLED AND VERIFIED'),self.events)


# Capture before per-test Device patching.
REAL_DEVICE=entry.Device
# Avoid duplicating inherited core test methods in this orchestration suite.
for name in list(fixture.TransactionTests.__dict__):
    if name.startswith('test_'):setattr(USBWorkerTests,name,None)
