"""MIT. Read bounded Mala preset metadata on the existing transport worker.

This identifies a genuine restored recording without changing LV2 state, ports,
or DSP. It accepts the local state.ttl form written by the preserved Ingen/Lilv.
"""
import base64
from functools import lru_cache
import os
from pathlib import Path
import re
import stat
import struct
from urllib.parse import unquote, urlsplit
import zlib

_KEY = rb'<urn:beebo-hector-lab:mala-preview#frozenBuffer>'
_VALUE = re.compile(_KEY + rb'\s+(?:"""([A-Za-z0-9+/=\s]+)"""|"([A-Za-z0-9+/=\s]+)")'
                    rb'\s*\^\^(xsd:base64Binary|<http://www.w3.org/2001/XMLSchema#base64Binary>)')
_MAX_FILE = 2 * 1024 * 1024


def _identity(s):
    return s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns


@lru_cache(maxsize=64)
def _read_frozen(path, identity):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as source:
        s = os.fstat(source.fileno())
        if not stat.S_ISREG(s.st_mode) or _identity(s) != identity or s.st_size > _MAX_FILE:
            return False
        text = source.read(_MAX_FILE + 1)
        if len(text) > _MAX_FILE or _identity(os.fstat(source.fileno())) != identity:
            return False
    matches = list(_VALUE.finditer(text))
    if len(matches) != 1:
        return False
    match = matches[0]
    if match[3] == b'xsd:base64Binary' and not re.search(
            rb'@prefix\s+xsd:\s*<http://www.w3.org/2001/XMLSchema#>\s*\.', text):
        return False
    data = base64.b64decode(re.sub(rb'\s', b'', match[1] or match[2]), validate=True)
    if len(data) != 768032:
        return False  # Includes the valid-but-empty 32-byte state marker.
    tag, version, size, pointer = struct.unpack_from('<4I', data)
    if (tag, version, size) != (0x5a5a5246, 1, 768000) or data[16] > 3 or data[17] > 1:
        return False
    if any(data[i] for i in (18, 19, 24, 25, 26, 27, 28, 29, 30, 31)):
        return False
    capacity = 6144000 // ((8, 12, 12, 16)[data[16]] * (1 if data[17] else 2))
    return (pointer < capacity and
            zlib.crc32(data[32:], zlib.crc32(data[:20])) == struct.unpack_from('<I', data, 20)[0])


def has_frozen_state(uri):
    """Return a boolean hint only: no network, RDF execution or state mutation."""
    try:
        if not isinstance(uri, str): return False
        u = urlsplit(uri)
        if u.scheme != 'file' or u.netloc not in ('', 'localhost') or u.query or u.fragment:
            return False
        p = Path(unquote(u.path))
        if not p.is_absolute() or p.suffix != '.ttl': return False
        s = p.lstat()
        if not stat.S_ISREG(s.st_mode) or s.st_size > _MAX_FILE: return False
        return _read_frozen(str(p), _identity(s))
    except (OSError, ValueError, struct.error):
        return False
