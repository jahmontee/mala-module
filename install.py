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
import catalog as policy

DATA = Path('/mnt/hector-community-beta')
KIT_COMPONENT = 'squelch-box'
OWNED_SERVICES = ('hector-link-sync-control.service','hector-link-sync-ethernet.service','hector-link-sync-wifi.service','hector-network-panel.service')
LOWER = Path('/overlay/lower')
USB = Path('/usb_flash')
SERVICES = ('lightdm.service', 'jack.service', 'pcm_power.service')


def command(argv, timeout=45):
    p = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True,
                       timeout=timeout, env=dict(PATH='/usr/sbin:/usr/bin:/sbin:/bin', LC_ALL='C'))
    if p.returncode:
        raise RuntimeError('Command failed: ' + ' '.join(argv[:3]) + ': ' + p.stderr[-1200:])
    return p.stdout


def wifi_module_contract(modinfo, modprobe, kernel, run):
    contracts = [
        ('ath9k_htc', 'usb:v0CF3p9271',
         {'ath9k_htc/htc_9271-1.4.0.fw', 'ath9k_htc/htc_7010-1.4.0.fw'}),
        ('mt76x2u', 'usb:v0E8Dp7612', {'mt7662.bin', 'mt7662_rom_patch.bin'})]
    for module, usb_alias, expected_firmware in contracts:
        aliases = run([modinfo, '-k', kernel, '-F', 'alias', module])
        if usb_alias not in aliases:
            raise ValueError('Missing stock adapter module contract: ' + module)
        run([modprobe, '--dry-run', '--show-depends', module])
        firmware = set(run([modinfo, '-k', kernel, '-F', 'firmware', module]).splitlines())
        if firmware != expected_firmware:
            raise ValueError('Unqualified stock firmware contract: ' + module)


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
        self.services = SERVICES
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
        raw = ('Hector community beta\nStatus: ' + status + '\n' + detail + '\n').encode('utf-8')
        atomic(USB / (KIT_COMPONENT.upper().replace('-','_')+'-RESULT.txt'), raw)
        command(['/usr/bin/sync', '-f', str(USB / (KIT_COMPONENT.upper().replace('-','_')+'-RESULT.txt'))])

    def retire_inactive_reservation(self, action):
        marker = DATA / 'active.json'
        if not marker.exists():
            return
        protected(marker)
        reservation=json.loads(regular(marker).decode())
        token = reservation['operation']
        if reservation.get('component') != KIT_COMPONENT:raise ValueError('A different component has an interrupted operation; use its matching rollback kit')
        if not re.match(r'^[a-f0-9]{32}$', token):
            raise ValueError('Invalid reserved operation')
        state = command(['/bin/systemctl', 'show', 'hector-community-beta-' + token, '--property=ActiveState'])
        if 'ActiveState=inactive\n' not in state and 'ActiveState=failed\n' not in state:
            raise ValueError('A community operation is still running; leave power and USB connected')
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

    def network_ready(self):
        required = ['/usr/bin/nmcli', '/usr/sbin/NetworkManager']
        if any(not Path(p).is_file() for p in required):
            raise ValueError('Stock NetworkManager tools are required')
        if 'ActiveState=active\n' not in command(['/bin/systemctl', 'show', 'NetworkManager.service', '--property=ActiveState']):
            raise ValueError('Stock NetworkManager must already be active; its enable state is not changed')
        modinfo = shutil.which('modinfo', path='/usr/sbin:/usr/bin:/sbin:/bin')
        modprobe = shutil.which('modprobe', path='/usr/sbin:/usr/bin:/sbin:/bin')
        if not modinfo or not modprobe:
            raise ValueError('Stock module inspection tools are required')
        profiles = command(['/usr/bin/nmcli', '-g', 'UUID', 'connection', 'show'])
        if '57c2d8ed-f187-5e3e-9075-4247581b62aa' in profiles.splitlines():
            raise ValueError('A conflicting runtime Wi-Fi profile already exists')
        wifi_module_contract(modinfo, modprobe, platform.release(), command)

    def baseline(self, manifest, payload):
        if manifest['component']=='network-link' and manifest['action']=='install':self.network_ready()
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
                raise ValueError('An installed package owns community/UI targets: ' + p.name)
        for p in [LOWER, Path('/mnt')]:
            if shutil.disk_usage(str(p)).free < 64 * 1024 * 1024:
                raise ValueError('Need at least 64 MiB free on firmware and data storage')

    def select_services(self, component):
        self.services=SERVICES
        if component=='network-link':
            extra=[]
            for unit in OWNED_SERVICES:
                if 'LoadState=loaded\n' in command(['/bin/systemctl','show',unit,'--property=LoadState']):extra.append(unit)
            self.services=SERVICES+tuple(extra)

    def stop_timeout(self):
        # Network workers can need125s to join; their unit allows150s.
        return 300 if any(u in OWNED_SERVICES for u in self.services) else 60

    def pause(self):
        raw = b'[Unit]\nConditionPathExists=/run/hector-community-beta-enable-consumers\n'
        if Path('/run/hector-community-beta-enable-consumers').exists():
            raise ValueError('Unexpected consumer enable marker')
        for unit in self.services:
            parent = Path('/run/systemd/system') / (unit + '.d')
            if parent.is_symlink():
                raise ValueError('Linked runtime service directory')
            parent.mkdir(mode=0o755, exist_ok=True)
            target = parent / '90-hector-community-beta-pause.conf'
            fd = os.open(str(target), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644)
            with os.fdopen(fd, 'wb') as f:
                f.write(raw); f.flush(); os.fsync(f.fileno())
            self.pause_files.append(target)
        command(['/bin/systemctl', 'daemon-reload'])
        for unit in self.services:
            shown = command(['/bin/systemctl', 'show', unit, '--property=DropInPaths'])
            if str(Path('/run/systemd/system') / (unit + '.d') / '90-hector-community-beta-pause.conf') not in shown:
                raise ValueError('Runtime service pause not loaded')
        command(['/bin/systemctl', 'stop'] + list(self.services), self.stop_timeout())
        self.quiescent()

    def quiescent(self):
        for unit in self.services:
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
            if regular(p) != b'[Unit]\nConditionPathExists=/run/hector-community-beta-enable-consumers\n':
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


