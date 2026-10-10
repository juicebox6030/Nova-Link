# Multiverse firmware analysis

Offline analysis of City Theatrical Multiverse firmware update packages,
performed to generate capture-verification hypotheses for the 2.4 GHz
interoperability work. Read [the findings document](../Multiverse_Firmware_Findings.md)
for the conclusions; this directory records provenance and raw extraction
artifacts.

Vendor firmware binaries are **not** checked into this repository: they are
proprietary City Theatrical material and this project only derives
interoperability facts from them. Download them from the vendor firmware page
(<https://www.citytheatrical.com/resources/firmware>) and verify the hashes
below before re-running any analysis.

## Packages analyzed (2026-10-10)

| File | SHA-256 |
| --- | --- |
| `5911-multiverse-transmitter-firmware-v2.2.0.9.0.6---current.zip` | `2f7bf5c1c384dfefc388d25ef0d929edafd1d37c32e96b4c9b757ea49d382de2` |
| `5900-firmware.zip` (Multiverse SHoW Baby v1.0.0.9.0.394) | `cf7b947b0f470deceab2952bf98c9576e7d3b759e3bd9eb09fd42e0fc5ac4d5d` |

## Contents

| Archive entry | SHA-256 | Identification |
| --- | --- | --- |
| `5911-v2.2.0.9.0.6-APP.bin` (215,488 B) | `edd48e512d1caf7b3e6224882ae15d9e8817456949d1f312cc9d85db4b7b89e4` | 5911 host MCU application, STM32F7 + FreeRTOS + lwIP, ARM Thumb-2, vector table at file offset 4 (SP `0x20020000`, reset `0x00229370`, ITCM alias) |
| `5911WA-v1.2.0.9.0.2-APP.bin` (775,364 B) | `3050500b4b0df75018cb39642eca91dd6225e6ad85f5ef7b199005d480d32b0f` | ESP32 (ESP-WROOM) WiFi coprocessor application, ESP-IDF |
| `5911WB-v1.2.0.9.0.2-APP.bin` (26,756 B) | `876bf8c8861eed37892b24dc2fe5480eb30a0a8baf282823d043f62d8078167a` | ESP32 second-stage bootloader (OTA/partition aware) |
| `5911WP-v1.2.0.9.0.2-APP.bin` (3,076 B) | `2a7d0b128f591ce38dc0aa8e88bedad39661d3b1d19dcdab3894284231490c16` | ESP32 partition table (+ `phy_init` reference) |
| `5995-v0.2.0.9.0.43-APP.bin` (106,240 B) | `99a44d3fee34c3d578a8dc72c04d121065a7e96d7841f3419d38f2ef4d921a6e` | 5911-bundled Multiverse radio module app (older build) |
| `5995-v1.0.0.9.0.177-APP.bin` (106,240 B) | `3edeb2c8784bf9f2b4e69734cc8690837495d415320c282f18e958b32834001d` | Multiverse radio module app, self-identifies `Multiverse 2.4GHz`, `Dtrunk@5429 (WC 5429) for mv5994`, 1.0.0.9.0.177, built Feb 18 2021 by pkleissler |
| `5900-v1.0.0.9.0.394-APP.hex` | `5bdc644e406ae6db55479c9a06170677d55a2547d8ca274b2d7ba3ab06ab17d8` | Multiverse SHoW Baby host app, MIPS32 (PIC32MX-class: program flash `0x1D000000`/`0x1D010000`, boot/config flash `0x1FC00000`) |

Both products share the same radio module family (`mv5994`/`5995`): the
Multiverse Transmitters host it as "Radio A" (2.4 GHz) with a second "Radio B"
(900 MHz) module on the 5911, and the Multiverse SHoW Baby (5900) uses it as a
receiver. The 5995 application is an ARM Cortex-M image for a TI wireless MCU
(RF Core doorbell/RAT/CPE driver strings, APB register `0x400100xx`).

## Update path

Firmware updates are delivered over the network: the 5911 host app embeds a
TFTP server and the MvTxUpdater tool pushes the `*-APP.bin` files by IP. This
means an MvTxUpdater session on the bench can capture a full radio image
(including flash regions the website zips omit — see the findings document,
"Radio image layout").

## Artifacts in this directory

- `5995-v1.0.0.9.0.177-strings.txt` — complete `strings` inventory (>= 6
  printable chars) of the Multiverse 2.4 GHz radio application.
- `5911-v2.2.0.9.0.6-strings.txt` — same for the 5911 STM32 host application.

These text dumps are kept because the radio build ships unusually verbose
debug/formatter strings that pin down protocol vocabulary (hop specs,
band names, RF test modes, bootloader, reliable messaging, MSP SPI host
interface). All disassembly-derived constants quoted in the findings document
come from the hashed binaries above and are reproducible with the offsets
listed there.
