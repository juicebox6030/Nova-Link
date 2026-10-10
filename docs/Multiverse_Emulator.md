# Multiverse software emulator and adapter contract

The emulator now exercises DMX transmit and receive entirely offline, including
packet bytes, integrity checks, chunking, full/delta reconstruction, loss and
recovery. It is a portable software foundation for a future Multiverse adapter.
It does **not** encode or decode City Theatrical's proprietary RF format. There
are no real captures, radio drivers, measured PHY settings, or fixture results.

## Run it

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build --parallel
ctest --test-dir build --output-on-failure
./build/nova-multiverse-sim --seed 42 --loss-percent 20 \
  --capture build/multiverse.synthetic.jsonl
python3 tools/replay_multiverse.py build/multiverse.synthetic.jsonl \
  --end-us 3130200 --summary-only
python3 tools/replay_multiverse.py build/multiverse.synthetic.jsonl \
  --output build/multiverse.decoded.jsonl
```

The simulator submits 301 host states of 512 channels, splitting full states
into six chunks of at most 96 levels. It uses a seeded loss model, reverses
chunk order, duplicates selected observations, corrupts selected packet CRCs,
marks some observations' integrity unknown, and rejects some local submissions
before retrying. It forces a final clean full update and checks all delivered
frames against their exact host snapshot. It then advances time and verifies
link loss. The JSON summary includes actual counters. Try loss percentages
0, 20, 75, and 100 to distinguish sustained delivery from recovery after outage.
Even at 100%, the initial and final reference full updates are delivered; the
loss setting applies to the intervening updates.

A small versioned example covers reordered chunks, duplicates, a missing delta
base, full resync, corrupt/unknown integrity, session filtering, and silence:

```sh
python3 tools/replay_multiverse.py examples/multiverse.synthetic.jsonl \
  --end-us 104000 --summary-only
