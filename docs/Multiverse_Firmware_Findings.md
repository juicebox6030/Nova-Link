# Multiverse 2.4 GHz firmware findings

Offline analysis of publicly downloadable City Theatrical firmware (5911
Multiverse Transmitter v2.2.0.9.0.6, Multiverse SHoW Baby 5900
v1.0.0.9.0.394, and the shared Multiverse radio module application
5995 v1.0.0.9.0.177) performed to turn the open questions in
[Multiverse_2_4GHz.md](Multiverse_2_4GHz.md) into testable hypotheses for
bench captures. Raw evidence and hashes: [firmware_analysis/](firmware_analysis/README.md).

Confidence labels used below:

- **Verified** — read directly from firmware strings/disassembly of the hashed
  binaries; describes what the firmware contains, not what the air waveform is.
- **Decoded** — control flow/data tables reverse-engineered from the binary;
  structure is solid, individual field semantics may need confirmation.
- **Inferred** — plausible reading that a capture must confirm.
- **Open** — not recoverable from these images; needs RF captures.

These are hypotheses about vendor firmware, not a license to transmit:
per [Multiverse_2_4GHz.md](Multiverse_2_4GHz.md), nothing is treated as
Multiverse-compatible until a receiver decodes it on the bench.

## 1. Product architecture (Verified)

Both targets are built around the same **Multiverse radio module**
(`mv5994`/`5995` family):

| Product | Host CPU | Radio(s) | Role |
| --- | --- | --- | --- |
| 5910/5911/5912 Multiverse Transmitter | STMicroelectronics **STM32F7** (Cortex-M7, FreeRTOS, lwIP; web UI, Art-Net, sACN, DMXcat protocol, TFTP update server) + **ESP32** WiFi coprocessor (`5911WA/WB/WP` = ESP-IDF app/bootloader/partition table v1.2.0.9.0.2) | "Radio A" = 5994/5995 2.4 GHz module; 5911 adds "Radio B" 900 MHz module (both over SPI, per-port attention line) | Transmitter/hub |
| 5900 Multiverse SHoW Baby | **PIC32MX** (MIPS32; program flash `0x1D000000`, config flash `0x1FC00000`), embedded web UI (`logo White.png` in image) | 5994/5995 module | Receiver/node ("DMX Output Port", Rx signal quality/strength telemetry) |

The 5995 application is an ARM Cortex-M image for a **TI SimpleLink-class
wireless MCU** (RF Core doorbell `RFC_DBELL`/`CMDR`, RAT timer, CPE
command engine, DIO naming). This is encouraging for the CC1352R plan: the
vendor's own radio is a close architectural cousin of the bench radio.

Radio app build stamp: `Dtrunk@5429 (WC 5429) for mv5994`,
`1.0.0.9.0.177`, "Multiverse 2.4GHz", City Theatrical Inc.

## 2. PHY characteristics (Verified strings, Open waveform)

From the radio's RF test/config menus and driver:

| Item | Finding |
| --- | --- |
| Modulation/rate classes | `1Mbps FSK Neo` (base SHoW DMX Neo), `1Mbps BLE`, `2Mbps GFSK`, `5Mbps 8FSK`. Multiverse's multi-universe capacity evidently rides on higher-rate modes. |
| Frequency range | Test UI enforces `2400.0 <= F <= 2483.5` (MHz). |
| Band presets | `full band`, `low band`, `high band`, `very high band`, `avoiding lower 20MHz`, `avoiding upper 20MHz` — the classic SHoW band selections, present as first-class strings. |
| Whitening | On/off option (`whiten: %s`, continuous-Tx test), `PRBS-15`/`PRBS-32` test payloads, 16-bit configurable "test word". |
| TX power | Settable in dB steps (`Tx power (%u = %02.1g dB)`), optional external RF amp `bypassed`/`normal`, antenna selection `internal (PCB)`/`override`. |
| Adaptive hopping | Present ("NEO_AH_IS_ON", per-hop 64-bit mask printed as `%016b`, `Adaptive inactive`) — the radio maintains an avoided-channel bitmap per hop slot. |
| Deviation, bandwidth, preamble, sync word, CRC config | Open — encoded inside TI RF command structures; recover from SmartRF-style register dumps or captures, not from these strings. |

## 3. SHoW ID and hop spec (Decoded)

The radio distinguishes legacy "Neo" SHoW IDs from Multiverse IDs. A decoded
builder routine (`rfhops.c` region) expands a SHoW ID into a hop channel list:

- **IDs 1–100** — legacy Neo shows; a helper notes certain commands are valid
  `in neo showIDs only`.
- **IDs 101–164** (`0x65`–`0xA4`) — **Multiverse range**, processed in four
  groups of 16: `g = (id - 101) >> 4`, parity bit `p = (id - 101) & 1`.
