"""Mala's Qt 5 boundary to the public firmware 407 UI (MIT; see mala.LICENSE).

No audio instances, workers, sockets, preset files or hardware are opened here.
Only the new Mala bundle's pure knob lookup function is called from Python.
"""
import ctypes
import json
import math
from pathlib import Path
import time

from PySide2.QtCore import QObject, Property, Signal, Slot, QTimer

PORTS = json.loads((Path(__file__).parent / 'mala-ports.json').read_text())
SPEC = {p['symbol']: p for p in PORTS if 'audio' not in p and 'cv' not in p}
INPUTS = {s: p for s, p in SPEC.items() if p.get('control') != 'Output'}
OUTPUTS = set(SPEC) - set(INPUTS)
CV = ('time_cv', 'size_cv', 'shape_cv', 'pitch_cv', 'density_cv', 'assign_cv', 'seed_gate', 'freeze_gate')
AUDIO = ('left_in', 'right_in')
OUT = ('left_out', 'right_out')
DERIVED = ('connections', 'audio_connections', 'output_connections')
FRESH = ('input_stage', 'synth_enable', 'buffer_autosave', 'output_normalization', 'panel_response')
PANEL = ('time', 'size', 'shape', 'pitch', 'density', 'time_amount', 'size_amount',
         'shape_amount', 'pitch_amount', 'feedback', 'mix', 'reverb')

# Apply only after the host explicitly requests a new Mala instance. Keep LV2
# metadata/legacy fallback defaults intact for existing saved patches.
FRESH_KNOB_DEFAULTS = dict(time=.5, size=.5, shape=.5, pitch=0., density=.5,
    time_amount=0., size_amount=0., shape_amount=0., pitch_amount=0.,
    feedback=0., mix=.5, reverb=0.)


def prototype(entry):
    """Additive catalog entry; LV2 defaults/ranges remain the port contract."""
    result = {k: entry[k] for k in ('category', 'description', 'long_description', 'tags')}
    result.update(controls={s: [p['name'], p.get('default', 0), p['min'], p['max']] +
        (['int'] if p.get('integer') or p.get('toggled') else []) for s, p in INPUTS.items()},
        inputs={p['symbol']: [p['name'], 'AudioPort' if 'audio' in p else 'CVPort']
                for p in PORTS if p.get('audio', p.get('cv')) == 'Input'},
        outputs={p['symbol']: [p['name'], 'AudioPort'] for p in PORTS if p.get('audio') == 'Output'},
        broadcast_ports={s: [SPEC[s]['name'], 0, SPEC[s]['min'], SPEC[s]['max']] for s in sorted(OUTPUTS)},
        num_cv_in=len(CV))
    return result


class KnobResponse:
    def __init__(self, library):
        # The path is the future Mala bundle alongside the UI, never a firmware ELF.
        self.library = ctypes.CDLL(str(library))
        self.function = self.library.mala_knob_response
        self.function.argtypes = [ctypes.c_uint32, ctypes.c_float]
        self.function.restype = ctypes.c_float

    def target(self, symbol, position):
        return self.function(2 if symbol == 'pitch' else 1 if symbol.endswith('_amount') else 0, position)

    def position(self, symbol, value, enabled):
        p = SPEC[symbol]
        if not enabled or symbol not in PANEL:
            return (value - p['min']) / (p['max'] - p['min'])
        if symbol not in ('pitch',) + PANEL[5:9]:
            return max(0, min(1, value))
        if value <= p['min']: return 0.
        if value >= p['max']: return 1.
        def bound(strict):
            lo, hi = 0, 65536
            while lo < hi:
                mid = (lo + hi) // 2
                v = self.target(symbol, mid / 65536)
                if (v > value if strict else v >= value): hi = mid
                else: lo = mid + 1
            return lo
        first, last = bound(False), bound(True)
        return min(1, ((first + last - 1) / 2 if last > first else first) / 65536)


