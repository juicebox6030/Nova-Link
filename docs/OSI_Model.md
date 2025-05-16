# NOVA-LINK OSI Layer Mapping

## Overview

NOVA-LINK maps traditional OSI layers to embedded device boundaries for clarity and modularity.

### Layer Map

| OSI Layer | Function                          | Device          | Module/File          |
|-----------|-----------------------------------|------------------|----------------------|
| 1 - PHY   | Sub-1 GHz RF                      | CC1352R          | RF Stack             |
| 2 - MAC   | Mesh Networking + Deduplication   | CC1352R          | Radio Core           |
| 3 - Transport | SPI, fragmentation, seqNum   | ESP32 + CC1352R  | plugin_send_payload  |
| 4 - Session | Zone tracking, burst handling | ESP32            | Zone Manager         |
| 5 - Plugin | Logic, packet creation/parse    | ESP32            | SDK Plugin API       |

