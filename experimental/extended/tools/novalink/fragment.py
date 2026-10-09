"""DataFragment codec (mirrors src/nl_fragment.c).

Wire format::

    byte 0   origin<<5 | zone<<2 | flags      (flags: BURST 0x02, MGMT_LISTEN 0x01)
    byte 1   sequence number
    2..101   payload, 0..100 bytes
"""

from dataclasses import dataclass

from .common import (FRAGMENT_HEADER_SIZE, MAX_FRAGMENT, MAX_PAYLOAD, META_ZONE,
                     NUM_ORIGINS, NUM_ZONES, NLError)

FLAG_MGMT_LISTEN = 0x01
FLAG_BURST = 0x02
FLAG_MASK = 0x03


def make_header(origin, zone, flags):
    return ((origin & 0x07) << 5) | ((zone & 0x07) << 2) | (flags & FLAG_MASK)


def flag_names(flags):
    names = []
    if flags & FLAG_BURST:
        names.append("BURST")
    if flags & FLAG_MGMT_LISTEN:
        names.append("MGMT_LISTEN")
    return names


def seq_cmp(a, b):
    """Serial-number comparison of two 8-bit sequence numbers (nl_seq_cmp)."""
    d = (a - b) & 0xFF
    if d == 0:
        return 0
    return d if d < 128 else -((b - a) & 0xFF)


@dataclass(frozen=True)
class Fragment:
    origin: int
    zone: int
    flags: int
    seq: int
    payload: bytes = b""

    @property
    def burst(self):
        return bool(self.flags & FLAG_BURST)

    @property
    def mgmt_listen(self):
        return bool(self.flags & FLAG_MGMT_LISTEN)

    @property
    def is_meta(self):
        return self.zone == META_ZONE

    def encode(self):
        return encode_fragment(self.origin, self.zone, self.flags, self.seq, self.payload)

    @classmethod
    def decode(cls, buf):
        return decode_fragment(buf)

    def to_dict(self):
        return {
            "origin": self.origin,
            "zone": self.zone,
            "flags": self.flags,
            "flag_names": flag_names(self.flags),
            "seq": self.seq,
            "payload": self.payload.hex(),
            "payload_len": len(self.payload),
        }


def encode_fragment(origin, zone, flags, seq, payload=b""):
    """Encode like nl_fragment_encode: ARG for a bad origin/zone/flags, SIZE for
    a payload over 100 bytes."""
    payload = bytes(payload)
    if not (isinstance(origin, int) and 0 <= origin < NUM_ORIGINS):
        raise NLError("arg", "origin must be 0..7")
    if not (isinstance(zone, int) and 0 <= zone < NUM_ZONES):
        raise NLError("arg", "zone must be 0..7")
    if not isinstance(flags, int) or flags & ~FLAG_MASK:
        raise NLError("arg", "flags must be a subset of 0x03")
    if len(payload) > MAX_PAYLOAD:
        raise NLError("size", "payload is %d bytes, max %d" % (len(payload), MAX_PAYLOAD))
    if not (isinstance(seq, int) and 0 <= seq <= 0xFF):
        raise NLError("arg", "seq must be 0..255")
    return bytes((make_header(origin, zone, flags), seq)) + payload


def decode_fragment(buf):
    """Decode like nl_fragment_decode: SIZE unless 2 <= len <= 102."""
    buf = bytes(buf)
    if len(buf) < FRAGMENT_HEADER_SIZE or len(buf) > MAX_FRAGMENT:
        raise NLError("size", "fragment is %d bytes, expected 2..%d" % (len(buf), MAX_FRAGMENT))
    hdr = buf[0]
    return Fragment(hdr >> 5, (hdr >> 2) & 0x07, hdr & FLAG_MASK, buf[1], buf[2:])
