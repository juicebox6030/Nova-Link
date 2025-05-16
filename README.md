# NOVA-LINK

**NOVA-LINK** is an open, low-latency wireless communication protocol and firmware stack designed for use in real-time live event environments.

This SDK is the official implementation, targeting **ESP32**, with the **TI CC1352R** for the **NOVA-LINK** Wireless stack. The goal is a  modular, efficient, low latency wireless stack that can be accept whatever payload is required. The goal is there is an SDK that a plugin based system can interact with the **NOVA-LINK** Wireless stack.

## 🔧 Features

- 🌀 **Multi-Zone Messaging** with burst-mode and optional metadata
- 📦 **Fragmented Payload Handling** for payloads >100 bytes
- 🚦 **Zone Claim System** for plugin isolation and access control
- 🔌 **Pluggable Plugin API** for RF modes, protocol behaviors, and processing
- 🧠 **Stream Tracking Layer** separates transport logic from plugin handling
- 🎛️ **API to CC1352R via SPI**, controlled by ESP host or similar
- 📝 **Fully documented** using Doxygen
- **IEEE 802.15.4** Using 802.15.4 for the base wirelss stack.
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