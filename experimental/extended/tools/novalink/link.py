"""Host <-> radio link framing and payload codecs (mirrors src/nl_link.c).

Frame layout::

    0xAA  CMD  LEN  DATA[LEN]  CRC8

CRC8 is CRC-8/SMBUS (poly 0x07, init 0x00, no reflection, no final XOR)
computed over CMD, LEN and DATA. LEN is at most 128. CMD 0x00 and 0xFF are
never valid: they are what an idle or floating MISO line reads as.

Two receivers exist in C and both are mirrored here:

* :func:`decode_frame` is ``nl_link_decode``: it scans a whole buffer (one SPI
  transaction) for the first valid frame. Both the radio and the host SPI
  driver use it. :func:`decode_stream` repeats it the way the radio does.
* :class:`LinkParser` is the byte-at-a-time ``nl_link_parser_feed`` state
  machine. It does not rescan bytes it already consumed, so after a false
  SYNC or a CRC failure it can miss frames that :func:`decode_frame` finds.
"""

import struct
from dataclasses import dataclass, field, fields
from enum import IntEnum
from typing import List, Optional

from .common import (LINK_PROTOCOL_VERSION, NUM_ORIGINS, NUM_ZONES, VERSION_MAJOR,
                     VERSION_MINOR, VERSION_PATCH, NLError, check_u8, check_uint)

SYNC = 0xAA
OVERHEAD = 4
MAX_DATA = 128
FRAME_MAX = MAX_DATA + OVERHEAD


class Cmd(IntEnum):
    PING = 0x01
    PULL = 0x02
    PUSH = 0x03
    STATUS = 0x04
    ZONE_CONFIG = 0x05
    RADIO_CONFIG = 0x06
    RSP_FRAGMENT = 0xD0
    RSP_PONG = 0xD1
    RSP_STATUS = 0xD4


def cmd_name(cmd):
    try:
        return Cmd(cmd).name
    except ValueError:
        return "0x%02X" % cmd


def cmd_invalid(cmd):
    """NL_LINK_CMD_INVALID: 0x00 and 0xFF are idle-line patterns."""
    return cmd in (0x00, 0xFF)


# ---- CRC --------------------------------------------------------------------

def _crc_table():
    table = []
    for i in range(256):
        c = i
        for _ in range(8):
            c = ((c << 1) ^ 0x07) & 0xFF if c & 0x80 else (c << 1) & 0xFF
        table.append(c)
    return bytes(table)


_CRC_TABLE = _crc_table()


def crc8(data, crc=0):
    """nl_crc8(crc, data, len): CRC-8/SMBUS, chainable via ``crc``."""
    for b in data:
        crc = _CRC_TABLE[crc ^ b]
    return crc


# ---- Framing ----------------------------------------------------------------

@dataclass(frozen=True)
class LinkFrame:
    cmd: int
    data: bytes = b""

    @property
    def name(self):
        return cmd_name(self.cmd)

    def encode(self):
        return encode_frame(self.cmd, self.data)


@dataclass(frozen=True)
class DecodeResult:
    """Outcome of one nl_link_decode call.

    ``status`` is "ok", "empty" (no frame) or "crc" (no valid frame and at
    least one candidate failed its checksum). ``consumed`` is how many bytes
    the caller should drop; on failure it is the whole buffer.
    """
    status: str
    frame: Optional[LinkFrame]
    consumed: int


def encode_frame(cmd, data=b""):
    """nl_link_encode. SIZE if data exceeds 128 bytes.

    Like C, an invalid CMD (0x00/0xFF) is *not* rejected even though no
    receiver will accept the resulting frame.
    """
    data = bytes(data)
    check_u8(cmd, "cmd")
    if len(data) > MAX_DATA:
        raise NLError("size", "link data is %d bytes, max %d" % (len(data), MAX_DATA))
    body = bytes((cmd, len(data))) + data
    return bytes((SYNC,)) + body + bytes((crc8(body),))


def decode_frame(buf):
    """nl_link_decode: return the first valid frame anywhere in ``buf``."""
    buf = bytes(buf)
    n = len(buf)
    result = "empty"
    i = 0
    while i + OVERHEAD <= n:
        if buf[i] != SYNC or cmd_invalid(buf[i + 1]):
            i += 1
            continue
        dlen = buf[i + 2]
        if dlen > MAX_DATA or i + dlen + OVERHEAD > n:
            i += 1
            continue
        if crc8(buf[i + 1:i + 3 + dlen]) != buf[i + 3 + dlen]:
            result = "crc"
            i += 1
            continue
        frame = LinkFrame(buf[i + 1], buf[i + 3:i + 3 + dlen])
        return DecodeResult("ok", frame, i + dlen + OVERHEAD)
    return DecodeResult(result, None, n)