class Control(QObject):
    changed = Signal()
    def __init__(self, spec, parent):
        super().__init__(parent)
        self.spec = spec
        self.current = spec.get('default', 0)
    def update(self, value):
        value = float(value)
        if not math.isfinite(value): return False
        value = max(self.spec['min'], min(self.spec['max'], value))
        if self.spec.get('integer') or self.spec.get('toggled'): value = round(value)
        if value == self.current: return False
        self.current = value
        self.changed.emit()
        return True
    value = Property(float, lambda s: s.current, notify=changed)
    name = Property(str, lambda s: s.spec['name'], constant=True)
    rmin = Property(float, lambda s: s.spec['min'], constant=True)
    rmax = Property(float, lambda s: s.spec['max'], constant=True)


class Editor(QObject):
    changed = Signal()
    def __init__(self, hub, identifier):
        super().__init__(hub)
        self.hub, self.identifier = hub, identifier
        self.record = hub.effects[identifier]
        self.values = {s: Control(p, self) for s, p in SPEC.items()}
        self.positions = {}
        self.seed_down = self.ignore_seed_release = False
        self.manual_gain = 128
        self.hold_timer = QTimer(self)
        self.hold_timer.setSingleShot(True)
        self.hold_timer.timeout.connect(self.latch_hold)
        self.notches = [dict(value=v, position=hub.response.position('pitch', v, True))
                        for v in (-24, -12, -7, -4, -3, -1, 0, 1, 3, 4, 7, 12, 24)]
        self.sync()

    def alive(self):
        return (not self.hub.loading.value and self.hub.effects.get(self.identifier) is self.record
                and self.hub.records.get(self.identifier) is self.record)

    @Slot(str, result=str)
    def midiType(self, symbol):
        if not self.alive() or symbol not in INPUTS or symbol in DERIVED:
            return ''
        p = INPUTS[symbol]
        return 'bool' if p.get('toggled') else 'int' if p.get('integer') else 'float'

    def sync(self):
        if not self.alive(): return
        modified, inputs_changed = False, set()
        for group in ('controls', 'broadcast_ports'):
            for s, obj in self.record[group].items():
                if s in self.values and self.values[s].update(obj.value):
                    modified = True
                    if s in INPUTS: inputs_changed.add(s)
        enabled = self.values['panel_response'].value > .5
        for s in INPUTS:
            if s not in self.positions or s in inputs_changed or 'panel_response' in inputs_changed:
                self.positions[s] = self.hub.response.position(s, self.values[s].value, enabled)
                modified = True
        if self.values['input_gain'].value > 0: self.manual_gain = int(self.values['input_gain'].value)
        if modified: self.changed.emit()

    @Slot(str, float)
    def change(self, symbol, value):
        if not self.alive() or symbol not in INPUTS or symbol in DERIVED: return
        value = float(value)
        if not math.isfinite(value): return
        p = INPUTS[symbol]
        value = max(p['min'], min(p['max'], value))
        if p.get('integer') or p.get('toggled'): value = round(value)
        if symbol in ('freeze', 'freeze_release'):
            self.hub.restored_holds.discard(self.identifier)
        if symbol == 'input_gain' and value > 0: self.manual_gain = int(value)
        # LV2 integer/toggle hints still use float control buffers in Ingen.
        self.hub.knobs.ui_knob_change(self.identifier, symbol, float(value))
        self.sync()

    @Slot(str, float)
    def moveKnob(self, symbol, position):
        if symbol not in INPUTS or symbol in DERIVED or not math.isfinite(position) or not 0 <= position <= 1: return
        p = INPUTS[symbol]
        value = (self.hub.response.target(symbol, position) if symbol in PANEL and
                 self.values['panel_response'].value > .5 else p['min'] + position * (p['max'] - p['min']))
        self.change(symbol, value)
        if self.alive():
            self.positions[symbol] = position
            self.changed.emit()

    @Slot()
    def seedPress(self):
        if not self.alive(): return
        self.seed_down, self.ignore_seed_release = True, False
        self.pressed_at = time.monotonic()
        self.hold_timer.start(4000)
        self.change('seed', 1)
    @Slot()
    def seedRelease(self):
        if not self.seed_down: return
        self.seed_down = False
        self.hold_timer.stop()
        self.change('seed', 2 if self.ignore_seed_release or time.monotonic() - self.pressed_at >= 4 else 0)
    def latch_hold(self):
        if self.seed_down and self.alive():
            self.ignore_seed_release = True
            self.change('seed', 2)
    @Slot()
    def toggleLatch(self): self.change('seed', 0 if self.values['seed'].value == 2 else 2)
    @Slot()
    def toggleFreeze(self):
        if self.seed_down:
            self.ignore_seed_release = True
            self.change('seed', 2)
        else:
            restored = (self.identifier in self.hub.restored_holds
                        and self.values['freeze'].value <= .5
                        and self.values['active_freeze'].value > .5)
            if self.values['freeze'].value > .5 or restored:
                self.change('freeze_release', (self.values['freeze_release'].value + 1) % 16777216)
            self.change('freeze', 0 if restored else 1 - self.values['freeze'].value)
    @Slot(bool)
    def autoGain(self, enabled): self.relearnGain() if enabled else self.change('input_gain', self.manual_gain)
    @Slot()
    def relearnGain(self):
        self.change('input_gain', 0)
        self.change('gain_relearn', (self.values['gain_relearn'].value + 1) % 16777216)
    controls = Property('QVariantMap', lambda s: s.values, constant=True)
    panelPositions = Property('QVariantMap', lambda s: s.positions.copy(), notify=changed)
    pitchNotches = Property('QVariantList', lambda s: s.notches, constant=True)
    seedLatched = Property(bool, lambda s: s.values['seed'].value == 2, notify=changed)
    qualityLocked = Property(bool, lambda s: s.values['freeze'].value > .5 or s.values['active_freeze'].value > .5, notify=changed)
    patchedInputs = Property('QVariantMap', lambda s: dict(
        [(key, bool(int(s.values['connections'].value) & (1 << i))) for i, key in enumerate(CV)] +
        [(key, bool(int(s.values['audio_connections'].value) & (1 << i))) for i, key in enumerate(AUDIO)]), notify=changed)


