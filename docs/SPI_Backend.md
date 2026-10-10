# SPI backend service

The ESP32-S3 master uses the installed, caller-owned
[`nl_spi_backend`](../include/nova_link/spi_backend.h) service beneath the existing
`radio-link` transport plugin. It sends the documented native
`[AA][LEN][COMMAND][DATA]` frames to a CC1352R slave. This transports Nova-Link
fragments; it does not encode or decode proprietary Multiverse RF.

Initialize stable contexts and zero-initialized module instances, then start an
unordered manifest:

```c
nl_spi_backend spi;
nl_radio_link link;
nl_radio_link_config link_config;
nl_module_instance instances[2] = {0};
/* driver callbacks and driver.context remain alive for the registration. */
nl_spi_backend_init(&spi, &driver);
nl_spi_backend_link_config(&spi, 1, &link_config);
nl_radio_link_init(&link, &link_config);
nl_module backend = nl_spi_backend_module(&spi);
nl_module transport = nl_spi_backend_link_module(&link);
const nl_module *modules[] = {&transport, &backend};
nl_modules_start(&host, modules, instances, 2);
```

Check each API result in production code. Initialize the base with
`nl_host_init_plugins()`. The default transport remains `radio-link`, so existing
application dependencies work; its descriptor requires `spi-backend`. When
renaming the service, change the transport dependency list before registration.
The descriptors and contexts remain at stable addresses until shutdown.

Call `nl_host_poll(host, now_us)` from one serialized owner. The service begins
or finishes at most one transaction per poll; the radio-link provider then
settles input and application ticks run. Do not call tick a second time. Native
frames have a 105-byte maximum and native payloads have a 100-byte maximum.

## Driver ownership

The board adapter supplies `nl_spi_driver` callbacks. `ready()` samples the
adapter's task-owned interpretation of INT_READY. `begin()` accepts immutable
request storage and a local transaction identifier; an error accepts no work.
`finish()` returns BUSY while the driver still owns that request. Other results
end request ownership. Tokens monotonically increase across service stop/start;
exhaustion prevents starting another transfer instead of wrapping.

The backend contains one queued TX slot, one in-flight transaction, and one
cached RX receipt. PUSH success from the transport means **local queue
acceptance**. A second PUSH returns BUSY without changing the queued bytes. The
service retains exact bytes across delays and retries, and alternates TX and
ready RX opportunities so continuous application traffic cannot starve receive.
A cached RX receipt is settled before another device transaction starts.

A PULL completion supplies exactly one native `D0` frame and a nonzero,
adapter-local receipt. The backend validates framing, direction, and exact
length before exposing that receipt to the transport. Malformed framing calls
`settle(receipt, false)` to abort the staged response without dropping radio
input. Abort errors retain the receipt and retry abort; a valid response remains
immutable until `settle(receipt, true)` transfers ownership. BUSY or other
retryable settlement errors hold it, and STALE/EMPTY release invalidated
receipts without popping a replacement. The transport dispatches a valid frame
at most once while retrying settlement, including terminal application errors.

The driver binds the receipt to its original prepared radio response. The
receipt is not serialized and is not a physical acknowledgement. All callback
outcomes, including EMPTY and radio queue errors, are local C metadata. The
physical SPI protocol still lacks PUSH acknowledgement and empty/error response
bytes. A deployment must establish those mappings before claiming remote
acceptance or physical interoperability. PING and STATUS wire responses remain
unsupported.

## Uncertain transmit completion

A terminal PUSH error with `uncertain=false` must certify that the peer did not
accept the request. The backend may safely retry those immutable bytes. A driver
that cannot establish that fact returns `uncertain=true`; the backend holds the
TX slot and performs no automatic resend. A malformed successful PUSH completion
that unexpectedly carries response bytes or a receipt also holds the slot as
uncertain. RX can continue while TX is held.

