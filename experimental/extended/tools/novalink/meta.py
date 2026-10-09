"""Zone 0 metadata records (mirrors src/nl_meta.c and the builders in src/nl_host.c).

A zone 0 fragment payload is a sequence of TLV records::

    [type u8][len u8][value: len bytes] ...

A record never spans fragments, so a value is at most 98 bytes.
"""

import struct
from dataclasses import dataclass
from enum import IntEnum

from .common import (LINK_PROTOCOL_VERSION, MAX_PAYLOAD, VERSION_MAJOR, VERSION_MINOR,
                     VERSION_PATCH, NLError, check_u8, check_uint)

TLV_OVERHEAD = 2
MAX_VALUE = MAX_PAYLOAD - TLV_OVERHEAD          # 98
QUEUE_BYTES = 512                                 # NL_META_QUEUE_BYTES default
CLAIM_WIRE_SIZE = 4
MAX_CLAIMS = MAX_VALUE // CLAIM_WIRE_SIZE         # 24, NL_HOST_MAX_ANNOUNCED_CLAIMS
DEVICE_NAME_MAX = 24
PLUGIN_DATA_MAX = MAX_VALUE - 2                   # 96, nl_host_meta_send_plugin


class MetaType(IntEnum):
    DEVICE_ANNOUNCE = 0x01
    CLAIM_ANNOUNCE = 0x02
    PLUGIN_DATA = 0x03
    CONGESTION = 0x04
    DEBUG_TEXT = 0x05
    PEERS = 0x06
    VENDOR_BASE = 0x80


class ClaimMode(IntEnum):
    NONE = 0
    SHARED = 1
    EXCLUSIVE = 2
    READ_ONLY = 3


def type_name(t):
    try:
        return MetaType(t).name
    except ValueError:
        return "VENDOR_0x%02X" % t if t >= MetaType.VENDOR_BASE else "UNKNOWN_0x%02X" % t


def claim_mode_name(mode):
    """nl_claim_mode_str."""
    return {0: "none", 1: "shared", 2: "exclusive", 3: "read-only"}.get(mode, "invalid")


# ---- TLV --------------------------------------------------------------------

@dataclass(frozen=True)
class MetaRecord:
    type: int
    value: bytes

    def encode(self):
        return encode_record(self.type, self.value)


def iter_records(payload):
    """Yield MetaRecord objects like nl_meta_iter_next; raise NLError("proto")
    when the remaining bytes are truncated (records before it are yielded)."""
    payload = bytes(payload)
    pos, n = 0, len(payload)
    while pos < n:
        if pos + TLV_OVERHEAD > n or pos + TLV_OVERHEAD + payload[pos + 1] > n:
            raise NLError("proto", "truncated TLV record at offset %d" % pos)
        vlen = payload[pos + 1]
        yield MetaRecord(payload[pos], payload[pos + 2:pos + 2 + vlen])
        pos += TLV_OVERHEAD + vlen


def decode_records(payload):
    """Return ``(records, status)`` where status is "ok" or "proto"."""
    out = []
    try:
        for rec in iter_records(payload):
            out.append(rec)
    except NLError as e:
        return out, e.status
    return out, "ok"


def encode_record(rtype, value=b""):
    value = bytes(value)
    check_u8(rtype, "record type")
    if len(value) > MAX_VALUE:
        raise NLError("size", "record value is %d bytes, max %d" % (len(value), MAX_VALUE))
    return bytes((rtype, len(value))) + value


def encode_records(records):
    """Concatenate records; SIZE if the result does not fit one payload."""
    out = b"".join(encode_record(r.type, r.value) for r in records)
    if len(out) > MAX_PAYLOAD:
        raise NLError("size", "records need %d bytes, payload max %d" % (len(out), MAX_PAYLOAD))
    return out


# ---- Structured records -----------------------------------------------------

