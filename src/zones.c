#include <stddef.h>
#include "nova_link/zones.h"

static uint16_t plugin_bit(uint8_t plugin)
{
    return (uint16_t)(1u << plugin);
}

void nl_zones_init(nl_zone_table *table)
{
    size_t zone;
    if (table == NULL) return;
    for (zone = 0; zone < 8u; ++zone) {
        table->claims[zone].readers = 0;
        table->claims[zone].owner = NL_PLUGIN_NONE;
    }
}

nl_status nl_zones_claim(nl_zone_table *table, uint8_t plugin, uint8_t zone, nl_zone_mode mode)
{
    nl_zone_claim *claim;
    uint16_t bit;
    if (table == NULL || plugin >= NL_PLUGIN_MAX || zone >= 8u ||
        (mode != NL_ZONE_READ_ONLY && mode != NL_ZONE_EXCLUSIVE)) return NL_ERR_ARGUMENT;
    if (zone == 0u) return NL_ERR_ACCESS;
    claim = &table->claims[zone];
    bit = plugin_bit(plugin);
    if (claim->owner != NL_PLUGIN_NONE && claim->owner != plugin) return NL_ERR_CONFLICT;
    if (mode == NL_ZONE_EXCLUSIVE && (claim->readers & (uint16_t)~bit) != 0u)
        return NL_ERR_CONFLICT;
    claim->readers |= bit;
    claim->owner = mode == NL_ZONE_EXCLUSIVE ? plugin : NL_PLUGIN_NONE;
    return NL_OK;
}

nl_status nl_zones_release(nl_zone_table *table, uint8_t plugin, uint8_t zone)
{
    nl_zone_claim *claim;
    uint16_t bit;
    if (table == NULL || plugin >= NL_PLUGIN_MAX || zone >= 8u) return NL_ERR_ARGUMENT;
    if (zone == 0u) return NL_ERR_ACCESS;
    claim = &table->claims[zone];
    bit = plugin_bit(plugin);
    if ((claim->readers & bit) == 0u) return NL_ERR_NOT_FOUND;
    claim->readers &= (uint16_t)~bit;
    if (claim->owner == plugin) claim->owner = NL_PLUGIN_NONE;
    return NL_OK;
}

void nl_zones_release_plugin(nl_zone_table *table, uint8_t plugin)
{
    uint8_t zone;
    if (table == NULL || plugin >= NL_PLUGIN_MAX) return;
    for (zone = 1; zone < 8u; ++zone) (void)nl_zones_release(table, plugin, zone);
}

bool nl_zones_can_read(const nl_zone_table *table, uint8_t plugin, uint8_t zone)
{
    if (table == NULL || plugin >= NL_PLUGIN_MAX || zone >= 8u) return false;
    return zone == 0u || (table->claims[zone].readers & plugin_bit(plugin)) != 0u;
}

bool nl_zones_can_write(const nl_zone_table *table, uint8_t plugin, uint8_t zone)
{
    if (table == NULL || plugin >= NL_PLUGIN_MAX || zone >= 8u) return false;
    return zone == 0u || table->claims[zone].owner == plugin;
}

uint8_t nl_zones_active_mask(const nl_zone_table *table)
{
    uint8_t zone, mask = 0;
    if (table == NULL) return 0;
    for (zone = 1; zone < 8u; ++zone)
        if (table->claims[zone].readers != 0u) mask |= (uint8_t)(1u << zone);
    return mask;
}
