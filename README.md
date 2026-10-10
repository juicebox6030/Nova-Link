# NOVA-LINK

NOVA-LINK is an open wireless protocol and firmware SDK for live event applications
such as lighting, audio control, and synchronization. The intended system uses an
ESP32-S3 plugin host and a TI CC1352R radio co-processor.

The repository currently provides a **portable C99 implementation of the protocol
and application core**, with tests and an in-memory simulation. Native SPI host
and slave adapters provide portable asynchronous ownership boundaries; physical
SPI/GPIO drivers and over-the-air operation still require implementation and
validation. Dual-band
redundancy and sub-5 ms delivery are design targets, not measured capabilities.

## Build and try it without hardware

Requires CMake 3.16+ and a C99 compiler. Python 3 enables inspection and RF-budget tests;
Doxygen enables API documentation. The library has no third-party dependencies.

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build --parallel
ctest --test-dir build --output-on-failure
./build/nova-sim
./build/nova-plugin-sim
./build/nova-plugin-fault-sim
./build/nova-spi-pair-sim
./build/nova-spi-duplex-sim
./build/nova-config-manifest examples/plugins.ini
./build/nova-inspect frame 'AA 06 03 AF FE 00 AA FF'
./build/dmx_loopback
```

The simulation sends 300 counter messages through two plugin hosts, framed
transport, radio queues, and simulated RF delivery. Every message arrives twice,
as a model of redundant bands; exactly one copy reaches the receiving plugin.
The 8-bit sequence counter wraps during the run. Time is logical, so this does
not measure RF latency or physical throughput.

For memory and undefined-behavior checks on a toolchain with sanitizer runtimes:

```sh
cmake -S . -B build/sanitized -DCMAKE_BUILD_TYPE=Debug -DNOVA_ENABLE_SANITIZERS=ON
cmake --build build/sanitized --parallel
ctest --test-dir build/sanitized --output-on-failure
```

Build just the library for integration:

```sh
cmake -S . -B build/core -DNOVA_BUILD_TESTS=OFF -DNOVA_BUILD_TOOLS=OFF -DNOVA_BUILD_EXTENDED=OFF
cmake --build build/core
```

Use `add_subdirectory()` and link `NovaLink::nova_link`, or install the SDK with
`cmake --install build/core --prefix <sdk-directory>` and use
`find_package(NovaLink 0.1 CONFIG REQUIRED)`. See the
[development guide](docs/Development.md) for plugin and embedded integration.
The independent DMX library is installed as `NovaLink::nova_dmx`.
Link `NovaLink::nova_plugins` for the included counter, Multiverse-model,
radio-link transport, asynchronous native SPI backend, logger, configuration and
capture plugins, or select their individual targets.
The base initializes with `nl_host_init_plugins()`; an unordered manifest starts
providers before consumers, and `nl_host_poll()` polls input then ticks plugins.
See [the compiled plugin guide](plugins/README.md) for the common module API.

Generate a standalone plugin starter with
`python3 tools/new_plugin.py my-plugin --kind application --output build/my_plugin`.
The generated CMake project uses the installed SDK and includes a lifecycle smoke
test and a reusable [plugin conformance suite](docs/Plugin_Conformance.md).
The [development guide](docs/Development.md) explains how to build it.
Link `NovaLink::nova_plugin_conformance` from plugin tests to check the common
lifecycle contract; reports distinguish exercised cases from unsupported optional
capabilities. `NovaLink::nova_fault_backend` provides selectable deterministic
delay, disconnect and congestion scenarios for transport tests. These developer
targets are separate from `NovaLink::nova_plugins` and the ESP-IDF component.
The [configuration service](docs/Plugin_Configuration.md) and offline
`nova-config-manifest` example compose installed plugins from bounded INI text.
Run `nova-plugin-fault-sim` for deterministic delayed transfers, disconnects,
congestion and explicit restart; see its
[scenario guide](docs/Transport_Fault_Simulation.md).
The [hardware preparation guide](docs/Hardware_Preparation.md) uses the documented
ESP32-S3, TI CC1352R and City Theatrical 5911 reference. Its capture service stages
raw observations in the existing JSONL schema; board I/O and real Multiverse RF
decoding still require implementation and measurements. Both documented vendor
compile projects build with pinned SDK/toolchain baselines; see the guide for
their artifacts and deployment records.
The [native SPI backend](docs/SPI_Backend.md) connects the radio-link provider to
a caller-supplied asynchronous driver. Its completion outcomes and receipt tokens
are local adapter metadata; the existing wire format defines no physical PUSH
acknowledgment or empty/error response.
`NovaLink::nova_spi_virtual` is an explicit developer dependency that connects
the actual host backend and slave helper using native serialized frames. Run
`nova-spi-pair-sim` for the counter/Multiverse-model pair under logical transfer
delays and injected faults. See the [SPI simulation guide](docs/SPI_Backend.md).
Run `nova-spi-duplex-sim` for simultaneous two-way 512-slot DMX using production
plugin ticks, exact frame checks, congestion, outage recovery and silence expiry.
The virtual driver is excluded from the production plugin aggregate and
ESP-IDF component; its software outcomes do not establish physical timing or
Multiverse interoperability.

## Implemented core

- Explicit DataFragment serialization, field/length validation, and golden vectors.
- Command framing and incremental parsing across arbitrary byte boundaries.
- Per-origin/per-zone duplicate and stale-packet rejection, including sequence wrap.
- Exclusive or shared read-only zone claims; globally accessible metadata zone 0.
- Static plugin registration with generation handles, startup rollback, shutdown,
  payload send/receive, periodic hooks, and guarded structured logging callbacks.
- Named modules with declarative claims, provider dependencies, transactional
  manifest startup, and dependency/ownership checks during shutdown.
- Lifecycle-managed transport and logging providers using the same plugin API.
- Configuration service with bounded, schema-validated INI buffers and typed values.
- Bounded TX/RX queues with in-process backpressure, retry-safe deduplication,
  and optional latest-state coalescing per stream.
- Clock-driven zone rounds, optional metadata slots, and bounded burst extensions.
- PUSH/PULL command handling with transactional PULL receipts, offline JSON
  inspection, an RF airtime calculator, and a counter plugin.
- Native complete-frame slave adapter and lifecycle-managed asynchronous SPI
  driver service, with immutable transfers and shutdown ownership checks.
- CMake installation, an ESP-IDF component definition, and Doxygen documentation.

All core storage is fixed or caller-owned. The library does not allocate memory,
create threads, read configuration files, or access a network or device. Its APIs
require serialized calls from the application's event loop. Zone checks provide
cooperative access control for trusted compiled plugins; they are not a memory
sandbox.

## Protocol

Eight logical zones are available: zone 0 for metadata, zones 1–7 for plugin data.
Plugins own application payload encoding. The implemented fragment is:

```text
[origin:3 | zone:3 | BURST:1 | MGMT_LISTEN:1][sequence:8][0..100 payload bytes]
```

The maximum serialized fragment is 102 bytes. Larger messages require an
application-defined fragmentation/reassembly format; the core returns an error
instead of truncating or inventing such a format.

The software transport envelope is `[0xAA][LEN][COMMAND][DATA]`, where `LEN`
includes the command. This makes the existing command list and variable payloads
unambiguous in software. Its compatibility with a future board adapter still
needs validation. The [protocol decisions](docs/Protocol_Decisions.md) explain
conflicting earlier notes, sequence limits, and unspecified commands.

## DMX and Multiverse work

The portable DMX library encodes level frames and parses validated UART
BREAK/MARK/byte events. The [Multiverse bench plan](docs/Multiverse_2_4GHz.md)
describes direct CC1352R interoperability work. The capture analyzer accepts
existing JSONL observations:

```sh
python3 tools/analyze_rf_capture.py examples/rf_capture.simulated.jsonl
```

The [Multiverse software emulator](docs/Multiverse_Emulator.md) now models both
TX and RX: chunked full/delta updates, asynchronous completion/retry ownership,
atomic receive reconstruction, duplicate/loss handling, and resynchronization.
Generate and replay a synthetic capture through the same C receive engine:

```sh
./build/nova-multiverse-sim --seed 42 --loss-percent 20 \
  --capture build/multiverse.synthetic.jsonl
