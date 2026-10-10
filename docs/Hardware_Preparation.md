# Documented hardware preparation

Prepare the documented **ESP32-S3 host**, **TI CC1352R radio**, **City Theatrical
5911 Multiverse Transmitter reference**, and **ETC ColorSource V fixture**. The
5911 is the 2.4 GHz, two-radio reference linked in the
[bench plan](Multiverse_2_4GHz.md). The silicon families are documented in
[the architecture background](Background.adoc) and
[the SPI design](spi_protocol.adoc).

The original target references identify silicon families and bench devices.
ESP32-S3 development-board products and CC1352R board revisions remain deployment
records. The ESP-IDF and TI SDK build baselines below are implementation choices.
The CC1352R compile project uses **LAUNCHXL_CC1352R1**; this identifies the vendor
project's board configuration and does not establish which physical board the
deployment owns. Record actual products, revisions and pin mappings with the
setup.

## ESP32-S3 vendor compile project

[The ESP-IDF check project](../platform/esp32/example/CMakeLists.txt) selects
`esp32s3`, includes the production Nova-Link component, and exercises an unordered
application/transport/logger manifest. Its backend reports an empty receiver and
rejects transmit requests. It configures no SPI/GPIO, radio, or network interface.
Its contexts live in static storage and the callbacks run on the application
task. ESP-IDF logging uses the SDK's normal console when run on a device. It is a
compile and lifecycle example, rather than a board driver.

With an installed ESP-IDF environment exported according to that SDK's own
instructions, run from the repository root:

```sh
idf.py --version
idf.py -C platform/esp32/example -B "$PWD/build/esp32-vendor" \
  -D SDKCONFIG="$PWD/build/esp32-vendor/sdkconfig" build
```

The chosen reproducible build baseline is **ESP-IDF v5.5.1**, revision
`fcae32885b0296b32044cb99ecbdc50d98dddb83`, with Xtensa GCC **14.2.0**
(`esp-14.2.0_20241119`). This SDK pin is an implementation choice added for the
build check. Keep a deployment's SDK selection recorded and revalidate its
build when changing versions.

On 2026-10-10 the actual ESP-IDF `esp32s3` build passed, compiling all 20 production
core/plugin source files, linking the application and bootloader, and generating
`build/esp32-vendor/nova_link_plugin_check.elf` and a 217,136-byte application
binary. Local evidence is recorded in `build/vendor-sdk-evidence.json` and
`build/vendor-sdk-build-final.log`; Python package versions are retained in
`build/vendor-sdk-python-freeze.txt`. This validates vendor compilation and image
generation. No hardware was present for execution, flashing or physical I/O
validation. The CC1352R vendor build is recorded separately below.

Keep the version output, ESP-IDF Git revision/release, toolchain version,
generated `sdkconfig`, and build logs with the artifact. The target is selected
by the project; a different `IDF_TARGET` is rejected. The output uses ESP-IDF's
normal build defaults: this check's generated configuration selects DIO flash,
80 MHz and 2 MB. These are compile-artifact defaults; deployment settings come
from the actual board record. Review flash/boot settings against the board before
using an image. This workflow performs no flashing and does not select any board
pins.

The offline platform test compiles the production component sources and runs the
same startup example with a desktop log shim. This catches missing sources and
portable API regressions; it does not substitute for an ESP-IDF compiler/build.

## CC1352R native compile project and receiver handoff

The reproducible compile baseline is **SimpleLink CC13xx/CC26xx SDK 7.41.00.17**,
**TI Arm Clang 3.2.0.LTS**, and **SysConfig 1.18.1** (build 3343), using the SDK's
**LAUNCHXL_CC1352R1** configuration. The
[CC1352R project](../platform/cc1352r/README.md) retains vendor startup,
RTOS/linker and generated board support while compiling the portable native radio
and complete-frame slave adapter. Its startup check runs only a local native
PUSH/PULL model loopback. It does not configure SPI transfers, GPIO mappings,
candidate RF settings or proprietary Multiverse decoding.

The [host backend and virtual SPI device](SPI_Backend.md)
exercise that same native slave boundary without hardware. Their driver status
and receipt tokens are local software metadata, with no new physical wire ACK or
empty/error encoding. A physical adapter still needs a reviewed way to obtain
those outcomes, plus chip-select framing, cancellation, interrupt and timing
rules.

On 2026-10-10 the actual TI build compiled and linked the native check, producing
`build/cc1352r-check/cc1352r-project/tirtos7/ticlang/nova-radio-check.out`
(519,168 bytes), plus an Intel HEX artifact. The linked image contains the eight
portable radio/slave sources and the native task check with vendor startup,
SysConfig and TI-RTOS support. The map reports 19,020 bytes of flash and 30,878
bytes of SRAM for this compile image. Separately, all **20 production sources**
passed strict C99 freestanding TI Arm Clang compilation. The unchanged vendor
`empty`, `spiperipheral`, and `rfPacketRx` examples also compiled and linked.
The stock RF example retains its supplied TI PHY; it does not establish a
Multiverse profile.

