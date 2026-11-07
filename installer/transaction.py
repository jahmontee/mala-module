# SPDX-License-Identifier: MIT
"""Filesystem transaction shared by the device adapter and disposable tests.

No mounts, services, network, or physical-device access exists in this module.
Compatible with Python 3.5 and newer.
"""
import base64
import errno
import hashlib
import hmac
import json
import os
from pathlib import Path, PurePosixPath
import stat


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':')).encode('utf-8')


def safe(root, name):
    p = PurePosixPath(name)
    if not name or p.is_absolute() or '..' in p.parts or str(p) != name:
        raise ValueError('Unsafe relative path: ' + name)
    out = root.joinpath(*p.parts)
    for part in [out] + list(out.parents):
        if part.is_symlink():
            raise ValueError('Linked transaction path: ' + name)
        if part == root:
            break
    return out


def regular(path, limit=8 * 1024 * 1024):
    fd = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > limit:
            raise ValueError('Expected bounded, unlinked regular file: ' + str(path))
        with os.fdopen(fd, 'rb') as f:
            fd = None
            raw = f.read(limit + 1)
        if len(raw) > limit:
            raise ValueError('Read budget exceeded')
        return raw
    finally:
        if fd is not None:
            os.close(fd)


def file_hash(path):
    if not os.path.lexists(str(path)):
        return None
    return digest(regular(path))


