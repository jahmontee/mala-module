# SPDX-License-Identifier: MIT
"""Regressions specific to beta6 upgrades and authenticated catalog migration."""
import hashlib
import hmac
import json
import unittest
import test_usb_worker as worker
from transaction import Transaction, canonical
import catalog as policy


class UpgradeTests(unittest.TestCase):
    def setUp(self):
        self.worker = worker.USBWorkerTests()
        self.worker.setUp()

    def tearDown(self):
        self.worker.tearDown()

    def legacy_install(self):
        w = self.worker
        catalog = w.fixture.catalog
        old_digest = next(iter(catalog['legacy_catalogs']))
        before = catalog['states']['stock407']['files']
        after = catalog['states']['mala~mala-beta6']['files']
        manifest = policy.transition(catalog, 'stock407', 'mala', 'install')
        manifest.update(version='0.1.0-beta.6', catalog_sha256=old_digest, to_state='mala')
        manifest['files'] = [dict(path=path, before_sha256=before[path], sha256=value,
                                  size=catalog['artifacts'].get(value, {}).get('size', 0),
                                  mode=catalog['artifacts'].get(value, {}).get('mode', 0o644))
                             for path, value in after.items() if before[path] != value]
        manifest['file_count'] = len(manifest['files'])
        manifest['guards'] = dict(catalog['guards'], **{path: value for path, value in before.items()
                                                       if after[path] == value})
        payload = {row['path']: w.fixture.blobs[row['sha256']] for row in manifest['files']}
        token = '1' * 32
        store = w.data / 'transactions' / token
        store.mkdir()
        tx = Transaction(w.fixture.root, store, w.fixture.key)
        tx.prepare(manifest, payload, 'fixture-unit', w.boot)
        tx.apply(payload)
        (w.data / 'latest.json').write_text(json.dumps(dict(id=token)))
        record = dict(schema=1, identity='fixture-unit', catalog_sha256=old_digest,
                      state='mala', components={'mala': catalog['legacy_catalogs'][old_digest]['components']['mala']},
                      transaction=token)
        self.authenticated(w.data / 'components.json', record)
        return tx, record

    def authenticated(self, path, record):
        key = self.worker.fixture.key
        path.parent.mkdir(parents=True, exist_ok=True)
        envelope = dict(content=record, hmac=hmac.new(key, canonical(record), hashlib.sha256).hexdigest())
        path.write_bytes(canonical(envelope))

    def test_beta6_upgrades_in_place_in_all_four_companion_sets(self):
        w = self.worker
        for base in ('mala', 'mala+network-link', 'mala+squelch-box', 'mala+network-link+squelch-box'):
            with self.subTest(state=base):
                w.fixture.put_state(base + policy.LEGACY_SUFFIX)
                before = w.fixture.snapshot()
                tx, manifest, payload = w.fixture.change('mala', 'install')
                self.assertEqual(policy.detect(w.fixture.root, w.fixture.catalog), base)
                self.assertTrue(all(row['path'].startswith('home/debian/UI/') for row in manifest['files']))
                for path, value in manifest['guards'].items():
                    if value is not None:
                        self.assertEqual(w.fixture.snapshot()[path], before[path])
                tx.rollback()
                self.assertEqual(w.fixture.snapshot(), before)
                # Clear the fixture back to stock for the next independent set.
                for component in list(w.fixture.catalog['states'][base]['components']):
                    w.fixture.change(component, 'rollback')

    def test_companion_changes_retain_beta6_until_mala_is_updated(self):
        w = self.worker
        w.fixture.put_state('mala' + policy.LEGACY_SUFFIX)
        editor = w.fixture.root / 'home/debian/UI/qml/mala/Editor.qml'
        original = editor.read_bytes()
        w.change('squelch-box', 'install')
        self.assertEqual(policy.detect(w.fixture.root, w.fixture.catalog), 'mala+squelch-box' + policy.LEGACY_SUFFIX)
        self.assertEqual(editor.read_bytes(), original)
        w.change('mala', 'install')
        self.assertEqual(policy.detect(w.fixture.root, w.fixture.catalog), 'mala+squelch-box')

    def test_authenticated_compat1_inventory_migrates_through_real_worker(self):
        self.legacy_install()
        w = self.worker
        w.change('mala', 'install')
        self.assertEqual(policy.detect(w.fixture.root, w.fixture.catalog), 'mala')
        w.change('mala', 'install')
        self.assertEqual(json.loads((w.data / 'components.json').read_text())['content']['catalog_sha256'],
                         worker.digest(canonical(w.fixture.catalog)))

    def test_unknown_authenticated_old_catalog_is_refused_before_writes(self):
        _, record = self.legacy_install()
        record['catalog_sha256'] = 'f' * 64
        w = self.worker
        self.authenticated(w.data / 'components.json', record)
        before = w.fixture.snapshot()
        with self.assertRaises(ValueError):
            w.change('mala', 'install')
        self.assertEqual(w.fixture.snapshot(), before)
        self.assertEqual(w.write_count, 0)

    def test_legacy_component_version_mismatch_is_refused(self):
        _, record = self.legacy_install()
        record['components']['mala'] = dict(version='unknown')
        w = self.worker
        self.authenticated(w.data / 'components.json', record)
        with self.assertRaises(ValueError):
            w.change('mala', 'install')
        self.assertEqual(w.write_count, 0)

    def test_legacy_recovery_outcome_still_blocks_automatic_retry(self):
        tx, record = self.legacy_install()
        w = self.worker
        outcome = dict(schema=1, identity='fixture-unit', catalog_sha256=record['catalog_sha256'],
                       component='mala', action='install', transaction=tx.record['id'],
                       state='mala', outcome='restored-after-error', old_boot='old')
        self.authenticated(w.data / 'outcomes/mala.json', outcome)
        w.change('mala', 'install')
        self.assertEqual(policy.detect(w.fixture.root, w.fixture.catalog), 'mala' + policy.LEGACY_SUFFIX)
        self.assertEqual(w.write_count, 0)
        self.assertTrue(any(isinstance(event, tuple) and event[:2] == ('report', 'RECOVERY VERIFIED; NO RETRY')
                            for event in w.events))


if __name__ == '__main__':
    unittest.main(verbosity=2)