Exact commands, official download hashes, artifact/source hashes and logs are recorded
in `build/ti-sdk/vendor-evidence.json` and `build/ti-sdk/nova-cc1352r-build-final.log`.
The SDK ZIP SHA-256 is
`00a10b7f344a0fc5eb678d8137c3f56617737995e2e520f0394a4df6b184f12b`;
the Nova ELF SHA-256 is
`e20e74fec69918cb551142db902172426a28be19b6f1dd56f7771200c8f3008c`.
The [project guide](../platform/cc1352r/README.md) supplies the helper invocation
for an installed SDK/compiler/SysConfig environment. On this development host,
the compiler's compatibility library was extracted under ignored build storage
and selected for the build command; system libraries were unchanged.

This validates vendor compilation and image generation. The unchanged vendor
empty project retains its board-default LED0 GPIO and Power configuration; it
does not authorize deployment wiring. The Nova check opens no physical SPI or RF
driver, and no image was flashed or executed on hardware.

Use the receiver example supplied by the installed SimpleLink CC13xx/CC26xx SDK
for the actual CC1352R board, retain its SysConfig/SmartRF exports, and record the
SDK and compiler release. Build that vendor example unchanged first. The portable
radio source set is `src/status.c`, `src/fragment.c`, `src/transport.c`,
`src/stream.c`, `src/queue.c`, `src/scheduler.c`, and `src/radio.c`, with `include/`
on the include path and C99 enabled. For a direct Multiverse decoder, add
`src/dmx.c` and `src/multiverse.c`; the native fragment codec does not decode
Multiverse RF. A firmware project needs its vendor startup, linker, driver, and
RF-patch sources in addition to these portable files.

Keep generated RF settings in the receiver project. A profile identifies those
specific settings; it is not an inferred Multiverse PHY. Initially preserve raw
packet entries, actual tuned frequency, integrity result, monotonic timestamps,
and queue/UART drop diagnostics. Copy packet data from the RF callback into a
bounded task-owned queue; format and output captures from the task. A CC1352R
packet receiver is not a raw-IQ capture device.

The [capture service plugin](../include/nova_link/capture_plugin.h) provides a
portable JSONL output boundary for this handoff. It stages exact bytes in a
caller-owned buffer and retains the same record when the output is busy. The
board adapter owns RF callbacks, queue capacity, UART/file output and drop
diagnostics. Preserve payload bytes even when the candidate integrity check
fails; use `unknown` when the integrity check is not established. The service
neither decodes Multiverse nor configures a radio.

The service uses a plugin host even when no application/transmit plugins are
present. A CC1352R project using it also needs `src/host.c`, `src/zones.c`,
`src/module.c`, and `plugins/capture.c` in addition to the native source set
above. It can initialize a transport-free host and register just the capture
service; physical RF receive operations remain in the board adapter.

Initialize `nl_capture_context` with a stable `nl_capture_config`, register
`nl_capture_module()`, then call `nl_capture_submit()` with each task-owned
`nl_capture_observation`. `NL_OK` means the record is staged. `nl_host_poll()`
tries its output once; alternatively call `nl_capture_flush()` from the same
serialized owner. Only a successful output callback commits the record. A pending
record returns `BUSY` to another submit and vetoes ordinary module shutdown.
Account for upstream queue drops separately rather than overwriting that record.

The output callback accepts a **whole JSONL record atomically**. On any error it
must accept no bytes. A UART driver that writes only part of a buffer needs an
external bounded queue that copies the complete record on acceptance, then
tracks its own drain offset. Capture service acceptance then means local queue
acceptance; it does not mean the UART physically transmitted all bytes. That
queue remains a board-owned shutdown responsibility. Raw observations are not
authentication or confirmed Multiverse decoding.

## Reference bench record

Record the 5911 firmware, active radio(s), universe mapping, full SHoW ID,
SHoW Key, mDMX/FEC settings, ColorSource V firmware/address/personality, and
receiver board/revision plus SDK/configuration identifiers for each run. Establish
the existing transmitter-to-fixture output before captures. Use the
[capture schema and stimulus procedure](Multiverse_2_4GHz.md) and the analyzer
without translating raw captures to the synthetic replay profile. The proprietary
PHY, framing, hopping, and control exchanges still require real observations.

This preparation uses existing application connectivity and requires no UniFi,
gateway, firewall, routing, or DNS changes.
