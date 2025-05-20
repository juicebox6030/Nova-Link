# NOVA-LINK System Architecture

## Components

- **ESP32 API**: Hosts plugins, manages packet creation and SPI communication. Provides User connectivity via BLE and WIFI
- **TI CC1352R**: Handles radio transmission, deduplication, timing.
- **Plugin System**: Interface for applications to send/receive wireless payloads.
- **Zone Manager**: Tracks ownership and validity of communication zones.

## Data Flow
**TX**
[ Plugin ] 
    ↓
[ NOVA API ]
    ↓
[ SPI ]
    ↓
[ CC1352R Nova-Link Stack ]
    ↓
[ RF Transmission ]

**RX**
[ RF Transmission ] 
    ↓
[ CC1352R Nova-Link Stack ]
    ↓
[ SPI ]
    ↓
[ NOVA API ]
    ↓
[ Plugin ]

RF Scheduler cycles through zones based on zone priority. The RF Scheduler excludes non-registered zones and zone 0, unless the Managment flag is raised, then it will be added to the que with a low priority. 

The CC1352R is quick to switch between tx, rx, and differnet frequencys. Though it is quick, having all 8 zones send and receive at the same time can cause some latency, as the airtime of the packets will add up. 4 full zones (full payload, TX or RX) and zone 0 is the max reccomened to acheive minimal latency. 