From outside callbacks, call `nl_spi_backend_resolve_tx(&spi, retry)` only after
choosing an appropriate recovery. `retry=true` retransmits the exact bytes and
can duplicate a request already accepted by the peer. `retry=false` discards
local ownership without proving delivery and can lose an update. No default
resolution is chosen. For state plugins, an application can request a subsequent
FULL update after discarding an uncertain transfer. A peer restart still needs
its documented native sequence and model-session recovery; the service does not
silently reset either tracker.

## Lifecycle and physical limits

The service and transport veto ordinary shutdown while accepted TX, a transfer,
a held response, an abort, or driver-owned work remains. Finish or explicitly
resolve work and retry shutdown. Manifest startup rollback invokes `stop()` even
when `start()` failed; the driver must cancel or drain all request and receipt
ownership before returning. These callbacks run on the host task rather than an
interrupt context. Stop clears held ownership and timing state but preserves
transaction token history. Do not reinitialize a live backend or driver.

The adapter owns SPI clock rate, chip-select, duplex scheduling, padding/dummy
bytes, actual transfer lengths, GPIO configuration, DMA storage, timeouts, and
interrupt-to-task handoff. Supply board and pin records instead of guessing
values. Reject/truncate at the adapter boundary safely; `finish()` must never
write beyond its supplied capacity. Clock values are monotonic microseconds;
backward values skip driver progress and count an error.

The native frame envelope has no transport checksum. A plausible corrupted
payload can pass native framing validation. Multiverse-model NLM1 application
CRC detects corruption in its own payload; this does not authenticate a sender
or add a generic SPI checksum. Logical simulations and vendor compilation cannot
validate electrical timing, firmware execution, physical acknowledgements, or
Multiverse RF interoperability.

[`test_spi_backend.c`](../tests/test_spi_backend.c) exercises immutable retry,
post-acceptance uncertainty, malformed success, rollback, restart, deferred
commit/abort, stale receipts, clock and token limits, and receive progress while
an actual host application sends every tick. The paired virtual-device tests
add a complete master/slave path through the native radio handler.

The actual service and SPI transport also run all seven reusable plugin
conformance cases each, including immutable full-queue retries and clean
reinitialization with fresh lower-sequence work. Virtual faults distinguish
definite rejection, uncertainty before acceptance, and uncertainty after local
slave acceptance. Explicit retry preserves the held bytes; discarding a held
transfer and forcing a later FULL recovers model state. RX remains available
while TX awaits that explicit decision.

## Run paired and simultaneous two-way scenarios

`NovaLink::nova_spi_virtual` is opt-in developer support and is excluded from
the production plugin aggregate and vendor board components. It wraps the actual
backend and native slave helper; a separate logical air path preserves FIFO
ownership between native radio queues. It serializes native frames and models
bounded transfer delay, disconnection, malformed requests/responses, receipt
retry and uncertainty with caller-owned storage.

```sh
./build/nova-spi-pair-sim
./build/nova-spi-duplex-sim
ctest --test-dir build --output-on-failure -R 'spi_'
```

The paired scenario reconstructs 13 exact 512-slot frames and delivers 50 counter
messages while reaching the native 8-TX/16-RX queue limits and retaining FIFO
work across 273 congestion retries. It exercises definite rejection, delayed
completion, both uncertainty outcomes and explicit resolution, disconnect,
malformed input, corruption, deferred settlement and restart.

The simultaneous two-way scenario uses two independent logical air paths and
production `nl_host_poll()` ticks. Both hosts transmit and receive 512-slot DMX
in distinct zones. It verifies every committed frame against a complete submitted
snapshot, prevents regression to an older snapshot, reaches full queues, injects
an outage, recovers exact final frames, drains owned work and then reports loss
through silence. The deterministic baseline delivers 46/42 frames from 20/17
distinct snapshots; TX queue peaks are 8/8 and RX queue peaks 16/3. Logical
delays and delivery counts do not imply a real PHY rate or latency bound.
