# Protocol decisions for the portable implementation

The original design notes contain incompatible descriptions. These decisions
make the offline SDK reproducible while preserving the unresolved board work.
They describe the current software ABI and can be revised before hardware
interoperability is established.

| Topic | Implemented decision | Reason / limit |
|---|---|---|
| Header allocation | Origin bits 7–5, zone bits 4–2, BURST bit 1, MGMT_LISTEN bit 0 | Uses the detailed `packet_format.adoc`; the earlier README's 2/3/3 split was inconsistent |
| Fragment size | 2-byte header/sequence plus 0–100 bytes of payload | Maximum is **102**, not “under 102”; serialize fields explicitly |
| Transport envelope | `AA LEN COMMAND DATA`; LEN includes command | Combines the original SYNC/LEN concept with the command list; maximum LEN 103, frame 105 |
| Empty request | `AA 01 COMMAND` | PING, PULL, STATUS carry no request payload |
| Direction | PUSH `03` carries host→radio fragment; response type `D0` carries radio→host fragment | Host rejects PUSH/PULL/request frames as incoming payloads |
| PING/STATUS responses | Unsupported | Their response type/fields are absent from the specification; no response ABI is invented |
| Empty PULL / PUSH acknowledgment | C API status only | No byte-level empty/error/ack encoding is specified; a board adapter needs that decision |
| Zone ownership | Exclusive owner may read/write; shared read-only claims may only read | A new exclusive claim conflicts with any other reader; owners may downgrade explicitly |
| Zone 0 | Shared read/write for active plugins, never claimable | Scheduled after a data round when TX is queued or listening is requested |
| Fragmentation | Application-owned; oversized core payload rejected | No message ID, fragment index, count, or reassembly timeout exists in the RF format |
| Scheduling | Ascending active-zone rounds, then one requested metadata slot | Provisional deterministic policy; priorities/frequencies are not defined yet |
| BURST | TX announces a bounded extension; RX holds the current matching slot once | Extension is relative to the original slot start, never the arrival time; missed announcements still need shared timing recovery |
| MGMT_LISTEN | Requests a metadata slot after a data round | Zone number still determines payload routing; a flagged data fragment is not routed to zone 0 |
| PHY | Abstract adapter boundary | Earlier notes mention both 802.15.4 and proprietary EasyLink; portable code selects neither |

## Golden vector

Origin 5, zone 3, both flags set, sequence 254, payload `00 AA FF`:

```text
fragment: AF FE 00 AA FF
PUSH:     AA 06 03 AF FE 00 AA FF
PULL:     AA 01 02
response: AA 06 D0 AF FE 00 AA FF
```

`AA` in the sequence or payload is ordinary data once a valid length is known.
The incremental parser does not split a frame at those bytes.

## Sequence comparison and sessions

Each of the 64 `(origin, zone)` streams has an independent last sequence. The
first valid arrival is accepted. Thereafter, subtract the last sequence modulo
256: 0 is a duplicate, 1–127 advances the stream, and 128–255 is stale. Exactly
half a sequence space is ambiguous and is rejected. Sequence numbers advance
only after the outgoing transport accepts the fragment. A full RX queue does
not commit the incoming sequence, so a retransmission can be accepted later.

This is suitable for latest-value messages. It does not guarantee delivery of
every fragment, ordered reassembly, retransmission, or acknowledgment. Valid
queued updates are delivered in accepted FIFO order by default. Optional
`NL_RX_LATEST_PER_STREAM` replaces an already queued value of the same stream;
use it only for self-contained state, never application fragment groups. If 128
or more sequence values are skipped, or a packet
is delayed across a complete 256-packet wrap, the header alone cannot establish
its age. Retransmissions must reuse their original sequence number.

