# NOVA-LINK

NOVA-LINK is an open wireless protocol and firmware SDK for live event applications
such as lighting, audio control, and synchronization. The intended system uses an
ESP32-S3 plugin host and a TI CC1352R radio co-processor.

The repository currently provides a **portable C99 implementation of the protocol
and application core**, with tests and an in-memory simulation. Board drivers and
over-the-air operation are still to be implemented and validated. Dual-band
redundancy and sub-5 ms delivery are design targets, not measured capabilities.

## Build and try it without hardware

Requires CMake 3.16+ and a C99 compiler. Python 3 enables inspection and RF-budget tests;
Doxygen enables API documentation. The library has no third-party dependencies.

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build --parallel
ctest --test-dir build --output-on-failure
./build/nova-sim
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

## Implemented core

- Explicit DataFragment serialization, field/length validation, and golden vectors.
- Command framing and incremental parsing across arbitrary byte boundaries.
- Per-origin/per-zone duplicate and stale-packet rejection, including sequence wrap.
- Exclusive or shared read-only zone claims; globally accessible metadata zone 0.
- Static plugin registration with generation handles, startup rollback, shutdown,
  payload send/receive, periodic hooks, and guarded structured logging callbacks.
- Bounded TX/RX queues with in-process backpressure, retry-safe deduplication,
  and optional latest-state coalescing per stream.
- Clock-driven zone rounds, optional metadata slots, and bounded burst extensions.
- PUSH/PULL command handling with transactional PULL receipts, offline JSON
  inspection, an RF airtime calculator, and a counter plugin.
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

The example is synthetic. Multiverse RF reception, decoding, transmission, and
fixture operation remain unimplemented and unverified.

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
| `plugins/` | Example compiled counter plugin |
| `examples/` | Complete in-memory simulation |
| `tools/` | Offline fragment/frame/stream inspection and RF feasibility calculator |
| `tests/` | Unit, integration, CLI, and installed-SDK checks |
| `platform/` | Board integration contracts and ESP-IDF component |
| `config/` | CMake package configuration |
| `experimental/extended/` | Separate extended API, simulator, codecs, and vectors |
| `docs/` | Architecture, development guide, decisions, and roadmap |

Generate the public API reference with `cmake --build build --target docs` when
Doxygen is installed. Output is `build/api-docs/html/index.html`.
The `docs-extended` target generates the prototype reference in
`experimental/extended/build/doxygen/html/index.html`.

The [development roadmap](docs/Development_Roadmap.md) separates completed software
from remaining protocol decisions and board work. The [validation record](docs/Validation.md)
documents software checks, Opus 5.5 High checkpoint reviews, and RF assumptions.

## License and credits

[GPL-3.0](LICENSE). Designed by [Brent Scoggins](https://github.com/Juicebox6030),
[Luminary Technology and Productions](https://LuminaryTechnology.productions).
AI-assisted development.
