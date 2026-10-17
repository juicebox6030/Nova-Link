# Design decisions

This index preserves decisions that otherwise get lost between implementation threads. The native protocol decision table is maintained in [docs/Protocol_Decisions.md](docs/Protocol_Decisions.md); its rows are the authority for **Header allocation**, **Fragment size**, **Transport envelope**, **Empty request**, **Direction**, **PING/STATUS responses**, **Empty PULL / PUSH acknowledgment**, **Zone ownership**, **Zone 0**, **Fragmentation**, **Scheduling**, **BURST**, **MGMT_LISTEN**, and **PHY**. The table also contains the **Golden vector** and stream/session rules. These are not duplicated here.

Status values: `decided`, `verified-on-hardware`, `verified-in-emulation`, `open`.

| ID | Date | Decision | Rationale | Source | Status |
|---|---|---|---|---|---|
| NL-BOARD-001 | 2026-10-17 | Deployment board products, revisions, and pin assignments are not established. Do not treat the TI vendor compile target as a deployment wiring record. | The repository explicitly says actual board/revision/pin mappings remain to be recorded; compile checks do not establish wiring. | [docs/Hardware_Preparation.md](docs/Hardware_Preparation.md); [platform/cc1352r/README.md](platform/cc1352r/README.md) | open |
| NL-BOARD-002 | 2026-10-17 | GPIO18/19 were proposed for ESP32-C6 to CC1352R1 wiring in a thread, but no confirmation or complete signal mapping is preserved here. No physical pin assignment is adopted. | A proposal alone is insufficient to establish wiring; the board port and electrical behavior require confirmation. | Thread `501c0fb8` (ESP32 and CC1352R1 Pin Connections); `mcp:c8178ada` (ESP32-C6 platform port) | open |
| NL-BOARD-003 | 2026-10-17 | Use ESP32-C6 DevKit and TI LAUNCHXL-CC1352R1 as the boards under discussion for the ESP32-C6 port; this records thread context, not a deployment selection. | The user named these boards, while repo docs only identify the TI vendor compile configuration and ESP32-S3 reference target. | Thread `501c0fb8`; [docs/Hardware_Preparation.md](docs/Hardware_Preparation.md) | open |
| NL-MV-001 | 2026-10-17 | Multiverse PHY settings, over-air framing, hopping behavior, and interoperable pin/wiring remain unresolved for implementation purposes. Firmware-derived material is not an on-air confirmation. | The repo's bench plan expressly leaves these items unverified and requires capture/bench observations. | [docs/Multiverse_2_4GHz.md](docs/Multiverse_2_4GHz.md); [docs/Multiverse_Emulator.md](docs/Multiverse_Emulator.md); thread `2203da05` | open |

## Open questions

- Which exact development-board products and revisions are in use, and what reviewed pin mapping connects host and radio? See roadmap TODO [docs/Development_Roadmap.md](docs/Development_Roadmap.md#L115) and `NL-BOARD-001`/`NL-BOARD-002`.
- What is the verified physical SPI transaction, GPIO/interrupt mapping, and electrical timing?
- What Multiverse PHY, framing/integrity fields, hopping schedule, and control exchanges are confirmed by captures?
