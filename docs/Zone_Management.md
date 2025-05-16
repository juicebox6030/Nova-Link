# Zone Management

## Zone IDs

- Zone 0 = Metadata (cannot be claimed)
- Zones 1–7 = User zones
- Zone frequency pairs are defined via a frequency table. This table should also store zone priorities. 

## Rules

- If claimed exclusively, other plugins are blocked
- Violations generate warning logs

## Ownership Table

Tracked internally with plugin ID → zone claim map. The zone claim map should be distributed to other subscribing devices to avoid plugins reciving invalid payloads. 

# Metadata Handling (Zone 0)

## Special Case

- Only active upon data being pushed into the Zone 0 buffer. 
- Zone 0 cannot be claimed; these frequencys are fixed in the table. These frequencys will only change based on preset "Galexys"(future feature)
- Used for plugin coordination, debug, control, congestion alerts, pairing, and device discovery.
