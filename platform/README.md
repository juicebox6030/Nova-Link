# Platform integration boundary

The portable core does not configure a board, radio, network, or gateway. Hardware
adapters must provide stable state storage, synchronization, clocks, SPI/GPIO
drivers, and RF submission/completion. No packet captures or physical-link tests
are part of the software simulation.

## ESP32-S3

An ESP-IDF component definition is supplied in `platform/esp32/`. Add that directory
to the firmware project's `EXTRA_COMPONENT_DIRS` before including ESP-IDF's
`project.cmake`, then link/use the component from your application. This definition
compiles the portable native core/module base, DMX library, normalized Multiverse
engine, and counter, Multiverse-model, radio-link, logging, configuration and
raw-capture service plugins;
the asynchronous native SPI backend service and complete-frame slave helper are
also compiled. It supplies no pin mappings, SPI setup, tasks, Wi-Fi/BLE
configuration, flash settings, or radio firmware.

Keep `nl_host` and module contexts in persistent application storage. Initialize
the base with `nl_host_init_plugins()` and register a dependency manifest. Supply
the radio-link plugin's frame exchange/commit callbacks using the project's SPI
master driver; call `nl_host_poll()` to process input and tick applications.
The `nl_spi_backend` service supplies a bounded asynchronous implementation of
those exchange callbacks around an `nl_spi_driver`; use its radio-link module
wrapper to declare the provider dependency. The board layer implements that
driver's begin, finish, receipt settlement, readiness and cancellation callbacks.
The legacy direct send/receive entrypoints remain available. Handle INT_READY in
the board layer, posting work from
an ISR to the owning event loop/task. The core is not ISR-safe or thread-safe.
The [ESP32-S3 compile/startup project](esp32/example/CMakeLists.txt) provides a
vendor build entrypoint with no radio or transport I/O. See the
[hardware preparation guide](../docs/Hardware_Preparation.md) for the build and
capture handoff. The actual `esp32s3` vendor build passed with ESP-IDF v5.5.1 and
Xtensa GCC 14.2.0, compiling all production sources and producing ELF/BIN images.
Hardware execution remains unverified. The separate offline check compiles the
portable sources and runs the example lifecycle with a desktop compiler.
The configuration service accepts a caller-supplied text buffer; firmware owns
its source, storage and application policy. The desktop configuration CLI is an
offline example and is not part of the component.
The installed developer targets `nova_plugin_conformance` and
`nova_fault_backend` are excluded from this component, along with the synthetic
Multiverse test codec and developer-only `nova_spi_virtual` driver.

## TI CC1352R

Compile the relevant `src/*.c` files with C99 support and add `include/` to the SDK
project's include path. A radio-only image needs status, fragment, transport,
stream, queue, scheduler, and radio modules; host/zones are optional.

Use vendor SPI slave/GPIO drivers around the framing parser and PUSH/PULL
dispatcher. The portable `nl_spi_slave` helper validates one complete request,
stages a native response, and preserves its radio revision until commit or
cancel. Driver outcomes and tokens are local metadata; no physical acknowledgment
or empty/error bytes are defined. Drive RF operations from scheduled windows and call
`nl_radio_prepare_tx()` before each submission to refresh current BURST timing.
Ensure peers process the first BURST announcement before their original deadlines,
enforce PHY deadlines, and retain ownership of fragments while asynchronous TX
is in progress. Deliver
CRC-accepted RF bytes to the fragment decoder and portable radio RX path.

Frequency selection, legal transmit power, PHY/EasyLink/802.15.4 choice,
dual-band arbitration, common clock synchronization, and interrupt/electrical
timing remain board/protocol work. The configurable slot duration is a software
parameter, not a demonstrated physical timing budget.

## Before implementing board drivers

For direct Multiverse work, use the separate normalized TX/RX API in
`nova/multiverse.h`, not the native fragment decoder. The
[emulator and adapter contract](../docs/Multiverse_Emulator.md) describes local
completion ownership, atomic level delivery, clocks, recovery, and the still
unknown RF format. The synthetic codec is a tools/tests dependency and is not
included in the ESP-IDF component or installed SDK.

