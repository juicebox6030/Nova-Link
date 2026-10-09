"""Constants and errors shared by the NOVA-LINK codecs.

Everything here mirrors include/nova_link/nl_common.h. The C implementation
is the source of truth; tests/vectors/*.json are generated from it.
"""

import re

VERSION_MAJOR = 0
VERSION_MINOR = 1
VERSION_PATCH = 0
LINK_PROTOCOL_VERSION = 1

NUM_ZONES = 8
NUM_ORIGINS = 8
META_ZONE = 0
FRAGMENT_HEADER_SIZE = 2
MAX_PAYLOAD = 100
MAX_FRAGMENT = FRAGMENT_HEADER_SIZE + MAX_PAYLOAD

# nl_status_t codes and the short names used in the vector files.
STATUS_CODES = {
    "ok": 0,
    "arg": -1,
    "size": -2,
    "full": -3,
    "empty": -4,
    "perm": -5,
    "conflict": -6,
    "not_found": -7,
    "crc": -8,
    "proto": -9,
    "io": -10,
}
STATUS_NAMES = {code: name for name, code in STATUS_CODES.items()}


class NLError(ValueError):
    """A codec rejected its input the same way the C function would.

    ``status`` is the short status name ("arg", "size", "proto", ...) and
    ``code`` the matching negative nl_status_t value.
    """

    def __init__(self, status, message=""):
        if status not in STATUS_CODES:
            raise KeyError(status)
        self.status = status
        self.code = STATUS_CODES[status]
        super().__init__(message or status)


def check_u8(value, what):
    """Reject values that do not fit the C uint8_t field (Python is stricter)."""
    if not isinstance(value, int) or not 0 <= value <= 0xFF:
        raise NLError("arg", "%s must be 0..255, got %r" % (what, value))
    return value


def check_uint(value, bits, what):
    if not isinstance(value, int) or not 0 <= value < (1 << bits):
        raise NLError("arg", "%s must fit in %d bits, got %r" % (what, bits, value))
    return value


_HEX_JUNK = re.compile(r"0x|\\x|[\s:,;\-_]", re.IGNORECASE)


def parse_hex(text):
    """Parse a hex dump into bytes.

    Accepts "aa 01 00 15", "AA:01:00:15", "0xAA,0x01", "\\xaa\\x01" and plain
    "aa010015". Raises ValueError on anything else.
    """
    cleaned = _HEX_JUNK.sub("", text)
    if len(cleaned) % 2:
        raise ValueError("odd number of hex digits in %r" % text)
    try:
        return bytes.fromhex(cleaned)
    except ValueError:
        raise ValueError("not a hex string: %r" % text) from None


def hexstr(data, sep=""):
    """Lowercase hex, optionally separated (``sep=" "`` for dumps)."""
    return data.hex(sep) if sep else data.hex()