def kit(folder):
    info=json.loads(regular(folder/'kit.json').decode());catalog=policy.load(folder/'catalog.json')
    if info.get('component') not in policy.COMPONENTS or info.get('catalog_sha256')!=digest(canonical(catalog)):
        raise ValueError('Kit identity or compatibility catalog changed')
    if info.get('version')!=catalog['components'][info['component']]['version']:raise ValueError('Kit component version differs')
    return info,catalog

def inventory(device,catalog,current,transaction):
    record=dict(schema=1,identity=device.identity,catalog_sha256=digest(canonical(catalog)),state=current,
        components=policy.component_versions(catalog,current),transaction=transaction)
    key=regular(DATA/'key');envelope=dict(content=record,hmac=__import__('hmac').new(key,canonical(record),hashlib.sha256).hexdigest())
    atomic(DATA/'components.json',canonical(envelope))

def check_inventory(device,catalog):
    f=DATA/'components.json'
    if not f.exists():return
    protected(f);envelope=json.loads(regular(f).decode());record=envelope['content'];key=regular(DATA/'key')
    expected=__import__('hmac').new(key,canonical(record),hashlib.sha256).hexdigest()
    if not __import__('hmac').compare_digest(expected,envelope['hmac']) or record['identity']!=device.identity:
        raise ValueError('Component inventory authentication/device binding failed')
    mapped=policy.translate_state(catalog,record['catalog_sha256'],record['state'])
    if record['catalog_sha256']!=digest(canonical(catalog)):
        accepted=policy.migration(catalog,record['catalog_sha256'])
        expected={key:accepted['components'][key] for key in catalog['states'][mapped]['components']}
        if record['components']!=expected or policy.detect(LOWER,catalog)!=mapped:
            raise ValueError('Legacy inventory does not match the exact recognized installation')
        latest=device.latest()
        if latest is None or latest.record['id']!=record['transaction']:
            raise ValueError('Legacy inventory has no matching authenticated transaction')
        if latest.record['phase']=='committed':latest.verify_installed()
        elif latest.record['phase']=='rolled-back':latest.verify_restored()
        else:raise ValueError('Finish recovery with the original matching kit before upgrading')

