# NOVA-LINK

**NOVA-LINK** is an open, low-latency wireless communication protocol and firmware stack designed for use in real-time live event environments.

This SDK is the official implementation, targeting **ESP32**, with the **TI CC1352R** for the **NOVA-LINK Wireless stack**. The goal is a modular, efficient, low latency wireless stack that can be accept whatever payload is required.

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
  - `addr_flags`: [3-bit originID | 3-bit zoneID | 2-bit flags]
  - `seqNum`: 8-bit packet sequence number
  - `payload`: up to 100 bytes

- **SPI/UART Transport**:
  - Fragments are built entirely on the ESP and sent to the CC1352R
  - `SYNC` (`0xAA`) + `CMD` + `LEN` + data + CRC-8 framing

Byte-level details of everything on the air and on the link are in
[docs/wire_format.adoc](docs/wire_format.adoc).

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
| `src/`     | Portable C99 core (host + radio), no hardware access |
| `include/` | Public headers (`include/nova_link/`)    |
| `platform/`| Board-specific code (ESP32, CC1352R) — not started |
| `plugins/` | Modular plugin handlers — not started    |
| `sim/`     | Multi-device network simulator           |
| `tests/`   | C unit tests and shared byte vectors     |
| `tools/`   | Python decoder, airtime calculator, `novalink` package |
| `docs/`    | Design notes, wire format, simulation results |
| `config/`  | Default settings (`nova_link.ini`)       |
| `.github/` | CI: build + tests (gcc, clang, UBSan), Python tests, Doxygen |

---

## 🛠️ Building and Testing

The portable core, unit tests and simulator build on any desktop with a C99
compiler and CMake:

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j
ctest --test-dir build --output-on-failure
```

Other useful commands:

```sh
# Network simulator (see docs/simulation.adoc)
./build/sim/nl_sim --nodes 4 --runs 4

# Python tools and their tests
python3 -m unittest discover -s tools/tests -t tools
python3 tools/nl_decode.py --help

# API documentation (output in build/doxygen/html)
doxygen Doxyfile

# Regenerate the shared test vectors after a wire format change
./build/tests/gen_vectors --out tests/vectors
```

---

## 🚧 Development Status

NOVA-LINK is in **active development**. The portable core (fragments,
zones, metadata, stream tracking, segmentation, link framing, host and radio
logic) is implemented and tested on the desktop and in simulation. The
ESP32 and CC1352R platform layers, and testing on real radios, are next.

See the [Development Roadmap](docs/Development_Roadmap.md),
[wire formats](docs/wire_format.adoc) and
[simulation results](docs/simulation.adoc).

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
