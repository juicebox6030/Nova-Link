# NOVA-LINK OSI responsibility mapping

This mapping describes design responsibilities, rather than claiming a complete
implementation of seven standardized network layers. There is no implemented
mesh or routing protocol.

| Layer | Responsibility | Intended device / portable module |
|---|---|---|
| 1 — PHY | Modulation, channel selection, CRC, physical TX/RX | CC1352R board adapter (pending) |
| 2 — Link | Fragment header, sequence and duplicate-band handling | Shared `fragment.c`, `stream.c`, radio adapter |
| 3 — Scheduling | Active-zone rotation and management slot selection | CC1352R `scheduler.c`, `radio.c` |
| 4 — Delivery | Bounded buffers and stale/duplicate rejection | Radio and host `queue.c`, `stream.c` |
| 5 — Session | Plugin lifecycle and local zone ownership | ESP32-S3 `host.c`, `zones.c` |
| 6 — Presentation | Application payload codecs and any reassembly | Plugin-defined; example `plugins/counter.c` |
| 7 — Application | Plugin event hooks and send/receive API | ESP32-S3 `host.c` |

SPI/UART framing is a host/co-processor adapter boundary, implemented independently
of PHY and application payload encoding. Remote session establishment, clock
synchronization, RF drivers, and distributed zone discovery remain pending.
