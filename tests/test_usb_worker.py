# SPDX-License-Identifier: MIT
"""Actual worker/capture paths; only device,mounts,services and reboot simulated."""
import importlib.util,itertools,json,os,sys,unittest,hashlib,tempfile
from pathlib import Path
from unittest.mock import patch
import test_transaction as fixture
from transaction import Transaction,canonical,digest
import catalog as policy
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('community_usb_entry',ROOT/'install.py');entry=importlib.util.module_from_spec(spec);spec.loader.exec_module(entry);REAL_DEVICE=entry.Device
class USBWorkerTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixture.TransactionTests();self.fixture.setUp();f=self.fixture;self.data=f.base/'data';self.data.mkdir();(self.data/'transactions').mkdir();(self.data/'operations').mkdir();(self.data/'key').write_bytes(f.key)
        self.usb=f.base/'usb';self.usb.mkdir();self.events=[];self.failure=None;self.boot='boot-fixture';self.write_count=0;self.retire_allowed=False;parent=self
        class FakeDevice:
            identity='fixture-unit';usb_device=123;readonly_pending_reboot=False
            def __init__(self):self.boot=parent.boot;self.pause_files=[];self.services=entry.SERVICES;self.readonly_calls=0
            def check_mounts(self,mode):
                if parent.failure=='layout':raise ValueError('Changed mount layout')
            def lock(self):return os.open(str(parent.data/'lock'),os.O_CREAT|os.O_RDWR,0o600)
            def baseline(self,manifest,payload):Transaction(f.root,f.base/'unused',f.key).preflight(manifest,payload)
            def latest(self):
                marker=parent.data/'latest.json'
                if not marker.exists():return None
                token=json.loads(marker.read_text())['id'];tx=Transaction(f.root,parent.data/'transactions'/token,f.key);tx.load()
                if tx.record['identity']!=self.identity:raise ValueError('Wrong device backup')
                return tx
            def init_data(self):pass
            def retire_inactive_reservation(self,action):
                marker=parent.data/'active.json'
                if marker.exists():
                    if not parent.retire_allowed or action!='rollback' or json.loads(marker.read_text())['component']!=entry.KIT_COMPONENT:raise ValueError('Already active')
                    marker.unlink()
            def select_services(self,component):self.services=entry.SERVICES+(entry.OWNED_SERVICES if component=='network-link' else ())
            def pause(self):
                self.pause_files=['fixture'];parent.events.append(('pause',self.services));parent.events.append(('stop-timeout',REAL_DEVICE.stop_timeout(self)))
                if parent.failure=='pause':raise ValueError('Injected pause failure')
            def writable(self):parent.events.append('rw');parent.write_count+=1
            def readonly(self):
                self.readonly_calls+=1;parent.events.append('ro')
                if parent.failure=='ro' and self.readonly_calls==1:raise RuntimeError('Injected read-only refusal')
            def report(self,status,detail):parent.events.append(('report',status,detail))
            def reboot(self):parent.events.append('reboot')
            def resume_before_write(self,services):parent.events.append('resume')
        self.FakeDevice=FakeDevice
        self.patches=[patch.object(entry,'DATA',self.data),patch.object(entry,'LOWER',f.root),patch.object(entry,'USB',self.usb),patch.object(entry,'Device',FakeDevice),patch.object(entry,'protected',lambda *a:None),patch.object(entry,'legacy_busy',lambda:None),patch.object(entry,'command',lambda *a,**k:'ActiveState=active\n'),patch.object(entry,'saved_fingerprints',lambda:{p:v[0] for p,v in f.snapshot().items() if p.startswith('mnt/')}),patch.object(entry,'visible_state',lambda d,c:self.visible_checked(d,c))]
        for p in self.patches:p.start()
    def visible_checked(self,device,catalog):
        state=policy.detect(self.fixture.root,catalog);entry.verify_existing_metadata(device,catalog,state);return state
    def tearDown(self):
        for p in reversed(self.patches):p.stop()
        self.fixture.tearDown()
    def kit(self,component):
        folder=self.usb/component;folder.mkdir(exist_ok=True)
        for name in ['install.py','installer/transaction.py','installer/catalog.py']:
            p=folder/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/name).read_bytes())
        (folder/'kit.json').write_text(json.dumps(dict(component=component,version=self.fixture.catalog['components'][component]['version'],catalog_sha256=digest(canonical(self.fixture.catalog)))))
        (folder/'catalog.json').write_text(json.dumps(self.fixture.catalog));(folder/'blobs').mkdir(exist_ok=True)
        for h,raw in self.fixture.blobs.items():(folder/'blobs'/h).write_bytes(raw)
        return folder
    def change(self,component,action,run=True):
        folder=self.kit(component);entry.launch(self.FakeDevice(),folder,action)
        marker=self.data/'active.json'
        if not marker.exists():return None
        token=json.loads(marker.read_text())['operation'];config=self.data/'operations'/token/'operation.json'
        if run:entry.worker(config);self.boot='next-'+token
        return config
    def test_all_install_orders_crossed_with_all_removal_orders_through_actual_worker(self):
        before=self.fixture.snapshot()
        for installs in itertools.permutations(policy.COMPONENTS):
            for removals in itertools.permutations(policy.COMPONENTS):
                with self.subTest(install=installs,remove=removals):
                    current=set()
                    for c in installs:
                        self.change(c,'install');current.add(c);self.assertEqual(set(self.fixture.catalog['states'][policy.detect(self.fixture.root,self.fixture.catalog)]['components']),current)
                    for c in removals:
                        self.change(c,'rollback');current.remove(c);self.assertEqual(set(self.fixture.catalog['states'][policy.detect(self.fixture.root,self.fixture.catalog)]['components']),current)
                    self.assertEqual(self.fixture.snapshot(),before)
    def test_postboot_install_and_remove_checks_do_not_repeat_writes_or_reboots(self):
        self.change('squelch-box','install');writes=self.write_count;self.events=[]
        self.change('squelch-box','install');self.assertEqual(self.write_count,writes);self.assertNotIn('reboot',self.events);self.assertTrue(any(isinstance(v,tuple) and v[:2]==('report','INSTALLED AND VERIFIED') for v in self.events))
        self.change('mala','install');self.change('squelch-box','rollback');writes=self.write_count;self.events=[]
        self.change('squelch-box','rollback');self.assertEqual(self.write_count,writes);self.assertNotIn('reboot',self.events);self.assertEqual(policy.detect(self.fixture.root,self.fixture.catalog),'mala')
    def test_corrupt_captured_payload_never_pauses(self):
        config=self.change('squelch-box','install',False);manifest=json.loads((config.parent/'package/manifest.json').read_text());r=next(r for r in manifest['files'] if r['sha256']);(config.parent/'package/blobs'/r['sha256']).write_bytes(b'corrupt');self.events=[]
        with self.assertRaises(ValueError):entry.worker(config)
        self.assertFalse(any(isinstance(v,tuple) and v[0]=='pause' for v in self.events));self.assertEqual(policy.detect(self.fixture.root,self.fixture.catalog),'stock407')
    def test_changed_boot_never_pauses(self):
        config=self.change('squelch-box','install',False);self.boot='unexpected';self.events=[]
        with self.assertRaises(ValueError):entry.worker(config)
        self.assertNotIn('rw',self.events)
    def test_pause_failure_resumes_and_keeps_preimages(self):
        config=self.change('squelch-box','install',False);before=self.fixture.snapshot();self.failure='pause';self.events=[]
        with self.assertRaises(ValueError):entry.worker(config)
        self.assertEqual(self.fixture.snapshot(),before);self.assertIn('resume',self.events);self.assertNotIn('rw',self.events)
    def test_readonly_failure_restores_previous_modules_and_reboots(self):
        self.change('mala','install');before=self.fixture.snapshot();config=self.change('squelch-box','install',False);self.failure='ro';self.events=[]
        with self.assertRaises(RuntimeError):entry.worker(config)
        self.assertEqual(self.fixture.snapshot(),before);self.assertIn('reboot',self.events);self.assertEqual(policy.detect(self.fixture.root,self.fixture.catalog),'mala')
    def test_inventory_tamper_refused_before_a_new_operation(self):
        self.change('mala','install');p=self.data/'components.json';r=json.loads(p.read_text());r['content']['state']='stock407';p.write_text(json.dumps(r));before=self.fixture.snapshot()
        with self.assertRaises(ValueError):self.change('squelch-box','install')
        self.assertEqual(self.fixture.snapshot(),before)
    def test_stale_recovery_is_component_specific(self):
        config=self.change('squelch-box','install',False)
        with self.assertRaises(ValueError):entry.launch(self.FakeDevice(),self.kit('mala'),'rollback')
        self.assertEqual(policy.detect(self.fixture.root,self.fixture.catalog),'stock407')
    def test_network_transition_alone_pauses_owned_services(self):
        self.change('squelch-box','install');self.events=[];self.change('network-link','install')
        pauses=[v[1] for v in self.events if isinstance(v,tuple) and v[0]=='pause'];self.assertTrue(set(entry.OWNED_SERVICES).issubset(pauses[0]));self.assertEqual(policy.detect(self.fixture.root,self.fixture.catalog),'network-link+squelch-box');self.assertIn(('stop-timeout',300),self.events)
    def test_restored_error_install_usb_does_not_automatically_retry(self):
        self.change('mala','install');config=self.change('squelch-box','install',False);self.failure='ro'
        with self.assertRaises(RuntimeError):entry.worker(config)
        self.boot='after-error-reboot';self.failure=None;self.events=[];writes=self.write_count
        self.change('squelch-box','install');self.assertFalse((self.data/'active.json').exists());self.assertEqual(self.write_count,writes);self.assertEqual(policy.detect(self.fixture.root,self.fixture.catalog),'mala')
        self.assertTrue(any(isinstance(v,tuple) and v[:2]==('report','RECOVERY VERIFIED; NO RETRY') for v in self.events))
        # Further boots with the same USB remain blocked until acknowledgement.
        self.boot='yet-another-reboot';self.change('squelch-box','install');self.assertEqual(self.write_count,writes)
        self.change('squelch-box','rollback');self.change('squelch-box','install');self.assertEqual(policy.detect(self.fixture.root,self.fixture.catalog),'mala+squelch-box')
    def test_interrupted_removal_recovery_does_not_retry_on_rollback_usb(self):
        self.change('mala','install');self.change('squelch-box','install');before=self.fixture.snapshot();config=self.change('squelch-box','rollback',False)
        original=Transaction.apply
        def interrupted(tx,payload):
            def cut(stage,name):
                if stage=='after':raise fixture.PowerCut()
            return original(tx,payload,cut)
        with patch.object(Transaction,'apply',interrupted):
            with self.assertRaises(fixture.PowerCut):entry.worker(config)
        self.boot='after-cut';self.retire_allowed=True;recover=self.change('squelch-box','rollback');self.assertEqual(self.fixture.snapshot(),before)
        self.events=[];writes=self.write_count;self.change('squelch-box','rollback');self.assertEqual(self.write_count,writes);self.assertEqual(self.fixture.snapshot(),before)
        self.assertTrue(any(isinstance(v,tuple) and v[:2]==('report','RECOVERY VERIFIED; NO RETRY') for v in self.events))
        self.change('squelch-box','install');self.change('squelch-box','rollback');self.assertEqual(policy.detect(self.fixture.root,self.fixture.catalog),'mala')
    def test_stale_committed_outcome_never_hides_new_restored_journal(self):
        self.change('squelch-box','install');before=self.fixture.snapshot();config=self.change('squelch-box','rollback',False);self.failure='ro';original=entry.write_outcome
        def cut(device,catalog,config,state,outcome):
            if outcome=='restored-after-error':raise fixture.PowerCut()
            return original(device,catalog,config,state,outcome)
        with patch.object(entry,'write_outcome',cut):
            with self.assertRaises(fixture.PowerCut):entry.worker(config)
        self.boot='after-outcome-power-cut';self.failure=None;self.retire_allowed=True;writes=self.write_count;self.events=[]
        self.change('squelch-box','rollback');self.assertEqual(self.write_count,writes);self.assertFalse((self.data/'active.json').exists());self.assertEqual(self.fixture.snapshot(),before)
        self.assertTrue(any(isinstance(v,tuple) and v[:2]==('report','RECOVERY VERIFIED; NO RETRY') for v in self.events))
        self.change('squelch-box','install');self.change('squelch-box','rollback');self.assertEqual(policy.detect(self.fixture.root,self.fixture.catalog),'stock407')
    def test_postboot_hash_match_with_nonexecutable_network_helper_refused(self):
        self.change('network-link','install');p=self.fixture.root/'usr/local/lib/hector-link-sync/helper';p.chmod(0o644);self.events=[]
        with self.assertRaises(ValueError):self.change('network-link','install')
        self.assertFalse(any(isinstance(v,tuple) and v[:2]==('report','INSTALLED AND VERIFIED') for v in self.events))
    def test_postboot_preserved_file_metadata_change_refused(self):
        self.change('mala','install');self.change('squelch-box','install');p=self.fixture.root/'home/debian/UI/show_widget.py';st=p.stat();os.utime(p,ns=(st.st_atime_ns,st.st_mtime_ns+1000000))
        with self.assertRaises(ValueError):self.change('squelch-box','install')
    def test_legacy_component_nonexecutable_mode_refused(self):
        self.fixture.put_state('network-link');p=self.fixture.root/'usr/local/lib/hector-link-sync/helper';p.chmod(0o644)
        with self.assertRaises(ValueError):self.change('squelch-box','install')
    def test_desktop_refused_before_hardware_path_reads(self):
        with patch.object(entry.os,'geteuid',lambda:1000),patch.object(entry.Path,'read_bytes',side_effect=AssertionError('Hardware read')):
            with self.assertRaises(ValueError):entry.hardware()
class SavedAssetTests(unittest.TestCase):
    def test_large_presets_stream_in_bounded_memory(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);path=root/'large-frozen-buffer.bin';block=b'0123456789abcdef'*65536;h=hashlib.sha256()
            with path.open('wb') as f:
                for _ in range(12):f.write(block);h.update(block)
            sizes=[];read=entry.os.read
            def measured(fd,n):sizes.append(n);return read(fd,n)
            with patch.object(entry.os,'read',measured):result=entry.saved_tree(root)
            self.assertEqual(result,{'large-frozen-buffer.bin':h.hexdigest()});self.assertGreater(path.stat().st_size,8*1024*1024);self.assertLessEqual(max(sizes),1024*1024)
    def test_stock_and_network_shutdown_budgets(self):
        d=object.__new__(REAL_DEVICE);d.services=entry.SERVICES;self.assertEqual(d.stop_timeout(),60)
        d.services=entry.SERVICES+entry.OWNED_SERVICES;self.assertGreaterEqual(d.stop_timeout(),150);self.assertLessEqual(d.stop_timeout(),300)
if __name__=='__main__':unittest.main(verbosity=2)
