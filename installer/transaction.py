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


def validate_manifest(m):
    if (m.get('schema') != 'mala-hector/public-beta/1' or m.get('hardware') != 'Hector'
            or m.get('firmware') != '407' or m.get('architecture') != 'aarch64'
            or m.get('sample_rate') != 48000 or m.get('ports') != 58
            or m.get('plugin_uri') != 'urn:beebo-hector-lab:mala-preview'):
        raise ValueError('Unsupported release contract')
    seen = set()
    for row in m['files']:
        name = row['path']
        if (name in seen or not name.startswith(('home/debian/UI/', 'usr/lib/lv2/mala.lv2/'))
                or '..' in PurePosixPath(name).parts or PurePosixPath(name).is_absolute()
                or len(row['sha256']) != 64):
            raise ValueError('Unexpected or duplicate payload path')
        seen.add(name)
    if len(seen) != 34:
        raise ValueError('Expected the complete 34-file Mala release')


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
        if set(payload) != {r['path'] for r in manifest['files']}:
            raise ValueError('Payload file set differs')
        for row in manifest['files']:
            name = row['path']
            if digest(payload[name]) != row['sha256'] or len(payload[name]) != row['size']:
                raise ValueError('Corrupt payload: ' + name)
            if file_hash(safe(self.root, name)) != row['before_sha256']:
                raise ValueError('Stock 407 mismatch or conflicting installation: ' + name)
        for name, value in manifest['guards'].items():
            if file_hash(safe(self.root, name)) != value:
                raise ValueError('Stock catalog guard differs: ' + name)
        for name in manifest['require_absent']:
            if os.path.lexists(str(safe(self.root, name))):
                raise ValueError('Existing Mala/community target: ' + name)

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
            new_meta = old_meta or dict(mode=0o644, uid=ui_owner['uid'] if row['path'].startswith('home/') else self.root.stat().st_uid,
                gid=ui_owner['gid'] if row['path'].startswith('home/') else self.root.stat().st_gid,
                atime_ns=0, mtime_ns=0, xattrs={})
            rows.append(dict(row, original=base64.b64encode(raw).decode('ascii') if raw is not None else None,
                             metadata=old_meta, installed_metadata=new_meta))
        self.record = dict(schema=1, version=manifest['version'], identity=identity, boot=boot,
            phase='prepared', files=rows, guards=manifest['guards'], applied=[], pending=None,
            created_dirs=[], services={}, id=self.store.name)
        self.save()
        # Round-trip the complete durable original set before any target write.
        self.load()
        for row in rows:
            if row['original'] is not None and digest(base64.b64decode(row['original'])) != row['before_sha256']:
                raise ValueError('Original backup does not match')

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
        return p.with_name('.' + p.name + '.mala-' + self.record['id'] + '.tmp')

    def apply(self, payload, checkpoint=lambda stage, name: None):
        self.record['phase'] = 'publishing'
        self.save()
        for row in self.record['files']:
            name = row['path']
            p = safe(self.root, name)
            if file_hash(p) != row['before_sha256'] or digest(payload[name]) != row['sha256']:
                raise ValueError('Target or payload changed before publication: ' + name)
            self.ensure_parents(p)
            self.record['pending'] = name
            self.save()
            checkpoint('before', name)
            atomic(p, payload[name], row['installed_metadata'], self.temp_path(p))
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
            meta = metadata(p)
            if any(meta[n] != row['installed_metadata'][n] for n in ['mode', 'uid', 'gid', 'mtime_ns', 'xattrs']):
                raise ValueError('Installed metadata differs: ' + row['path'])
        for name, value in self.record['guards'].items():
            if file_hash(safe(self.root, name)) != value:
                raise ValueError('Preserved catalog differs')

    def verify_restored(self):
        for row in self.record['files']:
            p = safe(self.root, row['path'])
            if file_hash(p) != row['before_sha256']:
                raise ValueError('Restored file differs: ' + row['path'])
            if row['metadata'] is not None:
                observed = metadata(p)
                if any(observed[k] != row['metadata'][k] for k in ['mode', 'uid', 'gid', 'mtime_ns', 'xattrs']):
                    raise ValueError('Restored metadata differs: ' + row['path'])
        for name, value in self.record['guards'].items():
            if file_hash(safe(self.root, name)) != value:
                raise ValueError('Restored catalog guard differs')

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
        for name, value in self.record['guards'].items():
            if file_hash(safe(self.root, name)) != value:
                raise ValueError('Rollback catalog guard differs')

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
                    p.unlink()
                    sync_dir(p.parent)
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
