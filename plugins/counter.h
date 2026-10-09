#ifndef NOVA_COUNTER_PLUGIN_H
#define NOVA_COUNTER_PLUGIN_H
#include "nova_link/host.h"

/** Example application codec: a four-byte, big-endian unsigned counter. */
typedef struct {
    bool transmitter;
    uint8_t zone;
    uint32_t next_value;
    uint32_t last_value;
    unsigned deliveries;
    nl_status last_status;
} nl_counter_context;

/** Context must remain alive until the plugin is unregistered. */
nl_plugin nl_counter_plugin(nl_counter_context *context);
#endif
