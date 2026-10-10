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

The simulation reports state sizes for the current ABI; embedded alignment can
differ. A default radio has eight TX fragments per zone
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

## Compose plugins with modules

Use `nova_link/module.h` to describe deployable capabilities with one interface.
An `nl_module` contains its name, version, kind (`NL_MODULE_APPLICATION`,
`NL_MODULE_TRANSPORT`, or `NL_MODULE_SERVICE`), declared zone claims, named
dependencies, optional local service pointer, and the existing `nl_plugin` hooks.
Application codecs, radio transports,
and local services use the same registration and shutdown path. The base owns
lifecycle, access checks, sequence numbers, and dispatch; plugins own application
and device behavior.

Names identify local instances. They are not serialized and do not negotiate
remote payload compatibility. Use different names for multiple instances of one
implementation. Version and kind describe the module for inspection; they do not
change native packets. A dependency names another local module and establishes
startup/shutdown ordering. A service pointer is borrowed local state; consumers
must not retain it beyond the provider's lifetime.

Built-in factories provide a starting point:

| Module | Installed header | Constructor | Default dependency |
|---|---|---|---|
| Counter | `nova_link/counter_plugin.h` | `nl_counter_module()` | `radio-link` |
| DMX/Multiverse model | `nova_link/multiverse_plugin.h` | `nl_multiverse_module()` | `radio-link` |
| Radio transport | `nova_link/radio_plugin.h` | `nl_radio_link_module()` | None |
| Host event logger | `nova_link/logger_plugin.h` | `nl_logger_module()` | None |
| Configuration service | `nova_link/config_plugin.h` | `nl_config_module()` | None |
| Capture service | `nova_link/capture_plugin.h` | `nl_capture_module()` | None |

Descriptors can be adjusted before registration, including `name` and `requires`
when an application uses a differently named transport. A plugin that only uses
local services can omit transport dependencies and zone claims. Start with the
counter hooks for a small application protocol; use a service module for a
capability that should not receive zone payloads.

Module instances are caller-owned and zero-initialized. Keep their storage,
descriptor strings/lists, hook context, and backend context alive until shutdown.
The host copies its hook descriptor, while module metadata contains borrowed
references. Do not move active instances or edit their internal bookkeeping.

Use a separate mutable lifecycle context for each instance. Registration rejects
reusing a non-null `hooks.context` by default, before startup runs. Set
`shared_context = true` on both modules only for immutable/stateless context or
callbacks that safely track independent registrations. When sharing with a
legacy plugin, that flag explicitly asserts its context is safe to share too.

The complete [counter simulation](../examples/simulation.c) wires transport and
application modules to the portable radio core. Run it with `./build/nova-sim`.
The [combined plugin simulation](../examples/plugin_simulation.c) runs radio-link,
logger, counter, and Multiverse-model modules together on two hosts. Run
`./build/nova-plugin-sim` to verify atomic DMX frames alongside counter traffic
and duplicate rejection through the same lifecycle and transport.

After initializing persistent `counter`, `multiverse`, and `radio_link` contexts,
compose their descriptors like this. Use separate data zones, for example counter
zone 2 and Multiverse-model zone 1. Here `require()` checks for `NL_OK` and reports
an error, as in the simulation:

```c
nl_host host;
nl_module counter_module = nl_counter_module(&counter);
nl_module multiverse_module = nl_multiverse_module(&multiverse);
nl_module transport_module = nl_radio_link_module(&radio_link);
const nl_module *manifest[] = {
    &counter_module, &multiverse_module, &transport_module
};
nl_module_instance instances[3] = {0};

require(nl_host_init_plugins(&host, 1, 0), "base init");
require(nl_modules_start(&host, manifest, instances, 3), "start plugins");

/* In the serialized event loop, with a monotonic application timestamp: */
require(nl_host_poll(&host, now_us), "poll and tick plugins");

/* At shutdown, before contexts or backend storage go away: */
require(nl_modules_stop(instances, 3), "stop plugins");
```

The manifest can list consumers before their provider: `nl_modules_start()`
validates names, dependencies, individual claim declarations, context reuse, and
cycles, then starts providers first.
Malformed or unsatisfied manifests fail before hooks run. A startup failure rolls
back only modules started by that manifest, in reverse dependency order;
preexisting providers remain active. Declared claims are acquired before the
module's `start` hook, and failed startup releases them. Cleanup handles partial
startup. Conflicting claims between modules or existing owners can fail during
startup and trigger rollback; they are not all resolved during preflight.

