# Software development guide

Start with the build and test commands in the [README](../README.md). Public API
headers are under `include/nova_link/`; include `nova_link/nova_link.h` for the
whole API or individual headers for smaller integrations.

## State and execution

Allocate `nl_host` and `nl_radio` in stable storage, initialize them once, and
serialize calls through an application event loop. A radio contains queues that
point into its own arrays: **do not copy or move an initialized radio**. A generic
queue similarly requires its caller-owned storage to remain valid. Plugin context
and transport/logger context must outlive their registration.

The library uses no heap, OS services, filesystem, socket, clock, or device I/O.
`memcpy` and `memset` come from the target C library. Struct members are exposed
for allocation and inspection; do not modify their internal bookkeeping. Codec
input/output buffers must not overlap. Sizes are explicit; padding and native
struct layout are never serialized.

The simulation reports state sizes for the current ABI. On the current 64-bit
development build they are 1,888 bytes per host and 9,976 bytes per radio.
Embedded alignment can differ. A default radio has eight TX fragments per zone
and sixteen shared RX fragments. Overflow returns `NL_ERR_FULL`; producers retain
their application message and retry when space becomes available. Successful
enqueue means local ownership transfer, not wireless delivery.

Pass monotonic processing-time microsecond timestamps from the application's
clock. Do not substitute saved PHY arrival timestamps when processing order can
differ. A stream
rejects timestamps preceding its last accepted packet; the scheduler also rejects
backward calls. No default idle timeout is assumed: choose one only if the
application can tolerate the restart ambiguity described in
[protocol decisions](Protocol_Decisions.md).

## Register a plugin

`plugins/counter.c` is a complete compiled example with a four-byte big-endian
application payload. `examples/simulation.c` wires a transmitter and a read-only
receiver to the portable radio core.

1. Create a `nl_plugin` descriptor and persistent context. Unused hooks may be null.
2. `nl_host_register()` reserves an opaque `nl_plugin_id` handle and calls
   `start(host, id, context)`. Initialize unset handles to `NL_PLUGIN_ID_NONE`;
   zero is a valid handle. Store handles without interpreting their bits.
3. Claim zones with `nl_host_claim()`. Shared readers receive only; exclusive owners
   may transmit. No claim is required or permitted for zone 0.
4. Return `NL_OK` from startup to activate the plugin. Sending during startup is
   rejected. A failed start invokes `stop` if supplied, releases all claims, and
   retires the handle; cleanup must tolerate partial initialization.
5. Send at most 100 bytes through `nl_host_send()`. Check its returned status;
   queue acceptance advances the per-zone sequence, while failure does not.
6. `nl_host_receive_frame()` accepts validated `D0` frames, deduplicates them, and
   invokes interested active plugins. `nl_host_receive()` accepts an already
   decoded fragment. A missing recipient returns `NL_ERR_NOT_FOUND` without
   consuming the host stream sequence.
7. Call `nl_host_tick()` from the event loop for periodic plugin work.
8. `nl_host_unregister()` invokes shutdown and releases every claim.

Receive/tick callbacks may send payloads and update claims. The recipient set for
the current fragment is fixed before callbacks run. Registry changes, recursive
receive/tick, and transport callback reentrancy are rejected with `NL_ERR_BUSY`.
Callbacks must return promptly. Received fragment pointers are borrowed for the
callback duration; copy data that must be retained. Logging callbacks observe
structured events and must not re-enter host APIs.

Plugins are trusted code in the same address space. Claims prevent accidental
cross-zone API use; IDs are not security credentials and no executable sandbox
exists. A slot's generation advances on shutdown or failed startup, so a retired
handle cannot access a replacement plugin. After all 24-bit generations have
been consumed, that slot is permanently unavailable until host reinitialization;
registration returns `NL_ERR_FULL` when no usable slots remain. Handles belong to
one host initialization lifetime and must never be passed to another host or
retained across reinitialization. Cancel timers/work before unregistering.
Remote devices do not yet share a claim table, so matching application payload
formats and unique origin IDs remain configuration responsibilities. Incoming
fragments with the host's own origin return `NL_ERR_CONFLICT` without dispatch.

## Transport and radio adapters

The host's `nl_send_fn` callback should encode a PUSH frame and hand it to an
adapter. Return `NL_OK` only once the adapter takes ownership of the fragment or
serialized bytes. The fragment pointer belongs to the host's stack and cannot
be retained after returning. A physical adapter must define how a radio-side
queue rejection is reported before promising reliable queue acceptance.