Call `nl_stream_reset_origin()` on both host and radio trackers after an
application-established sender session restart. An optional idle timeout accepts
the next packet after inactivity, but can also accept an old delayed packet.
Zero disables automatic expiration. Duplicate/stale arrivals do not refresh the
last accepted time. An epoch/session ID would need a future wire-format change
to remove these ambiguities. The application must ensure origin IDs are unique;
there are only eight available.

## Integrity and stream recovery

Neither the RF fragment nor this transport envelope adds a checksum. Length and
command validation detect some malformed input, but they cannot detect arbitrary
payload corruption. Deduplication does not provide integrity. A future PHY
adapter must establish its CRC/error-reporting behavior before deployment.

The parser skips noise before SYNC and rejects invalid lengths/commands. A
plausible corrupted length can consume bytes from the next frame; it cannot
reliably find the intended boundary without stronger framing or a checksum.
Adapters must reset partial parsing at transaction boundaries or a configured
timeout. SPI clocking, chip-select transactions, dummy bytes, empty responses,
and hardware acknowledgment remain adapter/protocol decisions.

## Timing and deployment limits

The scheduler uses injected monotonic microseconds. It creates one due window
per call, starts late windows at the current time, and never emits a catch-up
burst. Durations and deadlines are checked for integer overflow. The caller owns
PHY pacing, per-slot airtime limits, radio completion/retry handling, and shared
timing with other devices. Independently initialized schedulers are not a
wireless synchronization protocol.

Before every PHY submission, `nl_radio_prepare_tx()` peeks the current head and
applies a current sender hold for BURST, including late arrivals and second
fragments in one slot. Peeking/popping alone does not apply this control. The
first announcement must be processed by receivers before their original slot closes;
the adapter must preflight that constraint before preparation, using the base
deadline even if the sender's selected window is extended. Received holds apply only while a
matching current window is open and are never saved for a future slot.
Fresh frames rejected for queue capacity still carry timing control, but stale
frames do not. Congestion spanning 128 sequence values can prevent both data and
holds until sequence/session recovery; it is the same skip ambiguity as above.

PULL preparation returns a response and an adapter-local uint64 revision token,
leaving the RX head queued until `nl_radio_commit_pull()` validates both. A new
head or coalesced value invalidates earlier tokens even if serialized bytes match.
An adapter can retry an aborted handoff without consuming another fragment. The
token never goes on the wire and is valid only for one radio initialization
lifetime. Exhaustion returns `NL_ERR_SIZE` without wrapping. This provides C-side
ownership, not a wire acknowledgment. A physical PUSH that only reports bytes
clocked out cannot prove radio queue acceptance.

The shared RX FIFO may drop new updates when full and allows one busy stream to
consume all slots. Optional per-stream coalescing keeps the newest queued state
of each represented stream, but there is no per-zone RX reservation; sixteen
distinct streams can still block others. Callers must provide a retry/refresh
policy. Sender
restarts without a tracker reset can suppress up to 129 initial sequence values.
The header is unauthenticated, so origin spoofing and sequence jumps can suppress
legitimate streams. The host rejects self-origin frames with `NL_ERR_CONFLICT`;
unique origin assignment and radio-side loop prevention remain application
responsibilities. Plugin handles include a slot generation to reject retired
handles; they are local bookkeeping, not wire identities or security credentials.

Queue capacity and logical slot duration do not imply achievable RF throughput.
The in-memory two-copy path models deduplication, not two simultaneous physical
radios or validated dual-band behavior.

`tools/rf_feasibility.py` checks airtime and an idealized delivery bound from
explicit inputs. A bound is `null` when the assumed transmission misses the base
window/first-announcement deadline or a specified continuous stream leaves no
schedule service headroom. The one-fragment model cannot use BURST to fit the
announcement itself; its extension only lengthens the round.
Receiver radio processing delay and clock rounding must be included in the
per-copy fixed margin; host/transport delay does not extend the hold deadline.
Passing the fit check does not establish receiver rendezvous, channel
access, RF reliability, or regulatory compliance. See [validation](Validation.md).