The installed Multiverse-model plugin carries normalized DMX state through native
NLM1 application payloads and FIFO queues. It shares the common module lifecycle
with transport and logging; it does not configure PHY settings or implement
proprietary Multiverse RF. Replace or add a verified RF backend once its format
is established, preserving explicit ownership and model/RF boundaries.

Resolve response layouts for PING/STATUS, empty PULL and failed PUSH behavior,
SPI chip-select/framing/timeout rules, and remote active-zone configuration.
These are software design decisions that can be reviewed without hardware.
See [protocol decisions](../docs/Protocol_Decisions.md) and the
[roadmap](../docs/Development_Roadmap.md) for the remaining work.

## Board and capture handoff

Use the documented ESP32-S3 host and CC1352R radio families with the City
Theatrical 5911 2.4 GHz reference and ETC ColorSource V fixture. The documentation
does not establish the user's development-board products/revisions. The
ESP32-S3 compile baseline is ESP-IDF v5.5.1. The CC1352R compile project uses
LAUNCHXL_CC1352R1 with SimpleLink CC13xx/CC26xx SDK 7.41.00.17, TI Arm Clang
3.2.0.LTS and SysConfig 1.18.1. Record the deployment details,
available debug/programming interfaces, firmware
versions and board schematics with the actual setup. The
[hardware preparation guide](../docs/Hardware_Preparation.md) supplies the
ESP32-S3 and [CC1352R](cc1352r/README.md) build entrypoints and capture handoff without choosing
unverified pins or proprietary PHY settings.

The existing backend contract gives a future board plugin a concrete boundary:

| Operation | Board/backend responsibility | Portable contract to preserve |
| --- | --- | --- |
| Start | Initialize the chosen driver and establish a serialized event-loop owner | Attach through the module lifecycle; failed startup releases ownership and cancels initialized work |
| PUSH exchange | Encode native framing and submit through the selected physical interface | Failure must not enqueue; success means local ownership acceptance, with a defined bounded queue |
| PULL exchange/commit | Retain the response and revision until its handoff is committed | Failed commit retries the exact receipt; STALE/EMPTY invalidates it without removing a replacement |
| RF submission/completion | Retain bytes until completion or confirmed cancellation and enforce the chosen PHY deadlines | Local queue acceptance, physical completion and peer acknowledgment are separate events |
| Stop/restart | Drain or cancel async I/O before storage reuse, and reject callbacks from an earlier lifetime | Pending ownership vetoes ordinary shutdown; startup rollback must clean up without that veto |
| Clock/interrupt | Supply monotonic timestamps and post ISR events to the owner | Host/radio calls are serialized; no driver callback recursively dispatches or polls the host |

Use the [conformance harness](../docs/Plugin_Conformance.md) and
[fault backend](../docs/Transport_Fault_Simulation.md) to exercise those lifecycle
and ownership paths on the development machine before replacing the backend
with vendor I/O. Their passing reports validate software contracts only.
The [SPI backend and virtual driver](../docs/SPI_Backend.md) now exercise that
boundary using the actual native host and slave adapters. The virtual device supplies local status
and receipt outcomes that a physical driver must resolve under an explicit
protocol. It does not validate chip-select timing, GPIO mappings or electrical
behavior.

Capture firmware should preserve raw received bytes, receive timestamps,
frequency/PHY configuration, integrity results, board/firmware identifiers and
the known DMX stimulus using the [capture log and bench plan](../docs/Multiverse_2_4GHz.md).
Keep undecoded bytes and settings rather than inferring proprietary fields. The
existing analyzer can compare labeled capture distributions; the synthetic
replayer accepts only its declared local test profile. Feed real captures to
independent framing/PHY analysis before implementing or validating proprietary
Multiverse TX. The normalized model, NLM1 payloads and test codecs do not supply
the missing RF encoding.
