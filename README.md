# NOVA-LINK

**NOVA-LINK** is an open, low-latency wireless communication protocol and firmware stack designed for use in real-time live event environments.

This SDK is the official implementation, targeting **ESP32**, with the **TI CC1352R** for the **NOVA-LINK Wireless stack**. The goal is a modular, efficient, low latency wireless stack that can be accept whatever payload is required. The goal is there is an SDK that a plugin based system can interact with the **NOVA-LINK** Wireless stack.

---

This SDK is the official implementation, targeting **ESP32**, with the **TI CC1352R** for the **NOVA-LINK** Wireless stack. The goal is a  modular, efficient, low latency wireless stack that can be accept whatever payload is required. The goal is there is an SDK that a plugin based system can interact with the **NOVA-LINK** Wireless stack.

## 🔧 System Overview

NOVA-LINK provides a dual-band (Sub-GHz + 2.4GHz) wireless backbone to reliably transport payloads like:

- DMX & RDM
- Audio Streams
- OSC and other control protocols
- Synchronization and Metadata messaging

---

## 💡 Core Design Goals

- **Low latency**: Sub-5ms multi-packet delivery
- **Dual-band redundancy** (900 MHz + 2.4 GHz) / Zone
- **Modular architecture** by OSI layer and device
- **Open-source, plugin-based design**
- **Deterministic performance**, no mesh delay
- **Fixed-size packets**, optional burst grouping
- **Plugin ownership model**, with strict access control
- **Fully documented** using Doxygen
- **IEEE 802.15.4** Using 802.15.4 for the base wirelss stack.
- **Co-Processor Model** Split brain logic to reduce workload and increase ease of use. ESP-32 is used for WIFI/BLE and plugin processing, the TI CC1352R will be used for sending the 802.15.4 fragment and deduplication.
  
---

## 📶 Protocol Highlights

- **8 Zones Total**:
  - Zone 0 reserved for Metadata
  - Zones 1–7 available for data payloads
- **100-byte max payload**
  - Fragments longer messages across multiple packets
  - Plugins strongly encouraged to avoid fragmentation
- **DataFragment Format**:
  ```
  [addr_flags][seqNum][payload...]
  ```
  - `addr_flags`: [2-bit originID | 3-bit zoneID | 3-bit flags]
  - `seqNum`: 8-bit packet sequence number
  - `payload`: up to 100 bytes

- **SPI/UART Transport**:
  - Fragments are built entirely on the ESP and sent to the CC1352R
  - `SYNC` (`0xAA`) + `LEN` framing protocol

---

## 🧱 OSI Layer Breakdown

| Layer | Role |
|-------|------|
| **L1** | Sub-GHz + 2.4GHz RF PHY (CC1352R) |
| **L2** | Fragment header encoding, dual-band transport |
| **L3** | Zone scan scheduling, metadata cycle injection |
| **L4** | RX buffering, burst tracking, deduplication |
| **L5** | Plugin session manager, zone claiming, access control |
| **L6** | Plugin-defined payload encoding/decoding |
| **L7** | Plugin runtime API, hooks, and message handling |

---

## 📦 Plugin Model

Plugins run on the **ESP host**, and must claim zones before use (except for zone 0).

Zones can be set to exclusive or read only.

Plugins have full control of payload.

Plugins can push data to the metadata buffer and the api will add it to the RF cycle as it will fit. 

Metadata is treated as any other zone, using `zoneID = 0`, and is globally readable/writable.

Metadata zone is a non-time sensitive zone. All other zones will get priority over this. Therfore, it is not a reliable way to transmit important data.

---

## 📂 Project Layout

| Folder     | Purpose                                  |
|------------|-------------------------------------------|
| `src/`     | Core protocol code, fragment logic, etc. |
| `include/` | Public headers for external integration  |
| `platform/`| Board-specific code (e.g., CC1352R setup)|
| `plugins/` | Modular plugin handlers                  |
| `tools/`   | Flashing, debugging, logging utilities   |
| `tests/`   | Unit tests and simulation harness        |
| `docs/`    | Markdown + Doxygen-generated docs        |
| `config/`  | Plugin mappings, filter rules, flags     |

---

## 🚧 Development Status

NOVA-LINK is in **active development**, with planning completed for all OSI layers and subsystem responsibilities. 

To contribute, follow the upcoming [Development Roadmap](#) (coming soon).

---

## 📜 License

[GPL-3.0](LICENSE) — Open-source, share-alike. See `LICENSE` file for details.

---

## 🧠 Credits

Designed by [Brent Scoggins](https://github.com/Juicebox6030)  

Luminary Technology and Productions (https://LuminaryTechnology.productions) 

AI Assisted ; I am not a software dev, just highly motivated!

---

## ✨ Goals for v1.0

- [ ] Dual-band TX/RX engine (ESP ↔ CC1352R)
- [ ] Fragment serialization & SPI framing
- [ ] Burst-mode handling + stream deduplication
- [ ] Metadata management channel (Zone 0)
- [ ] Plugin lifecycle hooks
- [ ] Plugin loader + runtime isolation