On the co-processor side, parse a whole command and call
`nl_radio_handle_frame(radio, request, response, token)`. PUSH enqueues TX data
and ignores the response/token pointers. PULL requires both output pointers and
returns a `D0` frame plus an `nl_pull_token`, or `NL_ERR_EMPTY`. It leaves the head
queued until `nl_radio_commit_pull(radio, response, token)` confirms ownership
transfer. `nl_radio_prepare_pull()` performs the same preparation directly.

Encode/copy both the response and token into adapter-owned storage before
asynchronous transfer. Commit after the adapter completes its handoff; an aborted
transfer can prepare again. The adapter-local token identifies a queue revision
and is **never serialized on the wire**. A stale response/token cannot remove
another head, even when its bytes are identical after sequence wrap. In latest
mode, a replacement invalidates a staged response: a stale commit leaves the
newer value available for the next PULL. Tokens belong to one radio initialization
lifetime; pending handoffs must be canceled before reinitialization. The radio
rejects new RX revisions with `NL_ERR_SIZE` after exhausting its uint64 token
counter rather than reusing tokens. `nl_radio_pull()` immediately transfers local
ownership for synchronous consumers. Physical delivery acknowledgment remains
unspecified.

RX defaults to `NL_RX_FIFO`. For self-contained state updates, set
`nl_radio_set_rx_policy(radio, NL_RX_LATEST_PER_STREAM)` while RX is empty. A newer
accepted `(origin, zone)` value replaces its queued predecessor in place and
increments `stats.coalesced`, including when the queue is full. Other streams
keep their relative order. Never enable this policy for fragment groups or
event streams that need every accepted value. Sixteen distinct streams can still
fill the shared queue; coalescing does not reserve capacity per zone.

For RF work, use `nl_radio_next_window()`, then
`nl_radio_prepare_tx(radio, now_us, fragment, window)` before **each** submission.
Before preparation, preflight the head with `nl_radio_peek_tx()` and inspect
timing through `nl_scheduler_current()`. Check that completion and receiver
processing fit the deadline: peers must process the first BURST **before** `start_us + slot_us`,
even when the selected sender window is already extended. Other submissions
must fit the current window. Use an extension only after a timely announcement.
Preparation peeks the current zone's head and refreshes the sender deadline if it
carries BURST, including late enqueue or a second fragment within a window.
`nl_radio_peek_tx()` alone does not apply timing flags. Pop only once the PHY
adapter takes ownership; if it rejects the submission, retain the head and retry.
The adapter must ensure peers process the first BURST announcement before their
original deadline, enforce airtime/completion limits, and reuse the sequence of
retransmissions. Call `nl_radio_receive()` only for packets accepted by the PHY
in the correct zone window. A fresh or duplicate BURST extends that current window
once, including when queue capacity rejects a fresh frame. A stale frame carries
no hold; prolonged congestion spanning 128 sequence values can therefore suppress
both data and timing control. Refresh the adapter deadline through
`nl_scheduler_current()` after RX processing; a previously returned window is
a snapshot. RX BURST flags with no current matching window are not carried into
a later slot. Missing burst announcements can still desynchronize peers, so
shared timing and control-loss recovery remain protocol work. `nl_radio_ready()`
reports whether RX data awaits the host; a GPIO adapter may use it for INT_READY.

Set active radio zones from `nl_zones_active_mask(&host.zones)` when applying local
configuration. This is a C-side operation in the simulation; a distributed SPI
configuration command is not defined yet. Disabling a zone with queued TX
returns `NL_ERR_BUSY`; drain it first. Zone 0 is automatically scheduled when TX
data exists or `nl_radio_request_management()` / MGMT_LISTEN requests a listen
slot.

See [platform integration](../platform/README.md) for the vendor SDK boundary.

## Offline tools

```sh
./build/nova-inspect fragment 'AF FE 00 AA FF'
./build/nova-inspect frame 'AA 01 02 0E 7C'
./build/nova-inspect stream fixture.bin
```

The first two commands print JSON. `stream` reads an existing binary file (or
stdin with `-`) and prints JSON Lines, using the same incremental parser as the
core. It never opens a network, serial port, or capture device. Non-hex input,
unsupported commands, malformed frames, truncated input, and streams without a
complete frame return a nonzero exit status. A stream may print valid frames
before reporting a malformed one. Noise outside frames is skipped.

The RF calculator uses explicit assumed bitrates, overhead, slots and host costs:

```sh
python3 tools/rf_feasibility.py --bitrate 2000000 --overhead-bytes 9 \
  --slot-us 644 --fixed-us 200 --zones 4 --metadata-slot --host-us 250 --require-fit
```

Output is JSON; `--require-fit` exits 2 if the requested copy/copies cannot fit or
a specified continuous input rate leaves no service headroom. Slot/extension
values must match the C scheduler's integer uint32 limits. Delivery bounds are
`null` for missed base/announcement deadlines or a rate at/above the modeled zone service
rate. `zone_service_hz` assumes one TX per zone window; `stream_load` reports the
fraction used by `--stream-hz`, assuming it is the sole stream in that zone.
The one-fragment-per-window model fits the fragment (and conservatively both
dual-band copies) against the base window. With BURST, completion must precede
the base deadline strictly. The extension lengthens rounds/service time but
cannot make that first announcement fit. Earlier separate announcements and
PHY holds during packet reception are not modeled.
Include worst-case radio RX processing delay and clock rounding/granularity in
`--fixed-us`, alongside setup/turnaround. `--host-us` is additional host/transport
delay after radio queueing; it does not buy time for a BURST hold. A computed
999.999 µs completion is too late if receiver processing records it as 1000 µs
against a 1000 µs base deadline.
Finite bounds assume common timing, one fragment per zone window, no loss or late scheduler calls,
the specified backlog, and no unaccounted processing cost. Secondary-band options
assume copies on one time-shared transmitter. A fitting sender budget does not
show that a receiver can hear both copies or gain redundancy. Bitrates mean
effective rates after FEC, spreading or line coding; the tool does not select or
validate a CC1352R PHY. See [validation](Validation.md) for assumptions and limits.

## Checks and packaging

The default build runs 33 CTest entries with Python and tools available:
the SDK's codecs, streams, host, radio, integration, simulation, and offline
tools; DMX framing/loopback and capture analysis; and the separate extended
prototype's C/Python tests, generated vectors, and network simulations; and
replays of every fuzz seed in `tests/fuzz/seeds/` (35 entries with security).
Use `-DNOVA_BUILD_EXTENDED=OFF` to omit the prototype. Release checks remain active;
they do not depend on `assert()` or `NDEBUG`.

```sh
cmake --build build --target docs
cmake --install build/core --prefix "$PWD/build/sdk"
cmake -S tests/consumer -B build/consumer -DCMAKE_PREFIX_PATH="$PWD/build/sdk"
cmake --build build/consumer
./build/consumer/consumer
```

Local GCC checks cover Debug, Release, address/undefined behavior sanitizers,
a freestanding core build, docs, and the installed-SDK consumer. See
[validation](Validation.md) for commands and results. Clang and vendor SDK
builds have not been run here.

## Fuzzing and long-term tests

`tests/fuzz/` has three libFuzzer harnesses with ASan and UBSan. Each one
checks invariants as well as crashes:

- `transport` covers SPI frames, fragments and the byte-stream parser. Every
  accepted input must re-encode to the same bytes.
- `radio` drives one `nl_radio` with random frames, commits, time jumps, TX
  windows and configuration changes. Every frame it emits must validate.
- `secure` checks seal-then-open round trips, bit flips, truncation,
  forgeries and replays through `nl_radio_receive_sealed`.

```sh
tools/fuzz.sh 600            # 10 minutes per harness; needs clang
tools/fuzz.sh 60 radio       # one harness
```

The corpus is kept in `build/fuzz-state` (`FUZZ_STATE`). Crashes are saved in
`<harness>/crashes/`, and running `build/fuzz/tests/fuzz/fuzz_<harness>
<file>` reproduces one. After a fix, copy the file into `tests/fuzz/seeds/<harness>/`.
Normal test builds replay every seed through gcc-built `replay_*` binaries, so
a fixed crash stays covered. `tools/check.sh` runs a 10-second fuzz smoke test
(`FUZZ_SECONDS`).

`tools/soak.sh` runs `nova-field-sim` over new seeds until `SOAK_SECONDS`
runs out. Each seed runs in Release with and without security, and in an
ASan+UBSan build with a tenth of the ticks. The next seed is saved, so no soak
repeats a seed.

`tools/longterm/install.sh` sets up both jobs as systemd user units on a build
machine:

- `nova-fuzz.service` fuzzes continuously.
- `nova-nightly.timer` runs `git pull`, `tools/check.sh` and a two-hour soak.

`tools/longterm/report.sh` summarises the last results, corpus sizes, crashes
and soak failures. Logs go to `~/nova-longterm/logs`.