def outcome_file(component):
    if component not in policy.COMPONENTS:raise ValueError('Unknown outcome component')
    return DATA/'outcomes'/(component+'.json')

def write_outcome(device,catalog,config,state,outcome):
    parent=DATA/'outcomes'
    if not parent.exists():parent.mkdir(mode=0o700);sync_dir(DATA)
    protected(parent,True)
    action='rollback' if config['action']=='recover' else config['action']
    record=dict(schema=1,identity=device.identity,catalog_sha256=digest(canonical(catalog)),component=config['component'],
        action=action,transaction=config['transaction'],state=state,outcome=outcome,old_boot=device.boot)
    key=regular(DATA/'key');envelope=dict(content=record,hmac=__import__('hmac').new(key,canonical(record),hashlib.sha256).hexdigest())
    atomic(outcome_file(config['component']),canonical(envelope))

def read_outcome(device,catalog,component):
    path=outcome_file(component)
    if not path.exists():return None
    protected(path);envelope=json.loads(regular(path).decode());record=envelope['content'];key=regular(DATA/'key')
    expected=__import__('hmac').new(key,canonical(record),hashlib.sha256).hexdigest()
    if not __import__('hmac').compare_digest(expected,envelope['hmac']) or record['identity']!=device.identity or record['component']!=component:
        raise ValueError('Postboot outcome authentication/device binding failed')
    # Authenticate before interpreting an explicitly admitted older catalog.
    policy.translate_state(catalog,record['catalog_sha256'],record['state'])
    return record

def saved_tree(root):
    result={}
    for p in Path(root).rglob('*'):
        if not p.is_file() or p.is_symlink():continue
        fd=os.open(str(p),os.O_RDONLY|os.O_NOFOLLOW)
        try:
            before=os.fstat(fd)
            if not stat.S_ISREG(before.st_mode):raise ValueError('Saved asset is not a regular file')
            h=hashlib.sha256()
            while True:
                part=os.read(fd,1024*1024)
                if not part:break
                h.update(part)
            after=os.fstat(fd)
            if (before.st_ino,before.st_size,before.st_mtime_ns)!=(after.st_ino,after.st_size,after.st_mtime_ns):
                raise ValueError('Saved asset changed while hashing; no overwrite attempted')
            result[str(p.relative_to(root))]=h.hexdigest()
        finally:os.close(fd)
    return result

def saved_fingerprints():
    # Streaming hashes remain private on Hector. Large saved buffers are valid;
    # the8MiB package-file reader limit does not apply to user-owned assets.
    roots=['/mnt/presets/beebo','/mnt/pedal_state','/mnt/community-lab/cardinal/user','/mnt/community-lab/cardinal/config','/etc/NetworkManager/system-connections']
    return {root:saved_tree(root) for root in roots}

def verify_existing_metadata(device,catalog,state):
    # Known added files have fixed modes/owners even before this manager adopts
    # an earlier public install. Host-file metadata comes from durable journals.
    shared={'home/debian/UI/'+n for n in ('show_widget.py','module_info.py','ingen_wrapper.py','qml/PatchBayEffect.qml','qml/TitleFooter.qml','qml/ModuleBrowser.qml','qml/PatchBay.qml','qml/ValueButtonsSlider.qml','qml/MultiValueButtonsSlider.qml','qml/ModuleMore.qml','qml/Spotlight.qml','qml/link/catalog.js','qml/poly303/catalog.js')}
    ui=(LOWER/'home/debian/UI/show_widget.py').stat();root=LOWER.stat()
    for name,h in catalog['states'][state]['files'].items():
        if h is None or name in shared:continue
        observed=metadata_local(safe(LOWER,name));mode=catalog['artifacts'][h]['mode']
        uid,gid=(ui.st_uid,ui.st_gid) if name.startswith('home/') else (root.st_uid,root.st_gid)
        if (observed['mode'],observed['uid'],observed['gid'])!=(mode,uid,gid):raise ValueError('Installed component mode/owner differs: '+name)
    latest=device.latest()
    if latest and latest.record.get('to_state')==state and latest.record['phase']=='committed':
        latest.verify_installed();return
    if latest and latest.record.get('from_state')==state and latest.record['phase']=='rolled-back':
        latest.verify_restored();return
    # Earlier Mala and Network kits have their own authenticated private backup
    # journals. Read them in place, without moving, exporting or rewriting them.
    for folder in ['/mnt/mala-public-beta','/mnt/network-link-public-beta']:
        base=Path(folder)
        if not (base/'latest.json').exists():continue
        protected(base/'latest.json');protected(base/'key')
        if (base/'key').stat().st_mode&0o077:raise ValueError('Legacy backup key permissions differ')
        marker=json.loads(regular(base/'latest.json').decode());token=marker['id']
        if not re.match(r'^[a-f0-9]{32}$',token):raise ValueError('Legacy transaction identifier differs')
        tx=Transaction(LOWER,base/'transactions'/token,regular(base/'key'));tx.load()
        if tx.record['identity']!=device.identity:raise ValueError('Legacy backup belongs to a different Hector')
        if tx.record['phase']!='committed':raise ValueError('Finish legacy installer recovery first')
        for row in tx.record['files']:
            path=safe(LOWER,row['path'])
            if file_hash(path)!=row['sha256']:continue  # A recognized companion can update shared UI source.
            now=metadata_local(path);expected=row['installed_metadata']
            if any(now[k]!=expected[k] for k in ['mode','uid','gid','mtime_ns','xattrs']):raise ValueError('Legacy authenticated metadata differs: '+row['path'])

