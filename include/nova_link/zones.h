#ifndef NOVA_LINK_ZONES_H
#define NOVA_LINK_ZONES_H

#include <stdbool.h>
#include <stdint.h>
#include "nova_link/status.h"

/** @file zones.h Cooperative plugin ownership; zone 0 is shared and cannot be claimed. */
#define NL_PLUGIN_MAX 16u
#define NL_PLUGIN_NONE 255u
typedef enum { NL_ZONE_READ_ONLY, NL_ZONE_EXCLUSIVE } nl_zone_mode;
typedef struct {
    uint16_t readers;
    uint8_t owner;
} nl_zone_claim;
typedef struct { nl_zone_claim claims[8]; } nl_zone_table;

void nl_zones_init(nl_zone_table *table);
/** Claims are idempotent. Upgrades succeed only when no other plugin reads the zone. */
nl_status nl_zones_claim(nl_zone_table *table, uint8_t plugin, uint8_t zone, nl_zone_mode mode);
nl_status nl_zones_release(nl_zone_table *table, uint8_t plugin, uint8_t zone);
void nl_zones_release_plugin(nl_zone_table *table, uint8_t plugin);
bool nl_zones_can_read(const nl_zone_table *table, uint8_t plugin, uint8_t zone);
bool nl_zones_can_write(const nl_zone_table *table, uint8_t plugin, uint8_t zone);
/** Return data-zone interest as a bit mask; bit 0 is always clear. */
uint8_t nl_zones_active_mask(const nl_zone_table *table);

#endif
