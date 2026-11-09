#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""USB entry and detached worker for Hector firmware 407. No network required."""
import argparse
import base64
import errno
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import stat
import subprocess
import sys
import time
import uuid

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent / 'installer'))
from transaction import Transaction, atomic, canonical, digest, file_hash, regular, safe, sync_dir

DATA = Path('/mnt/mala-public-beta')
LOWER = Path('/overlay/lower')
USB = Path('/usb_flash')
SERVICES = ('lightdm.service', 'jack.service', 'pcm_power.service')


def command(argv, timeout=45):
    p = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True,
                       timeout=timeout, env=dict(PATH='/usr/sbin:/usr/bin:/sbin:/bin', LC_ALL='C'))
    if p.returncode:
        raise RuntimeError('Command failed: ' + ' '.join(argv[:3]) + ': ' + p.stderr[-1200:])
    return p.stdout


def hardware():
    # Refuse a desktop before reading any device-specific path or creating files.
    if os.geteuid() != 0 or platform.machine() not in ('aarch64', 'arm64'):
        raise ValueError('This USB kit only runs on an ARM64 Hector, as root')
    if b'pine64,sopine' not in Path('/proc/device-tree/compatible').read_bytes():
        raise ValueError('Unsupported board')
    if json.loads(Path('/mnt/pedal_state/state.json').read_text()).get('model') != 'hector':
        raise ValueError('Hector required; Beebo is unsupported')
    return digest(Path('/sys/block/mmcblk0/device/cid').read_bytes() +
                  Path('/pedal_state/hardware_info.json').read_bytes())


def enter_main_namespace():
    if os.stat('/proc/self/ns/mnt').st_ino != os.stat('/proc/1/ns/mnt').st_ino:
        os.execv('/usr/bin/nsenter', ['/usr/bin/nsenter', '--mount=/proc/1/ns/mnt',
                 '/usr/bin/python3', '-I', '-B', str(Path(__file__).resolve())] + sys.argv[1:])


def mounts():
    rows = {}
    unescape = lambda s: re.sub(r'\\([0-7]{3})', lambda m: chr(int(m.group(1), 8)), s)
    for line in Path('/proc/self/mountinfo').read_text().splitlines():
        left, right = line.split(' - ', 1)
        a, b = left.split(), right.split()
        rows.setdefault(unescape(a[4]), []).append(dict(id=a[0], device=a[2], root=unescape(a[3]),
            options=a[5].split(','), fs=b[0], source=unescape(b[1]), super_options=b[2].split(',')))
    result = {}
    for name in ['/', '/overlay', '/overlay/lower', '/mnt', '/usb_flash']:
        fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            fields = dict(l.split(':', 1) for l in Path('/proc/self/fdinfo/' + str(fd)).read_text().splitlines())
            selected = [r for r in rows.get(name, []) if r['id'] == fields['mnt_id'].strip()]
        finally:
            os.close(fd)
        if len(selected) != 1:
            raise ValueError('Unexpected mount view: ' + name)
        result[name] = selected[0]
    return result


def protected(path, directory=False):
    for p in [path] + list(path.parents):
        if p == Path('/mnt'):
            break
        st = p.lstat()
        if p.is_symlink() or st.st_uid != 0 or st.st_mode & 0o022:
            raise ValueError('Unprotected private transaction path')
    if directory and not path.is_dir():
        raise ValueError('Transaction directory missing')