- **IDs 165/166** — fixed 5-channel Neo-style lists (stored ASCII-obfuscated
  as `JHPNL` / `IGMOK`).
- SHoW **Key** is a separate 0–500 value (both host apps label it
  `SHoW Key (0-500)`).

Hop pool construction (Decoded; field semantics Inferred):

```text
step[] = {36,18,12, 9,22, 6,21,23, 4,11,10, 3,17,29,32,30,
          13, 2,35,24, 7, 5, 8,20,34,27,26,33,14,16,31,15,
          28,25,19, 1}              # fixed 36-entry permutation, 1..36
lo, hi = band_bounds[g]             # per-group bytes from a 16-byte-strided table
for i in 0..35:                     # 36 attempts, modulo-37 generator
    pos  = (n * step[i] + step[i]) mod 37 - 1     # n = per-context byte
    if lo <= pos < hi:
        channel = (pos + 2) * 2 + p               # even/odd offset by ID parity
```

Decoded band bounds in the 2.4 GHz image:

| Group (IDs) | `lo` | `hi` | Pool size | Reading (Inferred) |
| --- | --- | --- | --- | --- |
| 101–116 | 0 | 36 | 36 | `full band`: 36 even channels |
| 117–132 | 17 | 4 | 0 | unused/other-band in this build |
| 133–148 | 14 | 34 | 20 | 20-channel sub-band (e.g. `high band`) |
| 149–164 | 79 | 76 | 0 | unused/other-band in this build |