```

It reconstructs four exact frames from eleven observations, then reports `lost`.

All time is logical. The host polls at 10,100 us intervals; the model refresh
interval is 10,000 us, full-update interval 50,000 us, assembly timeout 5,000 us,
and loss timeout 100,000 us. These are **test assumptions**, not Multiverse
settings, packet rates, or a latency guarantee. The fixed logged frequency is
illustrative; the simulator does not pretend to establish hopping rendezvous.

Replay runs the **same C receive engine**, checks reconstructed frames against
`expected_slots_hex` when present, and reports every result plus a final summary.
`--end-us` advances the clock through silence, so captures ending without a
packet can still test loss. Configure `--universe`, `--session`, `--loss-us`,
and `--assembly-us` to explore filtering and reconstruction boundaries. Use
`--engine <path>` for a different build. Mismatched expected levels or malformed
logs exit 2. A log must have `profile="nova-mv-synthetic-v1"` and
`synthetic=true` on every observation; real candidate-PHY logs are refused.
The wrapper buffers a capture in memory and is intended for finite bench/test
runs, not unbounded live logging. Its C bridge reads normalized text from stdin,
prints JSONL, and never opens a network connection or device.

## Implemented behavior

| TX | RX |
| --- | --- |
| Caller-owned latest DMX snapshot with coalescing | Explicit universe and session binding |
| Frozen snapshot throughout a chunked update | Only verified integrity is accepted |
| First/periodic/forced full updates | Full-state acquisition before deltas |
| Contiguous changed-span deltas and empty-span refresh | Per-update coverage with reordered/overlapping chunks |
| Configurable levels per chunk | Atomic commit; partial state never reaches the host |
| Local prepare/complete tokens; stale completions rejected | Duplicate/stale rejection across 16-bit wrap |
| Failed completion retries identical bytes with a new token | Inconsistent headers/overlap rejected before mutation |
| Sequence/base advances only after all chunks finish | Missing delta base requires full resynchronization |
| Changed slot counts force full state and clear unused slots | Hold last complete frame until loss timeout, then explicit lost status |
| Optional full request during an in-flight update | Bounded assembly deadline that duplicates cannot extend |
| Monotonic clock checks and token exhaustion | Session restart via explicit bind; expired duplicates cannot revive a link |

TX completion represents **local adapter/RF completion**, not peer reception or
an acknowledgment. Losing a chunk can therefore invalidate later delta bases.
RX holds the last good frame while recovering; periodic full updates restore
state without relying on a feedback channel. The model defines no peer ACK,
join handshake, control traffic, or automatic SHoW Key behavior. A future
verified adapter may implement those independently and request a full update.

An application can get held levels with `nova_mv_rx_get()` and inspect
`rx.link`: `wait_full`, `live`, `recovering`, or `lost`. `get()` never returns a
partial or expired frame. The host owns its loss policy: hold, blackout, or
other behavior must be chosen explicitly outside this library. Sequence history
survives loss. Ordering is unambiguous only within the 16-bit half-range; a
sender restart or larger sequence jump requires explicit session binding.
The model's sequence/session widths are local choices, not RF field discoveries.

## Integrate a future verified backend

`include/nova/multiverse.h` provides the installed target
`NovaLink::nova_multiverse`, which links the independent DMX library. No heap,
threads, callbacks, files, socket access, or board SDK is used. One instance
models one universe/session; instantiate independently for multiple streams.
The ESP-IDF component includes the portable engine and DMX core, but its vendor
build is still unverified. Tests and synthetic tools remain separate from the
installed engine. Neither this library nor its normalized packets share native
NOVA-LINK zones, DataFragments, or SPI framing.

A TX application follows this ownership sequence:

1. Initialize `nova_mv_tx_t` and submit `nova_dmx_frame_t` host levels.
2. Call `nova_mv_tx_prepare(now, &packet, &token)` when polling the adapter.
3. Have the verified encoder translate normalized levels into actual RF packets
   and control exchanges. Do not reinterpret the C struct as on-air bytes.
4. Complete the token once the adapter has finished all work corresponding to
   that normalized chunk. Report failure on local submission/completion failure.
   Repeated prepare calls while in flight return the same immutable packet/token.
5. Submit newer host levels at any time; they apply to the next update. Request
   a full update after reconnect or an independent verified recovery exchange.

On RX, copy RF observations promptly into an adapter-owned queue, validate the
**established** RF integrity scheme, resolve settings/control/session information,
and decode into normalized chunks. Call `nova_mv_rx_receive()` with the capture
timestamp; dispatch only `FRAME_READY` levels. Unknown candidate-PHY CRCs do not
count as established integrity. Poll `nova_mv_rx_tick()` even when no packet
arrives. Bind explicitly when discovery confirms a transmitter/session restart.
Adapter queue overflows, tuning gaps and dropped UART logs belong in diagnostics;
they cannot be silently inferred from missing receive events.

The normalized model uses full states or one contiguous delta span. A decoder
for an actual format with sparse updates, FEC groups, compressed states, or
independent universe counters may first reconstruct those in adapter-owned
storage, then supply a FULL or equivalent normalized span. Synthetic chunking
is not evidence that the real RF format uses these headers or boundaries.
An encoder may need additional buffering/control before completing a token.
That work cannot be specified correctly until the real format is established.

All calls on an instance must be serialized. Times are extended uint64
microseconds; adapters extend hardware timer wraps before calling the engine.
The application must initialize state, keep output/input storage independent
of engine storage, and treat bookkeeping as private. Reinitialization abandons
any in-flight token; cancel/drain the external adapter first. Tokens are valid
for one TX instance lifetime; reinitialize only once old callbacks are drained.

## Native host plugin integration

`NovaLink::nova_multiverse_plugin` installs `nova_link/multiverse_plugin.h` and
the actual compiled plugin. `nl_multiverse_init()` selects TX or RX, a data zone,
universe, explicit session and role-specific timing. TX uses an exclusive claim;
RX uses a read-only claim and pins the peer origin. `nl_multiverse_module()`
returns the common module descriptor, requiring the `radio-link` transport.
Register its manifest with `nl_modules_start()` and call `nl_host_poll()` from
the serialized event loop. The same lifecycle also manages logging and other
applications. See the [plugin guide](../plugins/README.md).

```sh
./build/nova-plugin-sim
ctest --test-dir build --output-on-failure \
  -R 'multiverse_plugin|radio_plugin|logger_plugin|modules|plugin_simulation'
