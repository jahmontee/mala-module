"""Portable adapter for Mala's approved bridge; no audio or file writes."""
from pathlib import Path
from types import SimpleNamespace
from .mala_407 import MalaHub, KnobResponse


def create_backend(effect, api):
    if api.get('native_editor_lifecycle') != 1:
        raise RuntimeError('Update the native module host before opening Mala.')
    binary = Path(__file__).resolve().parents[2].with_suffix('.so')
    hub = MalaHub(api['effects'], api['connections'], api['knobs'], api['ingen'],
                  api.get('loading') or SimpleNamespace(value=False),
                  KnobResponse(binary), hardware=api['hardware'])
    if api.get('fresh'):
        hub.expect_new(effect)
    hub.created(effect)
    editor = hub.bridge(effect)

    def readback(message):
        if message[0] in ('add_connection', 'remove_connection'):
            hub.topology_changed()
        hub.readback(message)

    def close():
        hub.release(editor)
        hub.retire(effect)

    editor.readback = readback
    editor.flush = hub.flush
    editor.close = close
    return editor