def metadata_local(path):
    from transaction import metadata
    return metadata(path)

def visible_state(device,catalog):
    device.check_mounts('ro');state=policy.detect(LOWER,catalog)
    for name in catalog['paths']+list(catalog['guards']):
        if os.path.lexists(str(safe(Path('/overlay/upper'),name))):raise ValueError('Writable overlay shadows a component')
        if file_hash(safe(Path('/'),name))!=file_hash(safe(LOWER,name)):raise ValueError('Visible and persistent component differ')
    verify_existing_metadata(device,catalog,state)
    return state

def legacy_busy():
    for root in ['/mnt/mala-public-beta','/mnt/network-link-public-beta']:
        if (Path(root)/'active.json').exists():raise ValueError('An older installer has a pending operation. Finish its recovery first.')

def load_package(folder):
    info,catalog=kit(folder);manifest=json.loads(regular(folder/'manifest.json').decode())
    expected=policy.transition(catalog,manifest['from_state'],info['component'],manifest['action'])
    if expected!=manifest:raise ValueError('Captured transition differs from the reviewed compatibility catalog')
    return manifest,policy.values(folder,manifest),info,catalog

def capture(folder,target,manifest,payload):
    target.mkdir(mode=0o700)
    names=['install.py','installer/transaction.py','installer/catalog.py','kit.json','catalog.json']
    for name in names:
        raw=regular(safe(folder,name));p=safe(target,name);p.parent.mkdir(mode=0o700,parents=True,exist_ok=True);atomic(p,raw)
    atomic(target/'manifest.json',canonical(manifest))
    for row in manifest['files']:
        if row['sha256'] is not None:
            p=target/'blobs'/row['sha256'];p.parent.mkdir(mode=0o700,exist_ok=True)
            if not p.exists():atomic(p,payload[row['path']])
    sync_dir(target);sync_dir(target.parent)

