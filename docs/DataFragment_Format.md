# DataFragment Format

## Header (1 byte)

- Bits 7-5: originID (0–7)
- Bits 4-2: zoneID (0–7)
- Bits 1-0: flags (see below)

## Fields

| Field      | Size     | Description                      |
|------------|----------|----------------------------------|
| Header     | 1 byte   | Encodes origin, zone, and flags  |
| seqNum     | 1 byte   | Fragment deduplication number    |
| payloadLen | optional | Length of payload (impl-defined) |
| payload    | ≤100 B   | Data sent by plugin              |

## Flags

- Bit 0 – `MGMT_LISTEN`
- Bit 1 – `BURST`
- Bits 2–3 – Reserved for plugins

