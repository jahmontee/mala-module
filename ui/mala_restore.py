"""MIT. Complete Mala frozen-state restoration after Ingen's graph controls.

Uses the existing transport/worker and Ingen preset API; no DSP or preset writes.
Only an explicit graph load can arm this one-shot completion barrier.
"""
import logging
import os
from pathlib import Path
import re
import stat
import threading
from urllib.parse import unquote, urlsplit

from mala_state import has_frozen_state

URI = 'urn:beebo-hector-lab:mala-preview'
STATE = 'http://lv2plug.in/ns/ext/state#state'
PRESET = 'http://lv2plug.in/ns/ext/presets#preset'


def first(body, key, default=None):
    values = body.get(key, [])
    return values[0] if isinstance(values, list) and values else default


def recording_bundle_uri(uri):
    """Admit only the saved serializer's self-contained Mala state bundle.

    Registering arbitrary manifests could introduce unrelated plugin metadata.
    These anchored forms admit one preset and its one inline recording only.
    """
    try:
        if not has_frozen_state(uri): return None
        path = Path(unquote(urlsplit(uri).path))
        if path.name != 'state.ttl': return None
        bodies = []
        for source, limit in ((path.parent / 'manifest.ttl', 8192), (path, 2 * 1024 * 1024)):
            fd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            with os.fdopen(fd, 'rb') as stream:
                before = os.fstat(stream.fileno())
                if not stat.S_ISREG(before.st_mode) or before.st_size > limit: return None
                text = stream.read(limit + 1)
                after = os.fstat(stream.fileno())
                identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
                if len(text) > limit or identity(before) != identity(after): return None
            prefix = re.compile(rb'\s*@prefix\s+(\w+):\s*<([^>]+)>\s*\.')
            namespaces = {}
            while True:
                match = prefix.match(text)
                if not match: break
                name, value = match[1], match[2]
                if name in namespaces: return None
                namespaces[name] = value
                text = text[match.end():]
            for name, value in {b'lv2': b'http://lv2plug.in/ns/lv2core#',
                    b'pset': b'http://lv2plug.in/ns/ext/presets#',
                    b'rdfs': b'http://www.w3.org/2000/01/rdf-schema#',
                    b'state': b'http://lv2plug.in/ns/ext/state#',
                    b'xsd': b'http://www.w3.org/2001/XMLSchema#'}.items():
                if namespaces.get(name) != value: return None
            bodies.append(text)
        plugin = re.escape(URI.encode())
        manifest = rb'\s*<state.ttl>\s+lv2:appliesTo\s+<' + plugin + rb'>\s*;\s*a\s+pset:Preset\s*;\s*rdfs:seeAlso\s+<state.ttl>\s*\.\s*'
        payload = (rb'\s*<>\s+a\s+pset:Preset\s*;\s*lv2:appliesTo\s+<' + plugin +
                   rb'>\s*;\s*state:state\s*\[\s*<' + plugin + rb'\#frozenBuffer>\s*'
                   rb'(?:"""[A-Za-z0-9+/=\s]+"""|"[A-Za-z0-9+/=\s]+")\s*\^\^xsd:base64Binary\s*\]\s*\.\s*')
        if not re.fullmatch(manifest, bodies[0]) or not re.fullmatch(payload, bodies[1]): return None
        return path.as_uri()
    except (OSError, ValueError, TypeError): return None


