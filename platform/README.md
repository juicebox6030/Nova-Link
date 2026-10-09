# Platform integration boundary

The portable core does not configure a board, radio, network, or gateway. Hardware
adapters must provide stable state storage, synchronization, clocks, SPI/GPIO
drivers, and RF submission/completion. No packet captures or physical-link tests
are part of the software simulation.

## ESP32-S3

An ESP-IDF component definition is supplied in `platform/esp32/`. Add that directory
to the firmware project's `EXTRA_COMPONENT_DIRS` before including ESP-IDF's
`project.cmake`, then link/use the component from your application. This definition
compiles the C core only; it supplies no pin mappings, SPI setup, tasks, Wi-Fi/BLE
configuration, flash settings, or radio firmware.

Keep `nl_host` in persistent application storage. Implement its send callback
using the project's SPI master driver, and decode incoming `D0` frames through
`nl_host_receive_frame()`. Handle INT_READY in the board layer, posting work from
an ISR to the owning event loop/task. The core is not ISR-safe or thread-safe.
The ESP-IDF component has not been compiled with the vendor SDK in this workspace.

## TI CC1352R

Compile the relevant `src/*.c` files with C99 support and add `include/` to the SDK
project's include path. A radio-only image needs status, fragment, transport,
stream, queue, scheduler, and radio modules; host/zones are optional.

Use vendor SPI slave/GPIO drivers around the framing parser and PUSH/PULL
dispatcher. Drive RF operations from scheduled windows and call
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

Resolve response layouts for PING/STATUS, empty PULL and failed PUSH behavior,
SPI chip-select/framing/timeout rules, and remote active-zone configuration.
These are software design decisions that can be reviewed without hardware.
See [protocol decisions](../docs/Protocol_Decisions.md) and the
[roadmap](../docs/Development_Roadmap.md) for the remaining work.