`nl_module_find(&host, name)` returns an active local instance for inspection or
service access. `nl_module_register()` and `nl_module_unregister()` support a
single module. Removing a provider while an active module requires it returns
`NL_ERR_BUSY`, including through the lower-level host unregister API. Optional
`can_stop` hooks can refuse ordinary shutdown while work is pending. Check stop
status and keep context alive until shutdown succeeds. Startup rollback bypasses
that veto, so failed initialization must cancel its work in `stop`.
Shutdown can stop ready consumers before another module refuses to stop; repeat
`nl_modules_stop()` after pending work is resolved. Inactive entries are ignored.

## Generate a plugin starter

The starter generator implements the auto-generated boilerplate requirement in
[the design](requirements.adoc). It creates a standalone C99 project with a
public header, module implementation, CMake package lookup, README, lifecycle
smoke test and conformance adapter. Generate it into a new directory, then build it against an installed
SDK:

```sh
cmake --install build/core --prefix "$PWD/build/sdk"
python3 tools/new_plugin.py my-plugin --kind application --output build/my_plugin
cmake -S build/my_plugin -B build/my_plugin-build \
  -DCMAKE_PREFIX_PATH="$PWD/build/sdk"
cmake --build build/my_plugin-build
ctest --test-dir build/my_plugin-build --output-on-failure
```

The installed SDK includes the generator and adjacent templates, so a consumer
can run the same command without the repository:

```sh
python3 build/sdk/share/NovaLink/tools/new_plugin.py my-service \
  --kind service --output build/my_service
```

Use `--kind service` for a local provider or `--kind transport` for a transport
adapter. Applications default to the `radio-link` dependency; `--zone` selects
the data zone and repeated `--requires` options declare provider names. Context
remains caller-owned and hooks follow the same lifecycle as included modules.
Add application behavior and backend ownership handling to the generated hooks.

## Verify a plugin contract

Link tests to `NovaLink::nova_plugin_conformance` and provide an adapter that
constructs fresh persistent plugin contexts and the real module manifest for
each case. The [conformance guide](Plugin_Conformance.md) describes startup
rollback, ownership, dependency-safe shutdown, pending work, backpressure and
restart cases. Reports distinguish passed, failed and skipped cases; a skipped
optional capability is not evidence that it works. Generated projects register
the common conformance test alongside their smoke test through CTest when the
manifest leaves space for the runner's probe modules. The generated README
explains that capacity limit and the `NOVA_PLUGIN_CONFORMANCE` switch.

Transport tests can link `NovaLink::nova_fault_backend` to select deterministic
logical-time delays, disconnects and congestion. The backend exposes the same
frame exchange/commit lifecycle used by radio-link; see the
[fault guide](Transport_Fault_Simulation.md) for ownership and restart rules.
Keep these developer targets in test dependencies. The included plugin aggregate
and ESP-IDF component do not depend on them. `BUILD_TESTING=OFF` in a generated
project builds its production plugin without developer support.

## Configuration as a plugin

The [configuration service](Plugin_Configuration.md) provides strict, bounded
schema validation and typed values outside the base. It addresses the
design's Host CLI configuration requirement using an offline startup example:

```sh
./build/nova-config-manifest examples/plugins.ini
```

The example owns filesystem I/O and its compiled factory allowlist. The portable
service performs no filesystem, network, hardware or dynamic-library operations.
It uses the same module lifecycle as other local providers. Live reload and
runtime loading remain separate work; see the guide for parsing rules, lifetime
requirements and validation behavior.

## Register a plugin directly

`plugins/counter.c` is a complete compiled example with a four-byte big-endian
application payload. `examples/simulation.c` wires a transmitter and a read-only
receiver to the portable radio core.

1. Create a `nl_plugin` descriptor with designated initializers and persistent
   context. Unused hooks may be null. `poll` and `can_stop` extend the original
   descriptor; designated initialization avoids positional-field warnings when
   compiling older plugin code with strict flags.
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
7. Call `nl_host_poll()` for transport polling followed by periodic plugin ticks.
8. `nl_host_unregister()` invokes shutdown and releases every claim.

Receive/tick callbacks may send payloads and update claims. A poll hook may
deliver incoming fragments through `nl_host_receive()`/`nl_host_receive_frame()`;
it runs outside dispatch. `nl_host_poll()` runs all poll hooks, then one tick
phase. Use `nl_host_tick()` directly only when input polling is handled elsewhere.
Registry changes and recursive polling remain blocked
during polling. The recipient set for
the current fragment is fixed before callbacks run. Registry changes, recursive
receive/tick, and transport callback reentrancy are rejected with `NL_ERR_BUSY`.
Callbacks must return promptly. Received fragment pointers are borrowed for the
callback duration; copy data that must be retained. Logging callbacks observe
structured events and must not re-enter host APIs.

