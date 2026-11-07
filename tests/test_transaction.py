# SPDX-License-Identifier: MIT
"""All optional add-on installation/removal orders and interruption recovery."""
import copy,importlib.util,itertools,json,os,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'installer'))
from transaction import Transaction,digest,canonical,metadata,safe
import catalog as policy
class PowerCut(BaseException):pass

def fixtures():
    actual=policy.load(ROOT/'provenance/component-catalog.json');catalog=copy.deepcopy(actual);blobs={}
    for state,row in catalog['states'].items():
        for path,h in row['files'].items():
            if h is None:continue
            local=ROOT/'integration/hosts'/state/path.removeprefix('home/debian/UI/')
            raw=local.read_bytes() if local.is_file() else ('non-executed component fixture '+h).encode()
            new=digest(raw);blobs[new]=raw;row['files'][path]=new
            catalog['artifacts'][new]=dict(size=len(raw),mode=actual['artifacts'][h]['mode'])
    for path,h in list(catalog['guards'].items()):
        if h is not None:
            raw=('public firmware guard '+path).encode();catalog['guards'][path]=digest(raw);blobs[digest(raw)]=raw
    return catalog,blobs

class TransactionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.base=Path(self.temp.name);self.root=self.base/'root';self.root.mkdir();self.key=os.urandom(32);self.serial=0
        self.catalog,self.blobs=fixtures();self.state='stock407';self.put_state(self.state)
        p=self.root/'mnt/presets/beebo/owner.ingen/main.ttl';p.parent.mkdir(parents=True);p.write_bytes(b'Owner preset never touched')
        p=self.root/'mnt/pedal_state/WiFi-and-themes';p.parent.mkdir(parents=True);p.write_bytes(b'Owner settings never touched')
    def tearDown(self):self.temp.cleanup()
    def put_state(self,state):
        rows=dict(self.catalog['states'][state]['files'],**self.catalog['guards'])
        for name,h in rows.items():
            if h is not None:
                p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(self.blobs[h]);p.chmod(self.catalog['artifacts'].get(h,{}).get('mode',0o644))
    def snapshot(self):return {str(f.relative_to(self.root)):(f.read_bytes(),{k:v for k,v in metadata(f).items() if k!='atime_ns'}) for f in self.root.rglob('*') if f.is_file()}
    def transaction(self,component,action):
        current=policy.detect(self.root,self.catalog);m=policy.transition(self.catalog,current,component,action)
        if m is None:return None,None,{}
        self.serial+=1;store=self.base/('journal-'+str(self.serial));store.mkdir(mode=0o700)
        tx=Transaction(self.root,store,self.key);payload={r['path']:self.blobs[r['sha256']] for r in m['files'] if r['sha256'] is not None}
        tx.prepare(m,payload,'fixture-unit','fixture-boot');return tx,m,payload
    def change(self,component,action):
        tx,m,payload=self.transaction(component,action)
        if tx is None:return
        tx.apply(payload);tx.verify_installed();self.assertEqual(policy.detect(self.root,self.catalog),m['to_state']);self.state=m['to_state'];return tx,m,payload
    def test_all_six_installation_orders_and_all_independent_removal_orders(self):
        for installs in itertools.permutations(policy.COMPONENTS):
            for removals in itertools.permutations(policy.COMPONENTS):
                with self.subTest(install=installs,remove=removals):
                    before=self.snapshot();installed=set()
                    for c in installs:
                        prior=self.snapshot();tx,m,p=self.change(c,'install');installed.add(c)
                        self.assertEqual(set(self.catalog['states'][policy.detect(self.root,self.catalog)]['components']),installed)
                        for n,h in m['guards'].items():
                            if h is not None:self.assertEqual(self.snapshot()[n],prior[n])
                    for c in removals:
                        prior=self.snapshot();tx,m,p=self.change(c,'rollback');installed.remove(c)
                        self.assertEqual(set(self.catalog['states'][policy.detect(self.root,self.catalog)]['components']),installed)
                        for n,h in m['guards'].items():
                            if h is not None:self.assertEqual(self.snapshot()[n],prior[n])
                    self.assertEqual(self.snapshot(),before)
    def test_install_and_remove_are_idempotent(self):
        before=self.snapshot();self.assertIsNone(policy.transition(self.catalog,'stock407','squelch-box','rollback'))
        self.change('squelch-box','install');after=self.snapshot();self.assertIsNone(policy.transition(self.catalog,'squelch-box','squelch-box','install'));self.assertEqual(self.snapshot(),after)
        self.change('squelch-box','rollback');self.assertEqual(self.snapshot(),before)
    def test_existing_public_mala_and_network_states_are_adopted_without_prior_journal(self):
        for s in ['mala','network-link','mala+network-link']:
            self.put_state(s);self.assertEqual(policy.detect(self.root,self.catalog),s)
            self.change('squelch-box','install');self.change('squelch-box','rollback');self.assertEqual(policy.detect(self.root,self.catalog),s)
            for c in list(self.catalog['states'][s]['components']):self.change(c,'rollback')
    def test_modified_addon_or_unknown_host_refused(self):
        p=self.root/'home/debian/UI/show_widget.py';p.write_bytes(b'Unknown community edit');before=self.snapshot()
        with self.assertRaises(ValueError):self.transaction('squelch-box','install')
        self.assertEqual(self.snapshot(),before)
    def test_corrupt_payload_refused_before_journal(self):
        tx,m,p=self.transaction('squelch-box','install');name=next(iter(p));p[name]+=b'corrupt'
        with self.assertRaises(ValueError):tx.apply(p)
        tx.rollback();self.assertEqual(policy.detect(self.root,self.catalog),'stock407')
    def test_unknown_deletion_target_refused(self):
        m=policy.transition(self.catalog,'stock407','squelch-box','install');m['files'][0]['path']='etc/shadow';store=self.base/'bad';store.mkdir()
        with self.assertRaises(ValueError):Transaction(self.root,store,self.key).prepare(m,{},'i','b')
    def test_all_publication_boundaries_restore_the_exact_previous_state(self):
        self.change('mala','install');self.change('network-link','install')
        for action in ['install','rollback']:
            if action=='rollback':self.change('squelch-box','install')
            m=policy.transition(self.catalog,policy.detect(self.root,self.catalog),'squelch-box',action)
            for boundary in range(len(m['files'])):
                before=self.snapshot();tx,m,p=self.transaction('squelch-box',action);counter=[0]
                def cut(stage,name):
                    if stage=='after':
                        if counter[0]==boundary:raise PowerCut()
                        counter[0]+=1
                with self.assertRaises(PowerCut):tx.apply(p,cut)
                fresh=Transaction(self.root,tx.store,self.key);fresh.load();fresh.rollback();self.assertEqual(self.snapshot(),before)
    def test_removal_failure_restores_binary_and_preserves_other_modules(self):
        for c in policy.COMPONENTS:self.change(c,'install')
        before=self.snapshot();tx,m,p=self.transaction('mala','rollback')
        def cut(stage,name):
            if stage=='after' and name.endswith('/mala.so'):raise PowerCut()
        with self.assertRaises(PowerCut):tx.apply(p,cut)
        tx.load();tx.rollback();self.assertEqual(self.snapshot(),before)
    def test_unknown_edits_or_metadata_stop_recovery(self):
        tx,m,p=self.transaction('squelch-box','install');tx.apply(p);path=self.root/m['files'][0]['path'];path.write_bytes(b'Later user edit');before=self.snapshot()
        with self.assertRaises(ValueError):tx.rollback()
        self.assertEqual(self.snapshot(),before)
    def test_modified_preserved_component_metadata_refused(self):
        self.change('mala','install');tx,m,p=self.transaction('squelch-box','install');f=self.root/'usr/lib/lv2/mala.lv2/mala.so';f.chmod(0o600)
        with self.assertRaises(ValueError):tx.apply(p)
    def test_journal_authentication_refuses_tampering(self):
        tx,m,p=self.transaction('squelch-box','install');f=tx.store/'journal.json';j=json.loads(f.read_text());j['content']['phase']='committed';f.write_text(json.dumps(j))
        with self.assertRaises(ValueError):tx.load()
    def test_symlink_and_hardlink_targets_refused(self):
        path=self.root/'home/debian/UI/show_widget.py';raw=path.read_bytes();other=self.base/'other';other.write_bytes(raw);path.unlink();path.symlink_to(other)
        with self.assertRaises(ValueError):self.transaction('squelch-box','install')
        path.unlink();os.link(other,path)
        with self.assertRaises(ValueError):self.transaction('squelch-box','install')
    def test_unowned_nested_file_survives_remove(self):
        self.change('squelch-box','install');p=self.root/'home/debian/UI/qml/poly303/user-note.txt';p.write_bytes(b'Unowned user note');self.change('squelch-box','rollback');self.assertEqual(p.read_bytes(),b'Unowned user note')
if __name__=='__main__':unittest.main(verbosity=2)
