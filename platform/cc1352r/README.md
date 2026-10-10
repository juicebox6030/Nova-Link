# CC1352R native SPI firmware compile check

The documented radio silicon is TI **CC1352R**. This project uses the SDK's
**CC1352R1_LAUNCHXL / LAUNCHXL-CC1352R1** target as a reproducible compilation
default. It does not establish the development board, revision, pin mapping or
electrical timing of the deployed Nova-Link device.

The pinned vendor baseline is **SimpleLink CC13xx/CC26xx SDK 7.41.00.17**,
**TI Arm Clang 3.2.0.LTS**, and **SysConfig 1.18.1**. The build uses the SDK's
TI-RTOS7 `drivers/empty` startup, linker and SysConfig scaffold. Its original
copyright notices remain in the generated project. The script copies the
scaffold and Nova sources into a separate build directory; it does not edit
the installed SDK.

## Build

Install those vendor releases using TI's installation instructions. From the
repository root, supply the corresponding installation paths:

```sh
python3 platform/cc1352r/build_check.py \
  --sdk /path/to/simplelink_cc13xx_cc26xx_sdk_7_41_00_17 \
  --compiler /path/to/ti-cgt-armllvm_3.2.0.LTS \
  --sysconfig /path/to/sysconfig_1_18_1/sysconfig_cli.sh \
  --build-dir "$PWD/build/cc1352r-vendor" --jobs 4
```

The SDK's Makefiles require installation paths without spaces. `--prepare-only`
stages the project without invoking the compiler. The script rejects a different
SDK release and refuses to overwrite a nonempty staging directory it does not
own. Generated sources, compiler output and the ELF/map artifacts stay under
the selected build directory. The helper also generates Intel HEX using the
compiler's `tiarmobjcopy`. Record tool versions and logs with the artifacts.
This command performs no device connection or flashing.

TI Arm Clang 3.2.0.LTS requires the host's `libtinfo.so.5`. On a newer Linux
distribution that only supplies a later ABI, provide a trusted compatible
library according to the vendor's host requirements. The build script inherits
the caller's environment; a locally extracted compatibility package can use
an `LD_LIBRARY_PATH` scoped to this command. The verification run used
`build/ti-sdk/tools/host-compat/lib/x86_64-linux-gnu`. The script neither installs
system libraries nor changes loader configuration.

## What the image checks

[`example/nova_radio_check.c`](example/nova_radio_check.c) implements the vendor
`mainThread` entrypoint using static native radio/slave storage. It exercises
the production C handler through native framed PUSH, local TX queue ownership,
software loopback into the RX queue, native framed PULL, exact decoded fragment
comparison and receipt commit. The task records its result in
`nova_cc1352r_check_status` and exits. The desktop `cc1352r_example` test runs
this same source; vendor compilation alone does not establish device execution.

The staged vendor startup uses a 2048-byte task stack. The stock `empty.syscfg`
includes Power, the RTOS kernel and the launchpad's LED0 configuration. Nova's
check does not call GPIO, SPI or RF I/O APIs. Those inherited launchpad settings
are compilation defaults, and need review against the actual board before
execution. The 1000-microsecond scheduler slot in the check is a local software
parameter rather than measured RF airtime.

## Board adapter boundary

[`nl_spi_slave`](../../include/nova_link/spi_slave.h) validates exactly one
complete `[AA][LEN][COMMAND][DATA]` native request before changing queue state.
It accepts PUSH only when the local bounded TX queue accepts ownership. It
copies a prepared PULL response to driver storage and retains the radio's RX
head until the adapter commits that complete response. Cancelling a staged
PULL leaves the queue entry available. Repeated PULL uses immutable staged
bytes; a coalesced replacement invalidates commit without removing the newer
entry. A cancelled receipt cannot commit a newly staged response.

Request bytes are borrowed for the exchange call only. The slave stores its
own response bytes, and the board driver owns the copy used by asynchronous
SPI. Receipt tokens and status codes are adapter-local C values. They are
never added to the native frame. Receipts belong to one initialized slave/radio
lifetime; cancel or drain all I/O before reinitializing either object and reject
late callbacks from the previous lifetime. Calls must share one serialized
task owner; the core is not ISR-safe or thread-safe.

A future physical driver must still define request/response turnaround,
chip-select boundaries, dummy bytes, timeout recovery, INT_READY wiring,
PUSH acknowledgment and wire EMPTY/error responses. The desktop virtual driver
can return C status directly; a physical SPI transaction cannot obtain those
outcomes from the documented byte envelope alone. A successful response handoff
does not prove master decoding or a remote RF acknowledgment. See the
[SPI protocol](../../docs/spi_protocol.adoc) and
[hardware preparation](../../docs/Hardware_Preparation.md).

The unchanged vendor `spiperipheral` and `rfPacketRx` examples provide separate
driver compile checks. Their launchpad SPI configuration and packet-receiver
RF profile are SDK examples, not verified Nova-Link wiring or a discovered
Multiverse PHY. The Nova image does not apply that RF profile. Real hardware
and independent captures remain necessary for physical SPI timing and
proprietary Multiverse interoperability.