`nl_logger_init()` and `nl_logger_module()` register the host observer as a
service using the same lifecycle. The application supplies the callback and owns
its output; the portable service performs no I/O. Set a named dependency on the
logger when another module needs it active before startup. One provider owns the
observer, and registration cannot displace an existing callback or logger.

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

`nl_host_init_plugins()` initializes a base without a transport. The radio-link
module attaches its transport during startup and detaches its own provider during
shutdown. Sending with no provider fails; it does not consume the native sequence.
The legacy `nl_host_init()` constructor still accepts a direct send callback for
applications that compose their own adapter.

Initialize an `nl_radio_link` with `nl_radio_link_init()` and a persistent
`nl_radio_link_config`. Its `exchange` callback receives a PUSH or PULL `nl_frame`;
the backend owns encoding, physical I/O, and validated response decoding.
`poll_budget` bounds PULL work per base poll. An in-memory backend calls
`nl_radio_handle_frame()` and can exercise the same plugin lifecycle without
hardware.

An exchange error must leave a rejected PUSH unqueued. A successful PULL returns
both response and token; `NL_ERR_EMPTY` means no queued RX data. Response/token
output pointers are present for both commands and ignored for PUSH. Non-busy
receive rejection is terminal: the plugin counts/discards that head and commits
it so an unwanted zone, stale packet, or malformed response cannot stall RX.

For two-phase PULL, supply the optional `commit` callback and pass its
`nl_pull_token` back to `nl_radio_commit_pull()`. The transport plugin holds a
pending response when dispatch is busy or commit fails. After successful
dispatch it retries commit without dispatching that response a second time.
Commit `NL_ERR_STALE`/`NL_ERR_EMPTY` reports an invalidated backend receipt; the
link abandons that cached receipt and pulls again. This permits latest-value RX
replacement without trapping polling or shutdown on a retired token.
Without a commit callback, a successful PULL exchange transfers ownership to
the link's pending storage. Check the link's status/statistics rather than
assuming every poll delivered a frame.

Optional backend `start`/`stop` callbacks own device setup and cleanup. Resolve
outstanding transport ownership before reinitializing its context. A board
backend must define asynchronous transfer, cancellation, and queue draining;
the portable transport plugin cannot verify physical completion.
Pending RX ownership makes ordinary shutdown return `NL_ERR_BUSY`; a backend
`can_stop` callback can also protect application-owned queues or device work.

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
./build/nova-inspect frame 'AA 01 02'
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

The default build runs CTest entries with Python and tools available:
the SDK's codecs, streams, host, radio, integration, simulation, and offline
tools; DMX framing/loopback and capture analysis; Multiverse-model TX/RX,
fault simulation and replay; plugin configuration, generated starter projects,
reusable conformance and fault-backend scenarios; and the separate extended
prototype's C/Python tests, generated vectors, and network simulations.
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
[validation](Validation.md) for commands and results. Clang checks currently
exclude the extended prototype. The ESP32-S3 example also builds with the selected
ESP-IDF v5.5.1 toolchain; CC1352R vendor builds and hardware execution remain
unverified. See [hardware preparation](Hardware_Preparation.md) for the exact
SDK baseline and artifacts.

## Multiverse host/adapter integration

The separate installed `NovaLink::nova_multiverse` target consumes and produces
`nova_dmx_frame_t` levels through `nova/multiverse.h`. Its portable engine models
full/delta state, chunking, immutable TX preparation/completion, and atomic RX
reconstruction. It does not share native NOVA-LINK zones or transport bytes.
See the [emulator guide](Multiverse_Emulator.md) for runnable fault/replay
scenarios and the contract for a future verified RF adapter. Its synthetic codec
is intentionally excluded from the installed API.

`NovaLink::nova_multiverse_plugin` adds the native host plugin and its module
factory. Initialize `nl_multiverse_context`, then register it alongside its
transport. TX claims one data zone exclusively; RX uses a read-only claim and
explicit peer origin/session binding. NLM1 payload chunks carry at most 72 DMX
levels within the native 100-byte payload, so full 512-slot updates span several
fragments and become visible only after complete atomic RX reconstruction.

Use FIFO transport/radio RX queues for these chunk groups. Native deduplication
requires native sequence order even though the underlying model supports
reordered normalized chunks. Keep ticking through silence to observe loss;
`nl_multiverse_get()` exposes only a complete live frame, and the plugin does not
implicitly generate blackout levels. Transport queue acceptance advances the
TX model; periodic full refresh repairs downstream loss. These native payloads
do not implement real Multiverse RF, RDM, or fixture interoperability.