@dataclass(frozen=True)
class DeviceAnnounce:
    """NL_META_DEVICE_ANNOUNCE: [proto][major][minor][patch][name 0..24 bytes].

    ``name_bytes`` is the raw wire name. C copies it verbatim and
    NUL-terminates, so C code sees it only up to the first NUL; ``name`` is
    that view decoded as UTF-8 (with replacement characters).
    """
    proto_version: int = LINK_PROTOCOL_VERSION
    fw_major: int = VERSION_MAJOR
    fw_minor: int = VERSION_MINOR
    fw_patch: int = VERSION_PATCH
    name_bytes: bytes = b""

    @property
    def c_name(self):
        return self.name_bytes.split(b"\0", 1)[0]

    @property
    def name(self):
        return self.c_name.decode("utf-8", "replace")

    def encode(self):
        return encode_device(self.proto_version, self.fw_major, self.fw_minor,
                             self.fw_patch, self.name_bytes)

    @classmethod
    def decode(cls, value):
        return decode_device(value)

    def to_dict(self):
        return {"proto_version": self.proto_version, "fw_major": self.fw_major,
                "fw_minor": self.fw_minor, "fw_patch": self.fw_patch,
                "name": self.name, "name_bytes": self.name_bytes.hex()}


def encode_device(proto_version, fw_major, fw_minor, fw_patch, name):
    """nl_meta_encode_device: the name is cut at the first NUL and at 24 bytes
    (the C struct holds 24 chars + NUL). ``name`` may be str (UTF-8) or bytes."""
    if isinstance(name, str):
        name = name.encode("utf-8")
    name = bytes(name).split(b"\0", 1)[0][:DEVICE_NAME_MAX]
    head = bytes(check_u8(v, "version") for v in (proto_version, fw_major, fw_minor, fw_patch))
    return head + name


def decode_device(value):
    """nl_meta_decode_device: PROTO if shorter than 4 or the name exceeds 24."""
    value = bytes(value)
    if len(value) < 4 or len(value) - 4 > DEVICE_NAME_MAX:
        raise NLError("proto", "device record is %d bytes, expected 4..28" % len(value))
    return DeviceAnnounce(value[0], value[1], value[2], value[3], value[4:])


@dataclass(frozen=True)
class Claim:
    zone: int
    mode: int
    plugin_type: int

    def to_dict(self):
        return {"zone": self.zone, "mode": self.mode, "mode_name": claim_mode_name(self.mode),
                "plugin_type": self.plugin_type}


def encode_claims(claims, cap=MAX_VALUE):
    """nl_meta_encode_claims: SIZE if 4*count exceeds cap or 98."""
    claims = list(claims)
    need = len(claims) * CLAIM_WIRE_SIZE
    if need > cap or need > MAX_VALUE:
        raise NLError("size", "%d claims need %d bytes, max %d" % (len(claims), need, min(cap, MAX_VALUE)))
    out = b""
    for c in claims:
        out += struct.pack("<BBH", check_u8(c.zone, "zone"), check_u8(c.mode, "mode"),
                           check_uint(c.plugin_type, 16, "plugin_type"))
    return out


def decode_claims(value, max_count=MAX_CLAIMS):
    """nl_meta_decode_claims: PROTO if len % 4, SIZE if more than max_count."""
    value = bytes(value)
    if len(value) % CLAIM_WIRE_SIZE:
        raise NLError("proto", "claim record length %d is not a multiple of 4" % len(value))
    count = len(value) // CLAIM_WIRE_SIZE
    if count > max_count:
        raise NLError("size", "%d claims, max %d" % (count, max_count))
    return [Claim(*struct.unpack_from("<BBH", value, i * 4)) for i in range(count)]


def encode_plugin_data(plugin_type, data=b""):
    """Value of NL_META_PLUGIN_DATA as built by nl_host_meta_send_plugin."""
    data = bytes(data)
    if len(data) > PLUGIN_DATA_MAX:
        raise NLError("size", "plugin data is %d bytes, max %d" % (len(data), PLUGIN_DATA_MAX))
    return struct.pack("<H", check_uint(plugin_type, 16, "plugin_type")) + data


def decode_plugin_data(value):
    """Receiver side (nl_host.c): needs at least the 2-byte plugin type."""
    value = bytes(value)
    if len(value) < 2:
        raise NLError("proto", "plugin data record shorter than 2 bytes")
    return struct.unpack_from("<H", value)[0], value[2:]