class MalaHub(QObject):
    def __init__(self, effects, connections, knobs, transport, loading, response=None, hardware='beebo'):
        super().__init__()
        self.effects, self.connections, self.knobs = effects, connections, knobs
        self.transport, self.loading = transport, loading
        self.response = response  # Lazy: non-Mala startup never loads any new ELF.
        self.hardware = hardware
        self.records, self.editors, self.retired = {}, {}, []
        self.live_outputs = {}
        self.restore_seen, self.restored_holds = set(), set()
        self.expected, self.fresh, self.dirty_editors = set(), set(), set()
        self.topology_dirty = False

    def expect_new(self, identifier): self.expected.add(identifier)
    def created(self, identifier):
        record = self.effects[identifier]
        if record['effect_type'] != 'mala': return
        self.retire(identifier)
        self.records[identifier] = record
        self.live_outputs[identifier] = set()
        if identifier in self.expected:
            self.fresh.add(identifier)
            self.expected.discard(identifier)
        self.topology_dirty = True

    def retire(self, identifier):
        self.restore_seen.discard(identifier)
        self.restored_holds.discard(identifier)
        self.records.pop(identifier, None)
        self.live_outputs.pop(identifier, None)
        self.fresh.discard(identifier)
        self.dirty_editors.discard(identifier)
        editor = self.editors.pop(identifier, None)
        if editor:
            editor.hold_timer.stop()
            self.retired.append(editor)  # QML may still be closing this record.
        self.topology_dirty = bool(self.records)

    def begin_load(self):
        for identifier in list(self.records): self.retire(identifier)
        self.expected.clear()

    def topology_changed(self): self.topology_dirty = bool(self.records)

    def readback(self, message):
        if message[0] == 'mala_restore_failed':
            self.restored_holds.discard(message[1].removeprefix('ingen:'))
            return
        if message[0] == 'mala_restored_freeze':
            identifier = message[1].removeprefix('ingen:')
            if identifier in self.records and identifier not in self.restore_seen:
                self.restore_seen.add(identifier)
                # Only an actual preset load can arm a restored hold. A later
                # graph Get or UI rediscovery must not reinterpret a live gate.
                if self.loading.value and message[2]: self.restored_holds.add(identifier)
            return
        if message[0] not in ('value_change', 'broadcast_update'): return
        identifier, symbol = message[1].removeprefix('ingen:').rsplit('/', 1)
        record = self.records.get(identifier)
        if record is None: return
        if symbol == 'freeze':
            try:
                if float(message[2]) != record['controls']['freeze'].value:
                    self.restored_holds.discard(identifier)
            except (TypeError, ValueError): return
        if symbol in DERIVED: self.topology_dirty = True
        if symbol in OUTPUTS:
            # Ingen graph Put snapshots carry output descriptor defaults. Once
            # a live monitor Set has arrived, a later Get must not erase it.
            if message[0] == 'value_change' and symbol in self.live_outputs[identifier]: return
            try:
                value = float(message[2])
                if math.isfinite(value):
                    record['broadcast_ports'][symbol].value = value
                    if message[0] == 'broadcast_update': self.live_outputs[identifier].add(symbol)
                    if (message[0] == 'broadcast_update' and symbol == 'active_freeze' and value < .5
                            and record['enabled'].value):
                        self.restored_holds.discard(identifier)
            except (TypeError, ValueError): return
        self.dirty_editors.add(identifier)

    def flush(self):
        if self.loading.value: return
        for identifier in sorted(self.fresh):
            for s in FRESH: self.knobs.ui_knob_change(identifier, s, 1.)
            for s in PANEL:
                self.knobs.ui_knob_change(identifier, s, FRESH_KNOB_DEFAULTS[s])
            self.knobs.ui_knob_change(identifier, 'cv_input_units', float(self.hardware == 'hector'))
        self.fresh.clear()
        if self.topology_dirty:
            # 407 maps destination/input -> [source/output, ...], not tail -> head.
            masks = {i: dict.fromkeys(DERIVED, 0) for i in self.records}
            for head, tails in self.connections.items():
                if not tails: continue
                identifier, symbol = head.rsplit('/', 1)
                if identifier in masks:
                    if symbol in CV: masks[identifier]['connections'] |= 1 << CV.index(symbol)
                    if symbol in AUDIO: masks[identifier]['audio_connections'] |= 1 << AUDIO.index(symbol)
                for identifier, symbol in tails:
                    if identifier in masks and symbol in OUT:
                        masks[identifier]['output_connections'] |= 1 << OUT.index(symbol)
            for i, values in masks.items():
                for s, value in values.items():
                    if self.records[i]['controls'][s].value != value:
                        self.knobs.ui_knob_change(i, s, float(value))
                self.dirty_editors.add(i)
            self.topology_dirty = False
        for identifier in self.dirty_editors:
            if identifier in self.editors: self.editors[identifier].sync()
        self.dirty_editors.clear()

    @Slot(str, result=QObject)
    def bridge(self, identifier):
        if identifier not in self.records: return None
        if self.response is None:
            # Planned package layout. Missing/foreign ABI is an explicit integration blocker.
            self.response = KnobResponse('/usr/lib/lv2/mala.lv2/mala.so')
        if identifier not in self.editors:
            self.editors[identifier] = Editor(self, identifier)
            for s in sorted(OUTPUTS): self.transport.set_broadcast(identifier + '/' + s, True)
        return self.editors[identifier]

    @Slot(QObject)
    def release(self, editor):
        if editor is None: return
        if editor in self.retired:
            self.retired.remove(editor)
        elif self.editors.get(editor.identifier) is editor:
            self.editors.pop(editor.identifier)
            for s in sorted(OUTPUTS): self.transport.set_broadcast(editor.identifier + '/' + s, False)
        else: return
        editor.hold_timer.stop()
        # Never leave a momentary Seed held after navigating away.
        editor.seedRelease()
        editor.deleteLater()
