"""Optional segmentation of messages larger than one fragment (mirrors src/nl_segment.c).

Each segment payload starts with a sub-header byte ``index<<4 | (count-1)``
followed by up to 99 data bytes; every segment except the last carries
exactly 99. Segments of one message use consecutive seqNums, so
``seq - index`` identifies the message.
"""

from .common import MAX_PAYLOAD, NLError

DATA_MAX = MAX_PAYLOAD - 1           # 99
MAX_SEGMENTS = 16                    # NL_SEG_MAX_SEGMENTS default
MAX_MESSAGE = DATA_MAX * MAX_SEGMENTS  # 1584


def seg_count(msg_len):
    """nl_seg_count: 1 for an empty message, SIZE above 1584 bytes."""
    if msg_len > MAX_MESSAGE:
        raise NLError("size", "message is %d bytes, max %d" % (msg_len, MAX_MESSAGE))
    if msg_len == 0:
        return 1
    return (msg_len + DATA_MAX - 1) // DATA_MAX


def build_segment(msg, index, cap=MAX_PAYLOAD):
    """nl_seg_build: payload of segment ``index`` (ARG if index >= count,
    SIZE if it does not fit ``cap``)."""
    msg = bytes(msg)
    count = seg_count(len(msg))
    if not 0 <= index < count:
        raise NLError("arg", "segment index %d out of range 0..%d" % (index, count - 1))
    off = index * DATA_MAX
    chunk = msg[off:off + DATA_MAX]
    if cap < len(chunk) + 1:
        raise NLError("size", "segment needs %d bytes, cap %d" % (len(chunk) + 1, cap))
    return bytes(((index << 4) | (count - 1),)) + chunk


def build_segments(msg):
    """All segment payloads of ``msg`` in order."""
    return [build_segment(msg, i) for i in range(seg_count(len(msg)))]


def parse_segment_header(payload):
    """Return ``(index, count, data)`` without validating the data length."""
    if not payload:
        raise NLError("proto", "empty segment payload")
    return payload[0] >> 4, (payload[0] & 0x0F) + 1, bytes(payload[1:])


def segment_problem(payload):
    """Return None if ``payload`` passes nl_reasm_feed's format checks, else a
    short reason string."""
    if len(payload) < 1 or len(payload) > MAX_PAYLOAD:
        return "length %d outside 1..%d" % (len(payload), MAX_PAYLOAD)
    index, last = payload[0] >> 4, payload[0] & 0x0F
    count, chunk = last + 1, len(payload) - 1
    if index > last:
        return "index %d > last %d" % (index, last)
    if count > MAX_SEGMENTS:
        return "count %d > %d" % (count, MAX_SEGMENTS)
    if index < last and chunk != DATA_MAX:
        return "non-final segment carries %d bytes, expected %d" % (chunk, DATA_MAX)
    if index == last and count > 1 and chunk == 0:
        return "empty final segment"
    return None


class Reassembler:
    """nl_reasm_t / nl_reasm_feed. ``cap`` is the caller's buffer size."""

    def __init__(self, cap=MAX_MESSAGE):
        self.cap = cap
        self.buf = bytearray(cap)
        self.active = False
        self.base_seq = 0
        self.count = 0
        self.mask = 0
        self.total_len = 0
        self.completed = 0
        self.aborted = 0

    def feed(self, seq, payload):
        """Feed one segment payload (after deduplication).

        Returns the message bytes when it completes, None if more segments are
        needed. Raises NLError("proto") for a malformed segment and
        NLError("size") when the message does not fit ``cap``.
        """
        payload = bytes(payload)
        problem = segment_problem(payload)
        if problem:
            raise NLError("proto", problem)
        index, last = payload[0] >> 4, payload[0] & 0x0F
        count, chunk = last + 1, len(payload) - 1

        base = (seq - index) & 0xFF
        if not self.active or base != self.base_seq or count != self.count:
            if self.active:
                self.aborted += 1
            self.active = True
            self.base_seq = base
            self.count = count
            self.mask = 0
            self.total_len = 0

        off = index * DATA_MAX
        if off + chunk > self.cap:
            self.active = False
            self.aborted += 1
            raise NLError("size", "segment %d does not fit a %d-byte buffer" % (index, self.cap))
        self.buf[off:off + chunk] = payload[1:]
        self.mask |= 1 << index
        if index == last:
            self.total_len = off + chunk
        if self.mask == (1 << count) - 1:
            self.active = False
            self.completed += 1
            return bytes(self.buf[:self.total_len])
        return None