def sync_dir(path):
    fd = os.open(str(path), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def metadata(path):
    st = path.stat()
    return dict(mode=stat.S_IMODE(st.st_mode), uid=st.st_uid, gid=st.st_gid,
                atime_ns=st.st_atime_ns, mtime_ns=st.st_mtime_ns,
                xattrs={n: base64.b64encode(os.getxattr(str(path), n)).decode('ascii')
                        for n in os.listxattr(str(path))})


def atomic(path, raw, meta=None, temporary=None):
    temp = temporary or path.with_name(path.name + '.new-' + os.urandom(8).hex())
    fd = os.open(str(temp), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(raw)
            f.flush()
            if meta:
                os.fchmod(f.fileno(), meta['mode'])
                os.fchown(f.fileno(), meta['uid'], meta['gid'])
                for name, value in meta['xattrs'].items():
                    os.setxattr(f.fileno(), name, base64.b64decode(value))
                os.utime(f.fileno(), ns=(meta['atime_ns'], meta['mtime_ns']))
            os.fsync(f.fileno())
        os.replace(str(temp), str(path))
        sync_dir(path.parent)
    finally:
        if os.path.lexists(str(temp)):
            temp.unlink()


ALLOWED_TARGETS = ('etc/systemd/system/hector-link-sync-control.service', 'etc/systemd/system/hector-link-sync-ethernet.service', 'etc/systemd/system/hector-link-sync-wifi.service', 'etc/systemd/system/hector-network-panel.service', 'etc/systemd/system/multi-user.target.d/90-network-link.conf', 'home/debian/UI/fourbyfour_display.py', 'home/debian/UI/ingen_wrapper.py', 'home/debian/UI/link-ports.json', 'home/debian/UI/mala-entry.json', 'home/debian/UI/mala-ports.json', 'home/debian/UI/mala.LICENSE', 'home/debian/UI/mala_407.py', 'home/debian/UI/mala_restore.py', 'home/debian/UI/mala_state.py', 'home/debian/UI/module_info.py', 'home/debian/UI/network-link-catalog.json', 'home/debian/UI/network_407.py', 'home/debian/UI/playhead_policy.py', 'home/debian/UI/poly303-entry.json', 'home/debian/UI/qml/ModuleBrowser.qml', 'home/debian/UI/qml/ModuleMore.qml', 'home/debian/UI/qml/MultiValueButtonsSlider.qml', 'home/debian/UI/qml/PatchBay.qml', 'home/debian/UI/qml/PatchBayEffect.qml', 'home/debian/UI/qml/Spotlight.qml', 'home/debian/UI/qml/TitleFooter.qml', 'home/debian/UI/qml/ValueButtonsSlider.qml', 'home/debian/UI/qml/link/FirmwarePanel.qml', 'home/debian/UI/qml/link/LinkButton.qml', 'home/debian/UI/qml/link/LinkChoice.qml', 'home/debian/UI/qml/link/LinkMeter.qml', 'home/debian/UI/qml/link/LinkSlider.qml', 'home/debian/UI/qml/link/LinkTempo.qml', 'home/debian/UI/qml/link/SyncEditor.qml', 'home/debian/UI/qml/link/catalog.js', 'home/debian/UI/qml/mala/BeadsBadge.qml', 'home/debian/UI/qml/mala/BeadsKnob.qml', 'home/debian/UI/qml/mala/BeadsSwitch.qml', 'home/debian/UI/qml/mala/Button.qml', 'home/debian/UI/qml/mala/ComboBox.qml', 'home/debian/UI/qml/mala/Editor.qml', 'home/debian/UI/qml/mala/EnvelopeGraphic.qml', 'home/debian/UI/qml/mala/FirmwarePanel.qml', 'home/debian/UI/qml/mala/ItemDelegate.qml', 'home/debian/UI/qml/mala/LibraryPanel.qml', 'home/debian/UI/qml/mala/ModeHelpDialog.qml', 'home/debian/UI/qml/mala/ParameterSlider.qml', 'home/debian/UI/qml/mala/Slider.qml', 'home/debian/UI/qml/mala/TouchButton.qml', 'home/debian/UI/qml/mala/assets/knob-body.png', 'home/debian/UI/qml/mala/assets/silver-button.png', 'home/debian/UI/qml/mala/assets/silver-panel.png', 'home/debian/UI/qml/mala/catalog.js', 'home/debian/UI/qml/network/FirmwarePanel.qml', 'home/debian/UI/qml/network/Keyboard.qml', 'home/debian/UI/qml/poly303/Bank.js', 'home/debian/UI/qml/poly303/BuildInfo.js', 'home/debian/UI/qml/poly303/Choice.qml', 'home/debian/UI/qml/poly303/ClockSource.js', 'home/debian/UI/qml/poly303/Editor.qml', 'home/debian/UI/qml/poly303/Fader.qml', 'home/debian/UI/qml/poly303/FirmwarePanel.qml', 'home/debian/UI/qml/poly303/Key.qml', 'home/debian/UI/qml/poly303/Knob.qml', 'home/debian/UI/qml/poly303/Names.js', 'home/debian/UI/qml/poly303/NumberBox.qml', 'home/debian/UI/qml/poly303/Pattern.js', 'home/debian/UI/qml/poly303/PatternMenu.qml', 'home/debian/UI/qml/poly303/Playhead.js', 'home/debian/UI/qml/poly303/TempoMenu.qml', 'home/debian/UI/qml/poly303/TempoReadout.js', 'home/debian/UI/qml/poly303/Theme.js', 'home/debian/UI/qml/poly303/ThemeSwitch.qml', 'home/debian/UI/qml/poly303/WaveSwitch.qml', 'home/debian/UI/qml/poly303/catalog.js', 'home/debian/UI/show_widget.py', 'home/debian/UI/squelch_bank.py', 'home/debian/UI/squelch_bank_codec.py', 'home/debian/UI/squelch_bank_fields.py', 'home/debian/UI/squelch_startup.py', 'home/debian/UI/sync_407.py', 'usr/lib/firmware/ath9k_htc/htc_9271-1.4.0.fw', 'usr/lib/firmware/mt7662.bin', 'usr/lib/firmware/mt7662_rom_patch.bin', 'usr/lib/lv2/hector-link-sync.lv2/hector_link_sync.so', 'usr/lib/lv2/hector-link-sync.lv2/manifest.ttl', 'usr/lib/lv2/hector-link-sync.lv2/sync.ttl', 'usr/lib/lv2/mala.lv2/LICENSE', 'usr/lib/lv2/mala.lv2/NOTICE', 'usr/lib/lv2/mala.lv2/UPSTREAM-LICENSES', 'usr/lib/lv2/mala.lv2/mala.so', 'usr/lib/lv2/mala.lv2/mala.ttl', 'usr/lib/lv2/mala.lv2/manifest.ttl', 'usr/lib/lv2/poly303.lv2/manifest.ttl', 'usr/lib/lv2/poly303.lv2/poly303.so', 'usr/lib/lv2/poly303.lv2/poly303.ttl', 'usr/local/lib/hector-link-sync/backend.py', 'usr/local/lib/hector-link-sync/client.py', 'usr/local/lib/hector-link-sync/control', 'usr/local/lib/hector-link-sync/helper', 'usr/local/lib/hector-network-panel/backend.py', 'usr/local/lib/hector-network-panel/client.py', 'usr/share/doc/network-link-hector/Atheros-firmware.txt', 'usr/share/doc/network-link-hector/MediaTek-firmware.txt')


def valid_hash(h):
    return h is None or isinstance(h,str) and len(h)==64 and all(c in '0123456789abcdef' for c in h)

def validate_manifest(m):
    if (m.get('schema')!='hector-community/transition/1' or m.get('hardware')!='Hector'
            or m.get('firmware')!='407' or m.get('architecture')!='aarch64'
            or m.get('component') not in ('mala','network-link','squelch-box')
            or m.get('action') not in ('install','rollback')):
        raise ValueError('Unsupported community transition contract')
    seen=set()
    for row in m['files']:
        name=row['path']
        if (name not in ALLOWED_TARGETS or name in seen or not valid_hash(row['sha256'])
                or not valid_hash(row['before_sha256']) or row['sha256']==row['before_sha256']
                or type(row['size']) is not int or row['size']<0 or row['size']>8388608
                or row.get('mode',0o644) not in (0o644,0o755)
                or (row['sha256'] is None and row['size']!=0)):
            raise ValueError('Unexpected or duplicate transition target')
        seen.add(name)
    if not seen or len(seen)!=m.get('file_count') or seen.intersection(m['guards']):
        raise ValueError('Incomplete or overlapping transition inventory')
    for name,h in m['guards'].items():
        p=PurePosixPath(name)
        if p.is_absolute() or '..' in p.parts or str(p)!=name or not valid_hash(h):raise ValueError('Invalid preservation guard')


class Transaction:
    def __init__(self, root, store, key):
        self.root, self.store, self.key = Path(root), Path(store), key
        self.record = None

    def save(self):
        content = self.record
        envelope = dict(content=content, hmac=hmac.new(self.key, canonical(content), hashlib.sha256).hexdigest())
        atomic(self.store / 'journal.json', canonical(envelope))

    def load(self):
        envelope = json.loads(regular(self.store / 'journal.json').decode())
        expected = hmac.new(self.key, canonical(envelope['content']), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, envelope['hmac']):
            raise ValueError('Backup journal authentication failed')
        self.record = envelope['content']
        return self.record

    def preflight(self, manifest, payload):
        validate_manifest(manifest)
        if set(payload) != {r['path'] for r in manifest['files'] if r['sha256'] is not None}:
            raise ValueError('Payload file set differs')
        for row in manifest['files']:
            name = row['path']
            if row['sha256'] is not None and (digest(payload[name]) != row['sha256'] or len(payload[name]) != row['size']):
                raise ValueError('Corrupt payload: ' + name)
            if file_hash(safe(self.root, name)) != row['before_sha256']:
                raise ValueError('Stock 407 mismatch or conflicting installation: ' + name)
        for name, value in manifest['guards'].items():
            if file_hash(safe(self.root, name)) != value:
                raise ValueError('Stock catalog guard differs: ' + name)
        for name in manifest['require_absent']:
            if os.path.lexists(str(safe(self.root, name))):
                raise ValueError('Existing community target: ' + name)

    def prepare(self, manifest, payload, identity, boot):
        self.preflight(manifest, payload)
        if (self.store / 'journal.json').exists():
            raise ValueError('Existing transaction must not be reused')
        rows = []
        ui_owner = metadata(safe(self.root, 'home/debian/UI/show_widget.py'))
        for row in manifest['files']:
            p = safe(self.root, row['path'])
            raw = regular(p) if row['before_sha256'] else None
            old_meta = metadata(p) if raw is not None else None
            new_meta = old_meta or dict(mode=row.get('mode', 0o644), uid=ui_owner['uid'] if row['path'].startswith('home/') else self.root.stat().st_uid,
                gid=ui_owner['gid'] if row['path'].startswith('home/') else self.root.stat().st_gid,
                atime_ns=0, mtime_ns=0, xattrs={})
            rows.append(dict(row, original=base64.b64encode(raw).decode('ascii') if raw is not None else None,
                             metadata=old_meta, installed_metadata=new_meta))
        self.record = dict(schema=1, version=manifest['version'], identity=identity, boot=boot,
            component=manifest['component'], action=manifest['action'], from_state=manifest['from_state'], to_state=manifest['to_state'], catalog_sha256=manifest['catalog_sha256'], phase='prepared', files=rows, guards=manifest['guards'], applied=[], pending=None,
            created_dirs=[], services={}, id=self.store.name, guard_metadata={n:metadata(safe(self.root,n)) for n,h in manifest['guards'].items() if h is not None})
        self.save()
        # Round-trip the complete durable original set before any target write.
        self.load()
        for row in rows:
            if row['original'] is not None and digest(base64.b64decode(row['original'])) != row['before_sha256']:
                raise ValueError('Original backup does not match')

    def verify_preimages(self):
        for row in self.record['files']:
            p=safe(self.root,row['path'])
            if file_hash(p)!=row['before_sha256']:raise ValueError('Preimage changed')
            if row['metadata'] is not None:
                now=metadata(p)
                if any(now[k]!=row['metadata'][k] for k in ['mode','uid','gid','mtime_ns','xattrs']):raise ValueError('Preimage metadata changed')
        self.verify_guards()

    def verify_guards(self):
        for name,h in self.record['guards'].items():
            p=safe(self.root,name)
            if file_hash(p)!=h:raise ValueError('Protected component changed: '+name)
            if name in self.record.get('guard_metadata',{}):
                now=metadata(p);expected=self.record['guard_metadata'][name]
                if any(now[k]!=expected[k] for k in ['mode','uid','gid','mtime_ns','xattrs']):raise ValueError('Protected component metadata changed')

    def ensure_parents(self, p):
        missing = []
        parent = p.parent
        while not parent.exists():
            missing.append(parent)
            parent = parent.parent
        for parent in reversed(missing):
            self.record['created_dirs'].append(str(parent.relative_to(self.root)))
            self.save()
            parent.mkdir(mode=0o755)
            sync_dir(parent.parent)

    def temp_path(self, p):
        return p.with_name('.' + p.name + '.community-' + self.record['id'] + '.tmp')

    def apply(self, payload, checkpoint=lambda stage, name: None):
        self.verify_preimages()
        self.record['phase'] = 'publishing'
        self.save()
        for row in self.record['files']:
            name = row['path']
            p = safe(self.root, name)
            if file_hash(p) != row['before_sha256'] or (row['sha256'] is not None and digest(payload[name]) != row['sha256']):
                raise ValueError('Target or payload changed before publication: ' + name)
            if row['sha256'] is not None:self.ensure_parents(p)
            self.record['pending'] = name
            self.save()
            checkpoint('before', name)
            if row['sha256'] is None:
                p.unlink();sync_dir(p.parent)
            else:atomic(p, payload[name], row['installed_metadata'], self.temp_path(p))
            checkpoint('after', name)
            self.record['applied'].append(name)
            self.record['pending'] = None
            self.save()
        self.verify_installed()
        self.record['phase'] = 'committed'
        self.save()

    def verify_installed(self):
        for row in self.record['files']:
            p = safe(self.root, row['path'])
            if file_hash(p) != row['sha256']:
                raise ValueError('Installed file differs: ' + row['path'])
            if row['sha256'] is None:continue
            meta = metadata(p)
            if any(meta[n] != row['installed_metadata'][n] for n in ['mode', 'uid', 'gid', 'mtime_ns', 'xattrs']):
                raise ValueError('Installed metadata differs: ' + row['path'])
        self.verify_guards()

    def verify_restored(self):
        for row in self.record['files']:
            p = safe(self.root, row['path'])
            if file_hash(p) != row['before_sha256']:
                raise ValueError('Restored file differs: ' + row['path'])
            if row['metadata'] is not None:
                observed = metadata(p)
                if any(observed[k] != row['metadata'][k] for k in ['mode', 'uid', 'gid', 'mtime_ns', 'xattrs']):
                    raise ValueError('Restored metadata differs: ' + row['path'])
        self.verify_guards()

    def admit_rollback(self):
        for row in self.record['files']:
            p = safe(self.root, row['path'])
            temp = self.temp_path(p)
            if os.path.lexists(str(temp)) and file_hash(temp) not in (row['before_sha256'], row['sha256']):
                raise ValueError('Unexpected incomplete staging file')
            if file_hash(p) not in (row['before_sha256'], row['sha256']):
                raise ValueError('Rollback refuses an edited or unexpected target: ' + row['path'])
            current = file_hash(p)
            expected_meta = row['installed_metadata'] if current == row['sha256'] else row['metadata']
            if current is not None and expected_meta is not None:
                observed = metadata(p)
                if any(observed[k] != expected_meta[k] for k in ['mode', 'uid', 'gid', 'mtime_ns', 'xattrs']):
                    raise ValueError('Rollback refuses changed target metadata: ' + row['path'])
            if row['original'] is not None and digest(base64.b64decode(row['original'])) != row['before_sha256']:
                raise ValueError('Backup original corrupt')
        self.verify_guards()

    def rollback(self, checkpoint=lambda stage, name: None):
        self.admit_rollback()
        self.record['phase'] = 'restoring'
        self.save()
        for row in reversed(self.record['files']):
            p = safe(self.root, row['path'])
            temp = self.temp_path(p)
            if os.path.lexists(str(temp)):
                temp.unlink()
                sync_dir(temp.parent)
            current = file_hash(p)
            if current == row['sha256']:
                checkpoint('before_restore', row['path'])
                if row['original'] is None:
                    if p.exists():p.unlink();sync_dir(p.parent)
                else:
                    atomic(p, base64.b64decode(row['original']), row['metadata'], self.temp_path(p))
                checkpoint('after_restore', row['path'])
        for name in reversed(self.record['created_dirs']):
            path = safe(self.root, name)
            try:
                path.rmdir()
                sync_dir(path.parent)
            except OSError as e:
                if e.errno not in (errno.ENOENT, errno.ENOTEMPTY):
                    raise
        self.verify_restored()
        self.record['pending'] = None
        self.record['phase'] = 'rolled-back'
        self.save()
        return 'rolled-back'
