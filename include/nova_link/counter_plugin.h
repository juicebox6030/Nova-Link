#ifndef NOVA_LINK_COUNTER_PLUGIN_H
#define NOVA_LINK_COUNTER_PLUGIN_H
#include "nova_link/module.h"

/** @file counter_plugin.h Minimal compiled application plugin example. */
typedef struct {
    bool transmitter;
    uint8_t zone;
    uint32_t next_value;
    uint32_t last_value;
    unsigned deliveries;
    nl_status last_status;
    nl_module_zone module_zone; /**< Constructor-owned declarative claim. */
} nl_counter_context;

/** Four-byte big-endian payload; context stays alive until unregister. */
nl_plugin nl_counter_plugin(nl_counter_context *context);
/** Construct before registration after setting the context. Default name counter;
 * requires radio-link. Edit returned descriptor's name
 * and requires list for another instance/provider before registering it.
 */
nl_module nl_counter_module(nl_counter_context *context);
#endif