class MalaLoadRestore:
    def __init__(self, transport, commands, messages, timeout=5):
        self.transport, self.commands, self.messages = transport, commands, messages
        self.timeout = timeout
        self.lock = threading.RLock()
        self.generation, self.sequence = 0, 1500000000
        self.graph, self.marker, self.timer = None, None, None
        self.nodes, self.pending, self.holds = {}, {}, set()
        self.restored, self.failed = set(), set()

    def load(self, filename, graph):
        with self.lock:
            self.generation += 1
            if self.timer: self.timer.cancel()
            self.timer = None
            self.graph = graph if graph.startswith('ingen:') else 'ingen:' + graph
            self.marker = None
            self.nodes, self.pending, self.holds = {}, {}, set()
            self.restored, self.failed = set(), set()
        self.transport.copy(filename, graph)

    def handle(self, message):
        """Return true only for our held completion marker or matched replies."""
        with self.lock:
            if self.graph is None: return False
            kinds = message.get('a', [])
            subject = first(message, 'patch:subject', '')
            if 'patch:Response' in kinds:
                try:
                    sequence = int(first(message, 'patch:sequenceNumber'))
                    status = int(first(message, 'patch:body'))
                except (TypeError, ValueError): return False
                if sequence not in self.pending: return False
                node, phase = self.pending.pop(sequence)
                if status != 0:
                    self.failed.add(node)
                    self._failure(node, 'engine rejected state ' + phase)
                elif phase == 'restore': self.restored.add(node)
                if not self.pending:
                    self._finish()
                return True
            if not isinstance(subject, str): return False
            if ('patch:Put' in kinds and self.marker is None
                    and subject.startswith(self.graph + '/')
                    and re.fullmatch(r'ingen:/[A-Za-z0-9_/-]+', subject)):
                body = message.get('patch:body')
                if isinstance(body, dict) and first(body, 'lv2:prototype') == URI:
                    state = first(body, STATE)
                    safe_uri = recording_bundle_uri(state) if state else None
                    if safe_uri:
                        enabled = first(body, 'ingen:enabled', 'true') not in (False, 'false', 0, '0')
                        self.nodes[subject] = (safe_uri, enabled)
            if ('patch:Set' in kinds and subject == self.graph
                    and first(message, 'patch:property') == 'ingen:file'):
                if self.marker is not None: return True
                self.marker = message
                if not self.nodes:
                    self.graph, self.marker = None, None
                    return False  # Stock completion unchanged for other patches.
                for node, (state, enabled) in self.nodes.items():
                    if not enabled:
                        # A bypassed plugin has not run: its initial restore
                        # baseline is still pending. Preset API would enable it.
                        self.holds.add(node)
                        continue
                    numbers = []
                    for phase in ('register', 'restore', 'clear-reference', 'unregister'):
                        self.sequence += 1
                        numbers.append(self.sequence)
                        self.pending[self.sequence] = (node, phase)
                    self.commands.put((self._send, self.generation, numbers, node, state))
                if self.pending:
                    self.timer = threading.Timer(self.timeout, self._expire, (self.generation,))
                    self.timer.daemon = True
                    self.timer.start()
                else: self._finish()
                return True
            return False

    def _send(self, generation, numbers, node, state):
        with self.lock:
            if generation != self.generation or not all(n in self.pending for n in numbers): return
            if recording_bundle_uri(state) != state:
                for number in numbers: self.pending.pop(number)
                self._failure(node, 'saved recording changed or became unavailable')
                if not self.pending: self._finish()
                return
            bundle = state.rsplit('/', 1)[0] + '/'
            # Ingen's preset API resolves through Lilv's world rather than its
            # initial-state file reader. Register only this existing state
            # bundle for the request, then remove that temporary cache entry.
            self.transport.send('[] a patch:Set ; patch:subject <ingen:/> ; '
                'patch:property <http://drobilla.net/ns/ingen#loadedBundle> ; '
                'patch:value <' + bundle + '> ; patch:sequenceNumber "' + str(numbers[0]) + '"^^xsd:int .\n' +
                '[] a patch:Set ; patch:subject <' + node +
                '> ; patch:property <' + PRESET + '> ; patch:value <' + state +
                '> ; patch:sequenceNumber "' + str(numbers[1]) + '"^^xsd:int .\n' +
                # The preset command is transient, not a saved dependency on
                # the old preset's directory. Keep the original state:state
                # serialization responsible for each newly saved recording.
                '[] a patch:Patch ; patch:subject <' + node + '> ; patch:remove [ <' + PRESET +
                '> <' + state + '> ] ; patch:add [] ; patch:sequenceNumber "' + str(numbers[2]) + '"^^xsd:int .\n' +
                '[] a patch:Patch ; patch:subject <ingen:/> ; '
                'patch:remove [ <http://drobilla.net/ns/ingen#loadedBundle> <' + bundle + '> ] ; '
                'patch:add [] ; patch:sequenceNumber "' + str(numbers[3]) + '"^^xsd:int .\n')

    def _failure(self, node, reason):
        self.failed.add(node)
        logging.warning('Mala frozen-state completion: %s', reason)
        self.messages.put(('mala_restore_failed', node))

    def _expire(self, generation):
        with self.lock:
            if generation != self.generation or not self.pending: return
            for node in {row[0] for row in self.pending.values()}:
                self._failure(node, 'state restoration response timed out')
            self.pending.clear()
            self._finish()

    def _finish(self):
        if self.timer: self.timer.cancel()
        self.timer = None
        self.holds.update(self.restored - self.failed)
        for node in sorted(self.holds):
            self.messages.put(('mala_restored_freeze', node, True))
        if self.marker is not None:
            self.messages.put(('pedalboard_loaded', first(self.marker, 'patch:subject'),
                               str(first(self.marker, 'patch:value'))))
        self.graph, self.marker = None, None
        self.nodes, self.pending, self.holds = {}, {}, set()
        self.restored, self.failed = set(), set()
