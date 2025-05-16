# Plugin API Specification

## Required Plugin Functions

- `plugin_init()` — Called on startup.
- `plugin_on_data(zoneID, data)` — Called when data is received.
- `plugin_get_payload(zoneID)` — Called when core polls for data.

## SDK Calls for Plugins

- `plugin_send_payload(zoneID, data, burst=False)`
- `plugin_claim_zone(zoneID, exclusive=False)`
- `plugin_release_zone(zoneID)`

## Access Rules

- Zone 0 (metadata) is always accessible.
- Other zones require claim.
- Violation triggers warning.