class Device:
    def __init__(self):
        self.identity = hardware()
        self.boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        self.initial = None
        self.usb_device = USB.stat().st_dev
        self.pause_files = []
        self.readonly_pending_reboot = False
        self.check_mounts('ro')

    def check_mounts(self, mode):
        current = mounts()
        for path, fs, source in [('/overlay/lower', 'btrfs', '/dev/mmcblk0p2'),
                                 ('/mnt', 'btrfs', '/dev/mmcblk0p3')]:
            row = current[path]
            if row['fs'] != fs or row['source'] != source or row['root'] != '/':
                raise ValueError('Unsupported persistent mount: ' + path)
        if (mode not in current['/overlay/lower']['options'] or 'rw' not in current['/mnt']['options']
                or current['/']['fs'] != 'overlay' or current['/overlay']['fs'] != 'tmpfs'
                or not {'lowerdir=/overlay/lower', 'upperdir=/overlay/upper', 'workdir=/overlay/work'}.issubset(set(current['/']['super_options']))):
            raise ValueError('Unexpected overlay or mount mode')
        usb = current['/usb_flash']
        if usb['fs'] != 'vfat' or 'rw' not in usb['options'] or not re.match(r'^/dev/sd[a-z][1-9][0-9]*$', usb['source']):
            raise ValueError('Use a writable, single-partition FAT32 USB thumb drive')
        identity = {p: {k: r[k] for k in ['id', 'device', 'root', 'fs', 'source']} for p, r in current.items()}
        if self.initial is None:
            self.initial = identity
        elif self.initial != identity:
            raise ValueError('Mount identity changed')

    def report(self, status, detail):
        if USB.stat().st_dev != self.usb_device:
            raise ValueError('USB removed or changed')
        raw = ('Mala public beta\nStatus: ' + status + '\n' + detail + '\n').encode('utf-8')
        atomic(USB / 'MALA-RESULT.txt', raw)
        command(['/usr/bin/sync', '-f', str(USB / 'MALA-RESULT.txt')])

    def retire_inactive_reservation(self, action):
        marker = DATA / 'active.json'
        if not marker.exists():
            return
        protected(marker)
        token = json.loads(regular(marker).decode())['operation']
        if not re.match(r'^[a-f0-9]{32}$', token):
            raise ValueError('Invalid reserved operation')
        state = command(['/bin/systemctl', 'show', 'mala-public-' + token, '--property=ActiveState'])
        if 'ActiveState=inactive\n' not in state and 'ActiveState=failed\n' not in state:
            raise ValueError('A Mala operation is still running; leave power and USB connected')
        if action != 'rollback':
            raise ValueError('An interrupted operation is reserved. Use the rollback USB kit.')
        marker.rename(DATA / ('interrupted-' + token + '.json'))
        sync_dir(DATA)

    def latest(self):
        if not DATA.exists():
            return None
        protected(DATA, True)
        if not (DATA / 'latest.json').exists():
            return None
        protected(DATA / 'latest.json')
        keyfile = DATA / 'key'
        protected(keyfile)
        if keyfile.stat().st_mode & 0o077:
            raise ValueError('Transaction key permissions differ')
        key = regular(keyfile)
        record = json.loads(regular(DATA / 'latest.json').decode())
        name = record['id']
        if not re.match(r'^[a-f0-9]{32}$', name):
            raise ValueError('Invalid transaction ID')
        store = DATA / 'transactions' / name
        protected(store / 'journal.json')
        tx = Transaction(LOWER, store, key)
        tx.load()
        if tx.record['identity'] != self.identity:
            raise ValueError('Backup belongs to a different Hector')
        return tx

    def init_data(self):
        if not DATA.exists():
            DATA.mkdir(mode=0o700)
            sync_dir(DATA.parent)
        protected(DATA, True)
        if not (DATA / 'key').exists():
            fd = os.open(str(DATA / 'key'), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, 'wb') as f:
                f.write(os.urandom(32)); f.flush(); os.fsync(f.fileno())
            sync_dir(DATA)
        for leaf in ['transactions', 'operations']:
            p = DATA / leaf
            if not p.exists():
                p.mkdir(mode=0o700); sync_dir(DATA)
            protected(p, True)

    def lock(self):
        fd = os.open(str(DATA / 'lock'), os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        if os.fstat(fd).st_uid != 0:
            os.close(fd); raise ValueError('Installer lock owner differs')
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return fd

    def baseline(self, manifest, payload):
        Transaction(LOWER, Path('/unused'), b'').preflight(manifest, payload)
        names = {r['path'] for r in manifest['files']} | set(manifest['guards'])
        for name in names:
            if os.path.lexists(str(safe(Path('/overlay/upper'), name))):
                raise ValueError('Writable overlay shadows a target: ' + name)
            for parent in safe(Path('/overlay/upper'), name).parents:
                if parent == Path('/overlay'):
                    break
                if parent.exists() and set(os.listxattr(str(parent))).intersection(['trusted.overlay.opaque','user.overlay.opaque','trusted.overlay.redirect','user.overlay.redirect']):
                    raise ValueError('Opaque or redirected writable overlay requires review')
            if file_hash(safe(Path('/'), name)) != file_hash(safe(LOWER, name)):
                raise ValueError('Visible and persistent firmware differ: ' + name)
        for p in Path('/var/lib/dpkg/info').glob('*.list'):
            owned = set(p.read_text().splitlines())
            if owned.intersection('/' + r['path'] for r in manifest['files']):
                raise ValueError('An installed package owns Mala/UI targets: ' + p.name)
        for p in [LOWER, Path('/mnt')]:
            if shutil.disk_usage(str(p)).free < 32 * 1024 * 1024:
                raise ValueError('Need at least 32 MiB free on firmware and data storage')

    def pause(self):
        raw = b'[Unit]\nConditionPathExists=/run/mala-public-enable-consumers\n'
        if Path('/run/mala-public-enable-consumers').exists():
            raise ValueError('Unexpected consumer enable marker')
        for unit in SERVICES:
            parent = Path('/run/systemd/system') / (unit + '.d')
            if parent.is_symlink():
                raise ValueError('Linked runtime service directory')
            parent.mkdir(mode=0o755, exist_ok=True)
            target = parent / '90-mala-public-pause.conf'
            fd = os.open(str(target), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644)
            with os.fdopen(fd, 'wb') as f:
                f.write(raw); f.flush(); os.fsync(f.fileno())
            self.pause_files.append(target)
        command(['/bin/systemctl', 'daemon-reload'])
        for unit in SERVICES:
            shown = command(['/bin/systemctl', 'show', unit, '--property=DropInPaths'])
            if str(Path('/run/systemd/system') / (unit + '.d') / '90-mala-public-pause.conf') not in shown:
                raise ValueError('Runtime service pause not loaded')
        command(['/bin/systemctl', 'stop'] + list(SERVICES), 60)
        self.quiescent()

    def quiescent(self):
        for unit in SERVICES:
            fields = dict(l.split('=', 1) for l in command(['/bin/systemctl', 'show', unit,
                '--property=ActiveState,MainPID']).splitlines() if '=' in l)
            if fields.get('ActiveState') not in ['inactive', 'failed'] or fields.get('MainPID') != '0':
                raise ValueError('Screen/audio consumer still active')
        for p in Path('/proc').glob('[0-9]*/cmdline'):
            try:
                raw = p.read_bytes()
            except OSError:
                continue
            if b'/home/debian/UI/show_widget.py\0' in raw or raw.startswith(b'/usr/bin/ingen\0'):
                raise ValueError('UI/audio engine process still present')

    def resume_before_write(self, services):
        for p in self.pause_files:
            if regular(p) != b'[Unit]\nConditionPathExists=/run/mala-public-enable-consumers\n':
                raise ValueError('Runtime service pause changed')
            p.unlink()
        command(['/bin/systemctl', 'daemon-reload'])
        for unit, active in services.items():
            if active:
                command(['/bin/systemctl', 'start', unit], 60)

    def writable(self):
        self.check_mounts('ro'); self.quiescent()
        command(['/usr/bin/mount', '-o', 'remount,rw', str(LOWER)])
        self.check_mounts('rw')

    def readonly(self):
        command(['/usr/bin/sync', '-f', str(LOWER)])
        try:
            command(['/usr/bin/mount', '-o', 'remount,ro', str(LOWER)])
        except RuntimeError as e:
            # Stock overlay407 can retain busy references after durable sync.
            # Leave consumers paused and complete closeout by ordinary reboot.
            if 'busy' not in str(e).lower():
                raise
            self.readonly_pending_reboot = True
            return
        self.check_mounts('ro')

    def reboot(self):
        os.sync()
        command(['/bin/systemctl', 'reboot'])


def load_package(folder, need_payload=True):
    manifest = json.loads(regular(folder / 'manifest.json').decode())
    payload = {}
    if need_payload:
        for row in manifest['files']:
            raw = regular(safe(folder / 'payload', row['path']))
            if digest(raw) != row['sha256'] or len(raw) != row['size']:
                raise ValueError('USB package incomplete or corrupt: ' + row['path'])
            payload[row['path']] = raw
    return manifest, payload


def capture(folder, target, need_payload):
    target.mkdir(mode=0o700)
    names = ['install.py', 'installer/transaction.py', 'manifest.json']
    if need_payload:
        manifest, _ = load_package(folder)
        names += ['payload/' + r['path'] for r in manifest['files']]
    for name in names:
        raw = regular(safe(folder, name))
        p = safe(target, name)
        p.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = os.open(str(p), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'wb') as f:
            f.write(raw); f.flush(); os.fsync(f.fileno())
        sync_dir(p.parent)
    sync_dir(target.parent)


def launch(device, folder, action):
    manifest, payload = load_package(folder, action == 'install')
    device.retire_inactive_reservation(action)
    latest = device.latest()
    if latest:
        if latest.record['version'] != manifest['version']:
            raise ValueError('A different public beta needs its own migration/rollback kit')
        if latest.record['phase'] == 'committed' and action == 'install':
            latest.verify_installed()
            for row in latest.record['files']:
                if file_hash(safe(Path('/'), row['path'])) != row['sha256']:
                    raise ValueError('Post-reboot visible firmware verification failed')
            device.report('INSTALLED AND VERIFIED', 'Mala ' + manifest['version'] + ' is installed. Remove the USB drive. No repeat installation or reboot was performed.')
            return
        if latest.record['phase'] == 'rolled-back' and action == 'rollback':
            latest.verify_restored()
            for row in latest.record['files']:
                if file_hash(safe(Path('/'), row['path'])) != row['before_sha256']:
                    raise ValueError('Post-reboot visible restoration verification failed')
            device.report('ROLLBACK VERIFIED', 'The pre-Mala files are restored. Remove the USB drive. No repeat rollback or reboot was performed.')
            return
        if action == 'install' and latest.record['phase'] != 'rolled-back':
            raise ValueError('An incomplete operation exists. Use the rollback USB kit; do not retry installation.')
    if action == 'rollback':
        if latest is None:
            raise ValueError('No public-beta backup exists on this Hector')
        latest.admit_rollback()
    else:
        device.baseline(manifest, payload)
    device.init_data()
    lock = device.lock()
    try:
        # Another USB/debug invocation must not reserve a competing worker.
        active = DATA / 'active.json'
        if active.exists():
            raise ValueError('An operation is already reserved. Inspect MALA-RESULT.txt; do not launch another worker.')
        token = uuid.uuid4().hex
        store = DATA / 'operations' / token
        store.mkdir(mode=0o700)
        capture(folder, store / 'package', action == 'install')
        config = dict(id=token, action=action, identity=device.identity, boot=device.boot,
                      usb_device=device.usb_device, transaction=latest.record['id'] if action == 'rollback' else token)
        atomic(store / 'operation.json', canonical(config))
        atomic(active, canonical(dict(operation=token)))
        device.report('STARTING', 'Mala ' + action + ' is starting. Keep the USB connected and do not switch power off. Hector will reboot normally after a verified result.')
        try:
            command(['/usr/bin/systemd-run', '--quiet', '--no-block', '--unit=mala-public-' + token,
                '--property=Type=oneshot', '--property=TimeoutStartSec=240', '--property=TimeoutStopSec=60',
                '--property=Restart=no', '--property=LimitCORE=0', '/usr/bin/python3', '-I', '-B',
                str(store / 'package/install.py'), '--worker', str(store / 'operation.json')])
        except Exception:
            active.unlink(); sync_dir(DATA)
            raise
    finally:
        os.close(lock)


def worker(config_path):
    protected(config_path)
    config = json.loads(regular(config_path).decode())
    device = Device()
    if (device.identity, device.boot, device.usb_device) != (config['identity'], config['boot'], config['usb_device']):
        raise ValueError('Device, USB, or boot changed after admission')
    lock = device.lock()
    tx = None
    write_attempted = False
    services = {}
    try:
        manifest, payload = load_package(config_path.parent / 'package', config['action'] == 'install')
        if config['action'] == 'install':
            device.baseline(manifest, payload)
            store = DATA / 'transactions' / config['transaction']
            store.mkdir(mode=0o700)
            tx = Transaction(LOWER, store, regular(DATA / 'key'))
            tx.prepare(manifest, payload, device.identity, device.boot)
            atomic(DATA / 'latest.json', canonical(dict(id=store.name)))
        else:
            tx = device.latest()
            if tx.record['id'] != config['transaction']:
                raise ValueError('Latest backup changed')
            tx.admit_rollback()
        for unit in SERVICES:
            value = command(['/bin/systemctl', 'show', unit, '--property=ActiveState'])
            services[unit] = 'ActiveState=active\n' in value or 'ActiveState=activating\n' in value
        tx.record['services'] = services; tx.save()
        device.pause()
        write_attempted = True
        device.writable()
        if config['action'] == 'install':
            tx.apply(payload)
        else:
            tx.rollback()
        device.readonly()
        tx.record['normal_reboot_requested'] = True
        tx.record['readonly_closeout_pending_reboot'] = device.readonly_pending_reboot
        tx.save()
        device.report('INSTALLED; REBOOTING' if config['action'] == 'install' else 'RESTORED; REBOOTING',
            'Files verified. Hector is rebooting normally. Keep the USB connected through this reboot for the final verification report.')
        (DATA / 'active.json').unlink(); sync_dir(DATA)
        device.reboot()
    except Exception as error:
        final = 'REFUSED; NO FIRMWARE WRITES'
        detail = str(error)
        if write_attempted and tx is not None:
            try:
                # Do not resume consumers while persistent files may be mixed.
                if os.statvfs(str(LOWER)).f_flag & os.ST_RDONLY:
                    device.writable()
                tx.rollback()
                device.readonly()
                final = 'RESTORED AFTER ERROR; REBOOTING'
                detail += '\nThe saved pre-Mala files were restored and verified. Normal reboot follows.'
            except Exception as restore_error:
                final = 'RECOVERY REQUIRED'
                detail += '\nRestoration/closeout error: ' + str(restore_error) + '\nKeep this report and backups. Do not reinstall or repeatedly cycle power. Follow the recovery instructions.'
        elif device.pause_files:
            device.resume_before_write(services)
        device.report(final, detail)
        if final != 'RECOVERY REQUIRED' and (DATA / 'active.json').exists():
            (DATA / 'active.json').unlink(); sync_dir(DATA)
        if final == 'RESTORED AFTER ERROR; REBOOTING':
            device.reboot()
        raise
    finally:
        os.close(lock)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--usb', choices=['install', 'rollback'])
    parser.add_argument('--worker', type=Path)
    args = parser.parse_args()
    if os.geteuid() != 0 or platform.machine() not in ('aarch64', 'arm64'):
        raise ValueError('This USB kit only runs on an ARM64 Hector, as root')
    enter_main_namespace()
    if args.worker:
        worker(args.worker)
        return
    if not args.usb:
        parser.error('This is a USB kit. Follow docs/USB-INSTALL.md.')
    device = None
    try:
        # A USB mount can arrive before the main data/model mounts finish booting.
        deadline = time.monotonic() + 45
        while True:
            try:
                device = Device()
                break
            except (OSError, ValueError):
                if time.monotonic() >= deadline:
                    raise
                time.sleep(1)
        launch(device, Path(__file__).resolve().parent, args.usb)
    except Exception as error:
        if device is not None:
            device.report('REFUSED; NO NEW OPERATION STARTED', str(error))
        raise


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('Mala USB operation stopped: ' + str(error), file=sys.stderr)
        sys.exit(1)