def decode_stream(buf):
    """Call :func:`decode_frame` repeatedly on the remaining bytes until it
    stops returning "ok" or the buffer is used up (the radio's SPI loop).

    Returns the list of every :class:`DecodeResult`, including the final
    non-ok one, exactly like the ``decode`` section of link_frames.json.
    """
    buf = bytes(buf)
    out = []
    off = 0
    while True:
        r = decode_frame(buf[off:])
        out.append(r)
        if r.status != "ok":
            break
        off += r.consumed
        if off >= len(buf):
            break
    return out


class LinkParser:
    """Byte-at-a-time receiver mirroring nl_link_parser_t / nl_link_parser_feed."""

    SYNC_STATE, CMD_STATE, LEN_STATE, DATA_STATE, CRC_STATE = range(5)

    def __init__(self):
        self.state = self.SYNC_STATE
        self.pos = 0
        self.cmd = 0
        self.len = 0
        self.data = bytearray(MAX_DATA)
        self.crc_errors = 0
        self.len_errors = 0
        self.cmd_errors = 0

    def feed(self, byte):
        """Feed one byte. Returns a :class:`LinkFrame` when one completes."""
        st = self.state
        if st == self.SYNC_STATE:
            if byte == SYNC:
                self.state = self.CMD_STATE
            return None
        if st == self.CMD_STATE:
            if cmd_invalid(byte):
                self.cmd_errors += 1
                self.state = self.SYNC_STATE
                return None
            if byte == SYNC:
                return None  # "AA AA ...": the second byte is the real SYNC
            self.cmd = byte
            self.state = self.LEN_STATE
            return None
        if st == self.LEN_STATE:
            if byte > MAX_DATA:
                self.len_errors += 1
                self.state = self.CMD_STATE if byte == SYNC else self.SYNC_STATE
                return None
            self.len = byte
            self.pos = 0
            self.state = self.DATA_STATE if byte else self.CRC_STATE
            return None
        if st == self.DATA_STATE:
            self.data[self.pos] = byte
            self.pos += 1
            if self.pos == self.len:
                self.state = self.CRC_STATE
            return None
        if st == self.CRC_STATE:
            data = bytes(self.data[:self.len])
            self.state = self.SYNC_STATE
            if crc8(bytes((self.cmd, self.len)) + data) != byte:
                self.crc_errors += 1
                return None
            return LinkFrame(self.cmd, data)
        self.state = self.SYNC_STATE
        return None

    def feed_bytes(self, data):
        """Feed many bytes; returns ``[(index, LinkFrame), ...]`` where index is
        the position of the byte that completed each frame."""
        out = []
        for i, b in enumerate(bytes(data)):
            f = self.feed(b)
            if f is not None:
                out.append((i, f))
        return out


# ---- Payload codecs ---------------------------------------------------------

class Band(IntEnum):
    SUBGHZ = 0
    GHZ24 = 1
    DUAL = 2


class TxPolicy(IntEnum):
    IMMEDIATE = 0
    IN_SLOT = 1


def _enum_name(enum, value):
    try:
        return enum(value).name
    except ValueError:
        return str(value)


_PARAMS_FMT = struct.Struct("<4B7IBI")


@dataclass
class RadioParams:
    """NL_CMD_RADIO_CONFIG payload (nl_radio_params_t, 37 bytes LE).

    ``mgmt_repeats`` (byte 32) is the number of transmissions per zone 0
    fragment; 0 means use ``tx_repeats``. ``cca_backoff_us`` (bytes 33..36)
    turns on listen before talk; 0 means transmit blindly."""
    origin_id: int = 0
    band: int = Band.SUBGHZ
    tx_policy: int = TxPolicy.IMMEDIATE
    tx_repeats: int = 3
    dwell_us: int = 2000
    burst_extend_us: int = 4000
    mgmt_hold_us: int = 250000
    repeat_interval_us: int = 1500
    tracker_stale_us: int = 500000
    repeat_jitter_us: int = 1000
    discovery_interval_us: int = 20000
    mgmt_repeats: int = 6
    cca_backoff_us: int = 2000

    WIRE_SIZE = 37

    @classmethod
    def default(cls):
        """nl_radio_params_default."""
        return cls()

    def encode(self):
        """nl_radio_params_encode. Like C it does not range-check the values
        the decoder rejects; it only refuses values that do not fit the field."""
        vals = []
        for i, f in enumerate(fields(self)):
            v = int(getattr(self, f.name))
            vals.append(check_uint(v, 32 if 4 <= i < 11 or i == 12 else 8, f.name))
        return _PARAMS_FMT.pack(*vals)

    @classmethod
    def decode(cls, buf):
        """nl_radio_params_decode: SIZE unless 37 bytes; ARG for origin >= 8,
        band > 2, tx_policy > 1 or tx_repeats == 0."""
        buf = bytes(buf)
        if len(buf) != cls.WIRE_SIZE:
            raise NLError("size", "radio params are %d bytes, expected %d" % (len(buf), cls.WIRE_SIZE))
        if buf[0] >= NUM_ORIGINS or buf[1] > Band.DUAL or buf[2] > TxPolicy.IN_SLOT or buf[3] == 0:
            raise NLError("arg", "radio params out of range")
        return cls(*_PARAMS_FMT.unpack(buf))

    def to_dict(self):
        d = {f.name: int(getattr(self, f.name)) for f in fields(self)}
        d["band_name"] = _enum_name(Band, self.band)
        d["tx_policy_name"] = _enum_name(TxPolicy, self.tx_policy)
        return d