```

The combined simulation sends 301 exact 512-channel snapshots alongside 301
counter messages, using four plugins on each host. It exercises encoded native
PUSH/PULL transport, bounded radio queues, scheduled native fragment delivery,
duplicate suppression, loss and payload corruption. The final clean FULL
recovers exact levels, then silence expires the link. All time and RF delivery
are simulated; multiple queued fragments are handed off within one logical
window without claiming an airtime budget or measured rate.

Submit levels with `nl_multiverse_submit()`. Each tick accepts at most the
configured 1..8 chunks, stopping at the first transport rejection. Each payload
has at most 72 levels: full 512-slot state needs eight native fragments. During
queue pressure, the frozen update stays immutable and newer host states coalesce
for the next update. Here engine completion means **native queue acceptance**;
downstream driver failures and packet loss require a periodic/forced FULL.
The direct verified-RF adapter contract above uses its own completion boundary.

Read levels with `nl_multiverse_get()` and check `NOVA_MV_FRAME_READY`; inspect
`rx.stats.frames` for newly committed frames and `rx.link` for holdover/loss.
It never exposes incomplete or expired levels or fabricates blackout. Tick through
silence. Invalid payloads, flags and peer origins have separate plugin counters;
the RX engine counts wrong universe/session, missing base and sequence rejection.
Each instance owns one universe; separate zones/contexts support several streams.

NLM1 is explicitly a **native application codec**, distinct from the NVS1 test
codec and City Theatrical RF. Its header documents fixed little-endian metadata,
length-derived chunk count, reserved-byte/version checks and CRC-32/ISO-HDLC.
The CRC detects corrupted payloads; it does not authenticate a sender. Native
radio/host deduplication accepts fragments in native sequence order, so native
reordering can drop an earlier chunk even though the normalized engine can
reassemble reordered chunks. Use FIFO RX queues; latest-per-stream coalescing
destroys fragment groups. A native sequence gap of at least 128 requires the
existing explicit/idle-reset policy, independently of model full refresh.

For a confirmed restart, drain old native queues and separately reset host/radio
origin tracking when the native sequence restarts, then call
`nl_multiverse_bind()` for the model peer/session. Binding never resets shared
native trackers implicitly. Unregister invalidates plugin access; reinitialize
a stopped Multiverse context before a new registration, with a new TX session
and old transport ownership drained. No external hardware completion callbacks
belong to this native tunnel. A future verified RF plugin can wrap the independent
engine and use the same module lifecycle without adopting NLM1 bytes.

## Synthetic codec

`include/nova/multiverse_synthetic.h` and `src/multiverse_synthetic.c` implement
an intentionally separate test codec. It is built for tools/tests and excluded
from SDK installation. It uses magic `NVS1`, explicit little-endian fields,
strict length/semantic validation, and CRC-32/ISO-HDLC. Its maximum packet is
542 bytes, which is **not** a CC1352R payload-budget claim. The header documents
the exact layout. Independent Python `struct`/`zlib` vectors check the C codec.
Changing synthetic bytes requires no gateway or radio settings.

## Capture work ready for real observations

Existing real/candidate-PHY logs can already be validated and summarized. The
analyzer can also compare candidate byte distributions between two labeled
stimuli while keeping profile, frequency, length, and CRC status separate:

```sh
python3 tools/analyze_rf_capture.py capture.jsonl \
  --compare-stimuli baseline channel_1_32 --output build/comparison.json
```

It reports byte offsets whose distributions differ, their observed value
counts, and whether both inputs were stable at each offset. Unequal sample
counts alone do not mark identical distributions as different. This is a
forensic aid, not a DMX decoder: counters, keys, FEC, integrity bytes and other
traffic can change independently of the stimulus. No hop sequence, channel
mapping, modulation, or key is inferred. Preserve raw observations and the
exact SmartRF profile/settings alongside run notes.

## Remaining evidence boundary

Further real Multiverse progress needs the board/transmitter identities,
reproducible captures with controlled DMX inputs, actual PHY/framing/integrity
and hopping characterization, startup/join/reacquisition exchanges, mDMX/FEC
and SHoW Key handling, and independent fixture-output checks. CC1352R firmware
and vendor SDK builds need the exact board/configuration. RDM is a separate
implementation and validation effort. These cannot be established by a
synthetic loopback or by successfully submitting an RF command.

The emulator provides tested host state and adapter ownership machinery to
plug those discoveries into. It does not establish real TX/RX compatibility.
See the [bench plan](Multiverse_2_4GHz.md) for physical acceptance steps.