def launch(device,folder,action):
    global KIT_COMPONENT
    info,catalog=kit(folder);KIT_COMPONENT=info['component'];legacy_busy()
    device.retire_inactive_reservation(action);check_inventory(device,catalog)
    latest=device.latest();recover=False
    outcome=read_outcome(device,catalog,info['component'])
    blocked=outcome and outcome['outcome'] in ('restored-after-error','recovered')
    # A durable journal also covers a power cut after restoration but before
    # the separate closeout marker is saved. Never replay that original action.
    matching_closed_outcome=outcome and latest and outcome['transaction']==latest.record['id'] and outcome['outcome'] in ('acknowledged','restored-after-error','recovered')
    if not matching_closed_outcome and latest and latest.record['phase']=='rolled-back' and latest.record['component']==info['component'] and latest.record['action']==action:
        visible_state(device,catalog);latest.verify_restored()
        config=dict(component=info['component'],action=action,transaction=latest.record['id'])
        write_outcome(device,catalog,config,latest.record['from_state'],'restored-after-error')
        outcome=read_outcome(device,catalog,info['component']);blocked=True
    if blocked:
        visible_state(device,catalog)
        if outcome['action']==action:
            opposite='rollback' if action=='install' else 'install'
            device.report('RECOVERY VERIFIED; NO RETRY', 'The previous module set is verified. No action was retried. Remove this USB. To acknowledge recovery, run the matching '+opposite+' kit once; then deliberately use this kit again if needed.')
            return
        # Swapping to the opposite verified kit is explicit acknowledgement.
        # The same original USB left inserted can never clear this condition.
        config=dict(component=info['component'],action=action,transaction=outcome['transaction'])
        write_outcome(device,catalog,config,visible_state(device,catalog),'acknowledged')
    if latest and latest.record['phase'] not in ('committed','rolled-back'):
        if action!='rollback' or latest.record['component']!=info['component']:
            raise ValueError('Interrupted component transaction: use its matching rollback kit')
        if latest.record['catalog_sha256']!=digest(canonical(catalog)):raise ValueError('Use the matching recovery catalog')
        latest.admit_rollback();recover=True;manifest=None;payload={}
    else:
        current=visible_state(device,catalog);manifest=policy.transition(catalog,current,info['component'],action)
        if manifest is None:
            device.report('INSTALLED AND VERIFIED' if action=='install' else 'ROLLBACK VERIFIED',
                info['component']+' '+info['version']+': component state verified; other modules retained. Remove this USB drive. No repeat write/reboot occurred.')
            return
        payload=policy.values(folder,manifest);device.baseline(manifest,payload)
    device.init_data();lock=device.lock()
    try:
        if (DATA/'active.json').exists():raise ValueError('Another community operation is already reserved')
        token=uuid.uuid4().hex;op=DATA/'operations'/token;op.mkdir(mode=0o700)
        if recover:
            target=op/'package';target.mkdir(mode=0o700)
            for n in ['install.py','installer/transaction.py','installer/catalog.py','kit.json','catalog.json']:
                p=safe(target,n);p.parent.mkdir(mode=0o700,parents=True,exist_ok=True);atomic(p,regular(safe(folder,n)))
        else:capture(folder,op/'package',manifest,payload)
        config=dict(id=token,action='recover' if recover else action,component=info['component'],identity=device.identity,boot=device.boot,usb_device=device.usb_device,
            transaction=latest.record['id'] if recover else token,catalog_sha256=digest(canonical(catalog)))
        atomic(op/'operation.json',canonical(config));atomic(DATA/'active.json',canonical(dict(operation=token,component=info['component'])))
        device.report('STARTING',info['component']+' '+action+'; other components will be retained. Keep USB/power connected through the ordinary reboot.')
        try:
            command(['/usr/bin/systemd-run','--quiet','--no-block','--unit=hector-community-beta-'+token,'--property=Type=oneshot',
                '--property=TimeoutStartSec=600','--property=TimeoutStopSec=90','--property=Restart=no','--property=LimitCORE=0',
                '/usr/bin/python3','-I','-B',str(op/'package/install.py'),'--worker',str(op/'operation.json')])
        except Exception:
            (DATA/'active.json').unlink();sync_dir(DATA);raise
    finally:os.close(lock)

