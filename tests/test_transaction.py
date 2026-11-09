# SPDX-License-Identifier: MIT
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'installer'))
from transaction import Transaction, digest, file_hash, metadata, regular, safe


class PowerCut(BaseException):pass


def candidate():
    release=json.loads((ROOT/'release.json').read_text())
    data={}
    for base,prefix in [(ROOT/'integration/firmware407','home/debian/UI/'),(ROOT/'ui','home/debian/UI/'),
                        (ROOT/'bundle','usr/lib/lv2/mala.lv2/')]:
        for p in base.rglob('*'):
            if p.is_file():data[prefix+str(p.relative_to(base))]=p.read_bytes()
    # Filesystem transaction tests never load this stand-in ELF.
    data['usr/lib/lv2/mala.lv2/mala.so']=b'fixture-ARM-plugin-not-executed'
    manifest={k:release[k] for k in ['version','hardware','firmware','architecture','sample_rate','ports','plugin_uri']}
    manifest.update(schema='mala-hector/public-beta/1',guards={'home/debian/UI/qml/module_info.js':digest(b'fixture-catalog')},
        require_absent=['home/debian/UI/qml/mala','usr/lib/lv2/mala.lv2'],
        files=[dict(path=n,size=len(raw),sha256=digest(raw),before_sha256=release['stock_sha256'].get(n)) for n,raw in sorted(data.items())])
    return manifest,data


class TransactionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.base=Path(self.temp.name)
        self.root=self.base/'root';shutil.copytree(ROOT/'tests/fixtures/stock407',self.root)
        self.catalog=self.root/'home/debian/UI/qml/module_info.js';self.catalog.write_bytes(b'fixture-catalog')
        (self.root/'presets').mkdir();(self.root/'presets/owner.txt').write_bytes(b'owner recording and preset placeholder')
        self.store=self.base/'private';self.store.mkdir(mode=0o700)
        self.key=os.urandom(32);self.manifest,self.payload=candidate()
        self.before={str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.tx=Transaction(self.root,self.store,self.key)
    def tearDown(self):self.temp.cleanup()
    def prepare(self):self.tx.prepare(self.manifest,self.payload,'unit-fixture','boot-fixture')
    def snapshot(self):return {str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
    def test_real_public_407_preimages_and_34_file_round_trip(self):
        self.prepare();self.tx.apply(self.payload);self.tx.verify_installed()
        fresh=Transaction(self.root,self.store,self.key);fresh.load();fresh.rollback()
        self.assertEqual(self.snapshot(),self.before)
        fresh.rollback();self.assertEqual(self.snapshot(),self.before)
    def test_original_metadata_round_trip(self):
        p=self.root/'home/debian/UI/show_widget.py';p.chmod(0o640);os.utime(str(p),ns=(1234567890000000000,1234567890000000000))
        if hasattr(os,'setxattr'):os.setxattr(str(p),'user.mala_fixture',b'test')
        before=metadata(p);self.prepare();self.tx.apply(self.payload);self.tx.rollback();after=metadata(p)
        for field in ['mode','uid','gid','mtime_ns','xattrs']:self.assertEqual(after[field],before[field])
    def test_edited_stock_refuses_before_target_writes(self):
        p=self.root/'home/debian/UI/show_widget.py';p.write_bytes(b'other community change');snapshot=self.snapshot()
        with self.assertRaises(ValueError):self.prepare()
        self.assertEqual(self.snapshot(),snapshot);self.assertFalse((self.store/'journal.json').exists())
    def test_corrupt_payload_refused(self):
        name=next(iter(self.payload));self.payload[name]+=b'corruption'
        with self.assertRaises(ValueError):self.prepare()
        self.assertEqual(self.snapshot(),self.before)
    def test_existing_addition_refused(self):
        p=self.root/'home/debian/UI/qml/mala';p.mkdir()
        with self.assertRaises(ValueError):self.prepare()
    def test_symbolic_and_hard_links_refused(self):
        p=self.root/'home/debian/UI/show_widget.py';other=self.base/'other';p.rename(other);p.symlink_to(other)
        with self.assertRaises(ValueError):self.prepare()
        p.unlink();os.link(str(other),str(p))
        with self.assertRaises(ValueError):self.prepare()
    def test_rollback_preserves_unknown_edits(self):
        self.prepare();self.tx.apply(self.payload);p=self.root/'home/debian/UI/show_widget.py';p.write_bytes(b'user edit')
        snapshot=self.snapshot()
        with self.assertRaises(ValueError):self.tx.rollback()
        self.assertEqual(self.snapshot(),snapshot)
    def test_journal_tamper_refused(self):
        self.prepare();p=self.store/'journal.json';r=json.loads(p.read_text());r['content']['phase']='committed';p.write_text(json.dumps(r))
        with self.assertRaises(ValueError):Transaction(self.root,self.store,self.key).load()
    def test_new_nested_content_is_preserved_during_rollback(self):
        self.prepare();self.tx.apply(self.payload)
        p=self.root/'home/debian/UI/qml/mala/user-note.txt';p.write_bytes(b'keep')
        self.tx.rollback();self.assertEqual(p.read_bytes(),b'keep')
    def test_known_full_staging_file_is_cleaned_before_restoration(self):
        self.prepare();row=self.tx.record['files'][0];p=self.root/row['path']
        self.tx.temp_path(p).write_bytes(self.payload[row['path']])
        self.tx.rollback();self.assertEqual(self.snapshot(),self.before)
    def test_unknown_partial_staging_file_is_preserved(self):
        self.prepare();row=self.tx.record['files'][0];p=self.root/row['path']
        staged=self.tx.temp_path(p);staged.write_bytes(b'unknown partial bytes')
        before=self.snapshot()
        with self.assertRaises(ValueError):self.tx.rollback()
        self.assertEqual(self.snapshot(),before)
    def test_completed_restoration_is_verified_exactly(self):
        self.prepare();self.tx.apply(self.payload);self.tx.rollback()
        self.tx.verify_restored()
        p=self.root/'home/debian/UI/show_widget.py';p.write_bytes(self.payload['home/debian/UI/show_widget.py'])
        with self.assertRaises(ValueError):self.tx.verify_restored()
    def test_unknown_paths_rejected(self):
        self.manifest['files'][0]['path']='../../etc/shadow'
        with self.assertRaises(ValueError):self.prepare()
    def test_interrupted_publication_at_each_file_is_recoverable(self):
        for cutoff in range(34):
            with self.subTest(file=cutoff):
                self.prepare();counter=[0]
                def interrupt(stage,name):
                    if stage=='after':
                        if counter[0]==cutoff:raise PowerCut()
                        counter[0]+=1
                with self.assertRaises(PowerCut):self.tx.apply(self.payload,interrupt)
                fresh=Transaction(self.root,self.store,self.key);fresh.load();fresh.rollback()
                self.assertEqual(self.snapshot(),self.before)
                (self.store/'journal.json').unlink()
    def test_interrupted_rollback_can_resume_at_each_file(self):
        for cutoff in range(34):
            with self.subTest(file=cutoff):
                self.prepare();self.tx.apply(self.payload);counter=[0]
                def interrupt(stage,name):
                    if stage=='after_restore':
                        if counter[0]==cutoff:raise PowerCut()
                        counter[0]+=1
                with self.assertRaises(PowerCut):self.tx.rollback(interrupt)
                fresh=Transaction(self.root,self.store,self.key);fresh.load();fresh.rollback()
                self.assertEqual(self.snapshot(),self.before)
                (self.store/'journal.json').unlink()


if __name__=='__main__':unittest.main()