@dataclass
class ZoneRF:
    priority: int = 0
    subghz_hz: int = 0
    ghz24_hz: int = 0


_ZONE_FMT = struct.Struct("<BII")


@dataclass
class ZonePlan:
    """NL_CMD_ZONE_CONFIG payload: 8 x [priority u8][subghz_hz u32][ghz24_hz u32]."""
    zones: List[ZoneRF] = field(default_factory=lambda: [ZoneRF() for _ in range(NUM_ZONES)])

    WIRE_SIZE = NUM_ZONES * 9

    def encode(self):
        if len(self.zones) != NUM_ZONES:
            raise NLError("arg", "a zone plan has exactly 8 zones")
        out = b""
        for i, z in enumerate(self.zones):
            out += _ZONE_FMT.pack(check_u8(z.priority, "zone %d priority" % i),
                                  check_uint(z.subghz_hz, 32, "subghz_hz"),
                                  check_uint(z.ghz24_hz, 32, "ghz24_hz"))
        return out

    @classmethod
    def decode(cls, buf):
        """nl_zone_plan_decode: SIZE unless exactly 72 bytes (priority is not
        validated, matching C)."""
        buf = bytes(buf)
        if len(buf) != cls.WIRE_SIZE:
            raise NLError("size", "zone plan is %d bytes, expected 72" % len(buf))
        return cls([ZoneRF(*_ZONE_FMT.unpack_from(buf, z * 9)) for z in range(NUM_ZONES)])

    def to_dict(self):
        return {"zones": [{"zone": i, "priority": z.priority, "subghz_hz": z.subghz_hz,
                           "ghz24_hz": z.ghz24_hz} for i, z in enumerate(self.zones)]}


STATUS_F_RX_PENDING = 0x01
STATUS_F_CONFIGURED = 0x02

_STATUS_FMT = struct.Struct("<4B6I")


@dataclass
class RadioStatus:
    """NL_RSP_STATUS payload (nl_radio_status_t, 28 bytes LE)."""
    proto_version: int = LINK_PROTOCOL_VERSION
    flags: int = 0
    rx_queue_len: int = 0
    tx_queue_len: int = 0
    rx_ok: int = 0
    rx_dup: int = 0
    rx_dropped: int = 0
    rx_ignored: int = 0
    tx_sent: int = 0
    tx_dropped: int = 0

    WIRE_SIZE = 28

    def encode(self):
        vals = [check_uint(int(getattr(self, f.name)), 8 if i < 4 else 32, f.name)
                for i, f in enumerate(fields(self))]
        return _STATUS_FMT.pack(*vals)

    @classmethod
    def decode(cls, buf):
        buf = bytes(buf)
        if len(buf) != cls.WIRE_SIZE:
            raise NLError("size", "status is %d bytes, expected 28" % len(buf))
        return cls(*_STATUS_FMT.unpack(buf))

    def to_dict(self):
        d = {f.name: getattr(self, f.name) for f in fields(self)}
        names = []
        if self.flags & STATUS_F_RX_PENDING:
            names.append("RX_PENDING")
        if self.flags & STATUS_F_CONFIGURED:
            names.append("CONFIGURED")
        d["flag_names"] = names
        return d


@dataclass
class Pong:
    """NL_RSP_PONG payload: protocol version and firmware version."""
    proto_version: int = LINK_PROTOCOL_VERSION
    fw_major: int = VERSION_MAJOR
    fw_minor: int = VERSION_MINOR
    fw_patch: int = VERSION_PATCH

    WIRE_SIZE = 4

    def encode(self):
        return bytes(check_u8(getattr(self, f.name), f.name) for f in fields(self))

    @classmethod
    def decode(cls, buf):
        buf = bytes(buf)
        if len(buf) != cls.WIRE_SIZE:
            raise NLError("size", "pong is %d bytes, expected 4" % len(buf))
        return cls(*buf)

    def to_dict(self):
        return {f.name: getattr(self, f.name) for f in fields(self)}