python3 tools/replay_multiverse.py build/multiverse.synthetic.jsonl \
  --end-us 3130200 --summary-only
```

The installed `NovaLink::nova_multiverse` library exposes normalized DMX state
and adapter ownership APIs. Its synthetic test codec is excluded from SDK
installation. Actual Multiverse RF reception, decoding, transmission, and fixture
operation remain unimplemented and unverified; the RF format needs real evidence.
The analyzer also supports `--compare-stimuli baseline channel_1_32` to inspect
candidate byte differences in labeled captures without claiming channel decoding.

The installed `NovaLink::nova_multiverse_plugin` connects that engine to the
common host/module lifecycle. It segments a 512-channel frame into native NLM1
application payloads, retries queue pressure, and delivers complete RX frames
atomically. `nova-plugin-sim` runs it alongside counter, transport and logger
plugins with injected loss/corruption and final recovery. NLM1 is a documented
NOVA-LINK application format; real Multiverse RF still needs captures and hardware.

## Extended protocol prototype

The [extended prototype](experimental/extended/README.md) preserves the separate
implementation with CRC-8 link frames, metadata discovery, segmentation, INI
configuration, Python codecs, and a multi-node RF simulator. The default build
tests it alongside the SDK; use `-DNOVA_BUILD_EXTENDED=OFF` to omit it.

Its `[AA][CMD][LEN][DATA][CRC8]` transport differs from the SDK's
`[AA][LEN][CMD][DATA]`. Both libraries export overlapping `nl_*` symbols and
must be used in separate programs. The extended API is not part of the installed
SDK. Neither transport is an established physical-radio interoperability format.

## Project layout

| Directory | Purpose |
|---|---|
| `include/nova_link/` | Public C API |
| `src/` | Portable protocol, host, and radio core |
| `plugins/` | Compiled application, transport, logger and configuration plugins |
| `support/` | Reusable plugin conformance harness for developer tests |
| `examples/` | Native and Multiverse-model simulations and DMX loopback |
| `tools/` | Plugin starters, offline inspection, RF budgets/capture comparisons, and synthetic replay |
| `tests/` | Unit, integration, CLI, and installed-SDK checks |
| `platform/` | Board integration contracts and ESP-IDF component |
| `config/` | CMake package configuration |
| `experimental/extended/` | Separate extended API, simulator, codecs, and vectors |
| `docs/` | Architecture, development guide, decisions, and roadmap |

Generate the public API reference with `cmake --build build --target docs` when
Doxygen is installed. Output is `build/api-docs/html/index.html`.
The `docs-extended` target generates the prototype reference in
`experimental/extended/build/doxygen/html/index.html`.

The CI workflow template is [config/ci.github-actions.yml](config/ci.github-actions.yml).
Copy it to `.github/workflows/ci.yml` to enable GitHub Actions; publishing that
path requires GitHub authentication with the `workflow` scope. Local build and
CTest checks do not require it.

The [development roadmap](docs/Development_Roadmap.md) separates completed software
from remaining protocol decisions and board work. The [validation record](docs/Validation.md)
documents software checks, Opus 5.5 High checkpoint reviews, and RF assumptions.

## License and credits

[GPL-3.0](LICENSE). Designed by [Brent Scoggins](https://github.com/Juicebox6030),
[Luminary Technology and Productions](https://LuminaryTechnology.productions).
AI-assisted development.