Empty groups most likely belong to band presets served by other radio builds
(900 MHz, or additional 2.4 GHz presets in the transmitter's Radio B image).

Channel numbering is `channel ≈ (2400 + ch) MHz` on a grid where even/odd
classes are offset by 1 MHz — consistent with `Hop on %u channels: low %.6g
MHz, high %.6g MHz, separation %.6g MHz` and with the pool landing inside the
2.4 GHz ISM block. **Capture must confirm the scale and spacing.**

Also decoded:

- A **hop order repair** routine validates the active list against a
  20-entry window (`i mod 20`) and fixes deviations — i.e. hop cycles of up
  to 20 effective channels are expected to repeat exactly.
- A **shuffle** routine permutes the 36-entry array with paired counters
  (outer 36, inner 10) — order randomization between shows.
- Two legacy lists ship in the image: 36 odd channels (7–77 odd) and a
  20-entry mixed list — matching older Neo band definitions.
- The per-context multiplier `n` above is the most likely place the **SHoW
  Key** (0–500) enters the hop order (different keys → different orders).
  Confirm by keying two transmitters with the same ID and different keys on
  the bench and comparing occupied sequences.

## 4. Data transport model (Verified strings)

- **Hub/node architecture** with dynamic discovery: 6-byte UIDs, automatic
  `shortId` assignment (`MSP_NODE_ASSIGN_ID_LEN`), node-lost notifications
  (`MSP_NODE_LOST_LEN`), group assignment.
- **Block packets** with partial-packet statistics: Rx counters track
  `total good part bad missed remade blk-recovery loss` — block payloads are
  recoverable from fragments (FEC-like), matching the transmitter's
  `Forward Error Correction (Tx)` option.
- **Reliable messaging** alongside DMX data: downstream/upstream reliable
  PDUs (`RFP_DSREL_HDRLEN`, `RFP_USREL_HDRLEN`) with XID-based ACK/NAK
  (`ACK%u,%u,%d,%u`, `RelAck XID mismatch`), used for mRDM and control.
- **mRDM** over the air: discovery mute/unmute callbacks, device list with
  binding (`bindId`), proxied-device enhancement
  (`CTI_PROXIED_DEVICES_ENHANCED`), TTL-tagged forwarded messages.
- **Slot-array packing** (`saPackSlotPdus`) — DMX levels are packed into
  radio slots per universe; a packet need not carry a whole universe verbatim
  (consistent with the existing docs).
- **`mDMX (Tx Only)`** and **encoding** options (`encoding %i, %u bytes max
  every %u`) — rate/threshold presets per show.
- **OTA bootloader** with ACKed image transfer (`BL initiate`, `BL data %d,
  retry`, `Going to bootloader mode!`) — also a bench window into radio
  internals via the host's "bootload" debug menu.

## 5. Host↔radio interface (Verified) — directly relevant to NovaLink

The host MCU drives the radio module over **SPI with an attention line**
(`DIO_SPI_nCS`), a command set named **MSC/MSP** (`Multiverse...` messages),
and per-radio multiplexing `M:%c` with ports `MV_A`/`MV_B`:

- Host commands observed: get/set SHoW ID, set SHoW Key (`mvApp: Set SHoW ID
  M:%c %d`), radio debug terminal pass-through (`mv: MV:%c Setting radio
  debug terminal`), `RFconfig`, `pushMenu`, `getCmdstaName`.
- Radio → host async events: node discovered (UID + attempts), shortId
  assigned, node lost/relocated, reliable msg received, reliable msg result
  (`ack, node, xid`), DMX/I2C content ID messages, "Unknown SPI Attention!
  M:%c CMD:%02x len:%d".
- The 5911 host also keeps per-radio boot counters and RDM contexts.

For NovaLink this validates the chosen ESP32-S3 + CC1352R split and the
existing async SPI boundary design: the vendor stacks do exactly
"application CPU ⇄ SPI ⇄ radio CPU with attention IRQ", including
OTA-bootloader handshakes (`0123blRdy`, `blStartDone`, `blDataDone`).

## 6. Bench-accessible debug terminal (Verified — operationally useful)

The radio module exposes a serial debug menu with RF introspection that will
make captures far easier to correlate:

- `RFconfig`, `show` (`showID %u (%s, %u hop channels, show key %u)`,
  `encoding %i`, `%u bytes max every %u`), hop spec printout with per-channel
  `order [%2u`, `iHop %2u, map` adaptive maps, `Tx cont`/`Tx pkts` tests,
  stats (`good packets`, `hop cycle`, `poll cycle`, heap views).
- Menu navigation strings (`Main menu:`, `Radio cfg:`, `Bl test menu:`)
  reveal the full command surface without needing the physical product UI.

If a spare radio module can be probed on the bench, its debug UART + this
menu can print the live hop sequence and adaptive masks next to an SDR
capture — the fastest way to confirm Section 3's algorithm.

## 7. Radio image layout (Verified, reproducibility notes)

The website `APP.bin` is a partial flash image; address references resolve
with a **+0x6000 offset for the final rodata chunk**:

- Code + vector table: flash `0x00000`–`0x14FFF` ≈ file `0x00000`–`0x14FFF`.
- Strings/config tables: file `0x15000`–`0x19F00` → flash `0x1B000`–`0x1FF00`
  (the image ends exactly at the 128 KB flash boundary, e.g. table base
  `0x1EF03`, string `JHPNLIGMOK` at `0x1EF4C`, legacy lists at `0x1EF56`).
- The middle region `0x15000`–`0x1B000` is not in the website package; a
  full flash dump (TFTP update session or chip read) would close remaining
  gaps (exact RF command structs, packet framing constants).

Key offsets for reproduction (5995 v1.0.0.9.0.177):

| Item | Flash address |
| --- | --- |
| `showID %u (%s...` formatter call site | `0x1490` |
| Hop list builder | `0x98E8` |
| Hop order repair (mod-20) | `0x9830` |
| Shuffle routine | `0x970C` |
| Permutation `step[36]` | `0x1EF28` (`0x1EF03 + 0x25`) |
| Band bounds (4×16 B groups) | `0x1EF20`–`0x1EF4B` (`lo` at `+0x21+16g`, `hi` at `+0x1D+16g`) |
| Legacy 36-odd / 20-entry lists | `0x1EF56` / `0x1EF7A` |

## 8. What this changes for the NovaLink plan

Feeds the open items in [Multiverse_2_4GHz.md](Multiverse_2_4GHz.md) and the
[roadmap](Development_Roadmap.md):

1. **Candidate PHYs for SmartRF exports** (in priority order): 1 Mbps 2-FSK,
   2 Mbps GFSK, 5 Mbps 8-FSK; expect whitening enabled; expect a short
   configurable sync word; channel grid even/odd 1 MHz-offset within
   2404–2477 MHz (confirm).
2. **Capture matrix gains controls**: repeat a show at SHoW IDs 101/102
   (parity pair, same group), 101 vs 133 (band pair), same ID different SHoW
   Key (hop-order divergence through `n`), and adaptive hopping on/off.
3. **Packet expectations**: look for block-structured DMX payloads with
   fragment/recovery fields (not raw universes), interleaved reliable control
   PDUs, discovery/shortId exchanges on join, and exact 20-hop cycle
   repetition.
4. **Decode targets** for the capture analyzer: slot-packed level arrays,
   `remade`/`blk-recovery` implies redundancy fields exist even without the
   exact FEC scheme.

## 9. Remaining unknowns (Open — capture required)

- Exact RF command parameters (deviation, RX bandwidth, preamble/sync words,
  CRC length/polynomial as transmitted, whitening polynomial/state).
- On-air packet framing: sync word values, length encoding, addressing,
  block/recovery header layouts, `RFP_BLK_PYLD_LEN`.
- Hop timing (dwell/hop period), beacon/join scheduling, poll cycle period.
- Whether real deployments use the BLE mode (config transport?) and how
  mRDM shares time with DMX blocks.
- SHoW Key derivation role (Section 3 hypothesis), and the exact mapping of
  the empty ID groups (117–132, 149–164) for this 2.4 GHz build.
- 900 MHz Radio B protocol (separate image, not in these packages).