def encode_congestion(zone_mask, dropped):
    """NL_META_CONGESTION value; ``dropped`` is clamped to 0xFFFF like nl_host.c."""
    return struct.pack("<BH", check_u8(zone_mask, "zone_mask"), min(int(dropped), 0xFFFF))


def decode_congestion(value):
    """Receiver side: needs at least 3 bytes; extra bytes are ignored."""
    value = bytes(value)
    if len(value) < 3:
        raise NLError("proto", "congestion record shorter than 3 bytes")
    return struct.unpack_from("<BH", value)


def decode_peers(value):
    """NL_META_PEERS: origins the sender knows. Extra bytes are ignored."""
    value = bytes(value)
    if len(value) < 1:
        raise NLError("proto", "peers record is empty")
    return [o for o in range(8) if value[0] >> o & 1]


def encode_debug_text(text):
    """nl_host_meta_debug: raw bytes truncated to 98 (may split a UTF-8 char)."""
    if isinstance(text, str):
        text = text.encode("utf-8")
    return bytes(text)[:MAX_VALUE]


def describe_record(rec):
    """Decode a record into a JSON-friendly dict (unknown types stay raw)."""
    d = {"type": rec.type, "type_name": type_name(rec.type), "len": len(rec.value),
         "value": rec.value.hex()}
    try:
        if rec.type == MetaType.DEVICE_ANNOUNCE:
            d["device"] = decode_device(rec.value).to_dict()
        elif rec.type == MetaType.CLAIM_ANNOUNCE:
            d["claims"] = [c.to_dict() for c in decode_claims(rec.value)]
        elif rec.type == MetaType.PLUGIN_DATA:
            ptype, data = decode_plugin_data(rec.value)
            d["plugin_data"] = {"plugin_type": ptype, "data": data.hex()}
        elif rec.type == MetaType.CONGESTION:
            mask, dropped = decode_congestion(rec.value)
            d["congestion"] = {"zone_mask": mask,
                               "zones": [z for z in range(8) if mask >> z & 1],
                               "dropped": dropped}
        elif rec.type == MetaType.DEBUG_TEXT:
            d["text"] = rec.value.decode("utf-8", "replace")
        elif rec.type == MetaType.PEERS:
            d["peers"] = decode_peers(rec.value)
    except NLError as e:
        d["error"] = e.status
    return d


# ---- Outgoing queue ---------------------------------------------------------

class MetaQueue:
    """nl_meta_queue_t: a FIFO of whole TLV records in a fixed byte buffer."""

    def __init__(self, size=QUEUE_BYTES):
        self.size = size
        self.buf = bytearray()
        self.dropped = 0

    @property
    def used(self):
        return len(self.buf)

    @property
    def pending(self):
        return bool(self.buf)

    def push(self, rtype, value=b""):
        """nl_meta_queue_push: SIZE if the value exceeds 98, FULL (and
        dropped += 1) if the record does not fit."""
        value = bytes(value)
        check_u8(rtype, "record type")
        if len(value) > MAX_VALUE:
            raise NLError("size", "record value is %d bytes, max %d" % (len(value), MAX_VALUE))
        if self.used + TLV_OVERHEAD + len(value) > self.size:
            self.dropped += 1
            raise NLError("full", "metadata queue full")
        self.buf += bytes((rtype, len(value))) + value

    def remove_type(self, rtype):
        """nl_meta_queue_remove_type."""
        kept = bytearray()
        rd = 0
        while rd < len(self.buf):
            rec = TLV_OVERHEAD + self.buf[rd + 1]
            if self.buf[rd] != rtype:
                kept += self.buf[rd:rd + rec]
            rd += rec
        self.buf = kept

    def pack(self, cap=MAX_PAYLOAD):
        """nl_meta_queue_pack: take whole records FIFO while they fit in cap.
        Stops at the first record that does not fit (even if it is the head)."""
        taken = 0
        while taken < len(self.buf):
            rec = TLV_OVERHEAD + self.buf[taken + 1]
            if taken + rec > cap:
                break
            taken += rec
        out = bytes(self.buf[:taken])
        del self.buf[:taken]
        return out
