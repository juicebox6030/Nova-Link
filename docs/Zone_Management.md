# Zone Management

`nl_zone_table` implements local ownership for zones 1–7. An exclusive owner can
read and write; multiple read-only subscribers can share an otherwise unowned
zone. Exclusive claims conflict with any other subscriber. Repeating a claim is
safe; an exclusive owner may explicitly downgrade to read-only. Release/unregister
clears interest, and `nl_zones_active_mask()` supplies the data-zone subscription
mask for a local radio configuration.

Zone 0 is shared metadata. All active plugins may read/write it, and it cannot be
claimed. Pending TX or a management-listen request schedules a metadata slot
following a data round; with no active data zones it may run alone. Metadata
shares ordinary bounded queues and carries no stronger delivery guarantee.

The host logs access violations through an optional structured callback. Plugin
IDs and claims are cooperative checks for trusted compiled code, not security
credentials. A remote claim-distribution protocol, frequency/priority table, and
future galaxy profiles are not implemented. See
[protocol decisions](Protocol_Decisions.md) for current scheduling semantics.