def worker(config_path):
    global KIT_COMPONENT
    protected(config_path);config=json.loads(regular(config_path).decode());KIT_COMPONENT=config['component'];device=Device()
    if (device.identity,device.boot,device.usb_device)!=(config['identity'],config['boot'],config['usb_device']):raise ValueError('Device,boot orUSB changed after admission')
    info,catalog=kit(config_path.parent/'package')
    if info['component']!=config['component'] or digest(canonical(catalog))!=config['catalog_sha256']:raise ValueError('Captured kit identity differs')
    lock=device.lock();tx=None;write_attempted=False;services={};fingerprints=None
    try:
        legacy_busy();device.select_services(config['component'])
        if config['action']=='recover':
            tx=device.latest()
            if tx.record['id']!=config['transaction'] or tx.record['component']!=config['component']:raise ValueError('Recovery transaction changed')
            tx.admit_rollback();payload={}
        else:
            manifest,payload,_,_=load_package(config_path.parent/'package')
            if manifest['component']!=config['component'] or manifest['action']!=config['action']:raise ValueError('Captured action differs')
            device.baseline(manifest,payload)
            store=DATA/'transactions'/config['transaction'];store.mkdir(mode=0o700)
            tx=Transaction(LOWER,store,regular(DATA/'key'));tx.prepare(manifest,payload,device.identity,device.boot)
            atomic(DATA/'latest.json',canonical(dict(id=store.name)))
        for unit in device.services:
            value=command(['/bin/systemctl','show',unit,'--property=ActiveState']);services[unit]='ActiveState=active\n' in value or 'ActiveState=activating\n' in value
        tx.record['services']=services;tx.save();device.pause();fingerprints=saved_fingerprints()
        if config['action']=='recover':tx.admit_rollback()
        else:tx.verify_preimages()
        legacy_busy();write_attempted=True;device.writable()
        if config['action']=='recover':tx.rollback();target=tx.record['from_state']
        else:tx.apply(payload);target=tx.record['to_state']
        if policy.detect(LOWER,catalog)!=target:raise ValueError('Component state failed after publication')
        if saved_fingerprints()!=fingerprints:raise ValueError('Saved settings/presets changed during the operation')
        inventory(device,catalog,target,tx.record['id']);device.readonly()
        write_outcome(device,catalog,config,target,'recovered' if config['action']=='recover' else 'committed')
        tx.record['normal_reboot_requested']=True;tx.record['readonly_closeout_pending_reboot']=device.readonly_pending_reboot;tx.save()
        device.report('RECOVERED; REBOOTING' if config['action']=='recover' else 'INSTALLED; REBOOTING' if config['action']=='install' else 'REMOVED; REBOOTING',
            'Verified the selected component change and preserved other modules, presets and settings. Keep USB connected for post-reboot verification.')
        (DATA/'active.json').unlink();sync_dir(DATA);device.reboot()
    except Exception as error:
        final='REFUSED; NO FIRMWARE WRITES';detail=str(error)
        if write_attempted and tx is not None:
            try:
                if os.statvfs(str(LOWER)).f_flag&os.ST_RDONLY:device.writable()
                tx.rollback()
                if policy.detect(LOWER,catalog)!=tx.record['from_state']:raise ValueError('Previous component set differs')
                inventory(device,catalog,tx.record['from_state'],tx.record['id']);device.readonly()
                write_outcome(device,catalog,config,tx.record['from_state'],'restored-after-error')
                final='RESTORED AFTER ERROR; REBOOTING';detail+='\nThe exact previous module set was restored. Normal reboot follows.'
            except Exception as restore_error:
                final='RECOVERY REQUIRED';detail+='\nRestoration/closeout: '+str(restore_error)+'\nKeep backups and this report. Use the matching rollback kit; do not reinstall.'
        elif device.pause_files:device.resume_before_write(services)
        device.report(final,detail)
        if final!='RECOVERY REQUIRED' and (DATA/'active.json').exists():(DATA/'active.json').unlink();sync_dir(DATA)
        if final=='RESTORED AFTER ERROR; REBOOTING':device.reboot()
        raise
    finally:os.close(lock)

def main():
    global KIT_COMPONENT
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--usb',choices=['install','rollback']);parser.add_argument('--worker',type=Path);args=parser.parse_args()
    if os.geteuid()!=0 or platform.machine() not in ('aarch64','arm64'):raise ValueError('This kit runs only on ARM64 Hector as root')
    enter_main_namespace()
    if args.worker:worker(args.worker);return
    if not args.usb:parser.error('Follow the USB installation/removal instructions')
    folder=Path(__file__).resolve().parent;info,_=kit(folder);KIT_COMPONENT=info['component'];device=None
    try:
        deadline=time.monotonic()+45
        while True:
            try:device=Device();break
            except (OSError,ValueError):
                if time.monotonic()>=deadline:raise
                time.sleep(1)
        launch(device,folder,args.usb)
    except Exception as error:
        if device is not None:device.report('REFUSED; NO NEW OPERATION STARTED',str(error))
        raise
if __name__=='__main__':
    try:main()
    except Exception as error:print('Community USB operation stopped: '+str(error),file=sys.stderr);sys.exit(1)
