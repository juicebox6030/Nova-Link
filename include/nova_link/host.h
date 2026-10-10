#ifndef NOVA_LINK_HOST_H
#define NOVA_LINK_HOST_H

#include "nova_link/stream.h"
#include "nova_link/transport.h"
#include "nova_link/zones.h"

/** @file host.h Static plugin lifecycle, access-controlled send, and per-stream deduplicated dispatch.
 * Like the radio, the host takes no locks: call it from one task, never from an ISR. */
typedef struct nl_host nl_host;
/** Opaque slot + generation handle. Valid only for one host initialization lifetime. */
typedef uint32_t nl_plugin_id;
#define NL_PLUGIN_ID_NONE UINT32_MAX
typedef nl_status (*nl_send_fn)(void *context, const nl_fragment *fragment);
typedef enum { NL_LOG_ACCESS, NL_LOG_START, NL_LOG_SEND, NL_LOG_RECEIVE } nl_log_event;
/** Observer callback; must not re-enter host APIs. */
typedef void (*nl_log_fn)(void *context, nl_log_event event, nl_status status, nl_plugin_id plugin, uint8_t zone);
typedef struct {
    nl_status (*start)(nl_host *host, nl_plugin_id plugin, void *context);
    void (*receive)(nl_host *host, nl_plugin_id plugin, const nl_fragment *fragment, void *context);
    void (*tick)(nl_host *host, nl_plugin_id plugin, uint64_t now_us, void *context);
    void (*stop)(nl_host *host, nl_plugin_id plugin, void *context);
    void *context;
} nl_plugin;
typedef enum { NL_PLUGIN_FREE, NL_PLUGIN_STARTING, NL_PLUGIN_ACTIVE, NL_PLUGIN_STOPPING } nl_plugin_state;
typedef struct { nl_plugin callbacks; nl_plugin_state state; uint32_t generation; } nl_plugin_slot;

/** Sandbox hooks run around every plugin callback (start, receive, tick, stop)
 * with the host and slot index (0..NL_PLUGIN_MAX-1). Define both before
 * including this header (or with -D) to, for example, switch MPU regions to
 * the plugin's own RAM and drop privilege; EXIT must restore the host's view.
 * Callbacks may re-enter host APIs, so the hooks must leave nl_host and the
 * plugin's context reachable. Both default to nothing.
 */
#ifndef NL_PLUGIN_ENTER
#define NL_PLUGIN_ENTER(host, index) ((void)0)
#endif
#ifndef NL_PLUGIN_EXIT
#define NL_PLUGIN_EXIT(host, index) ((void)0)
#endif

struct nl_host {
    uint8_t origin;
    uint8_t next_sequence[8];
    nl_zone_table zones;
    nl_stream_tracker streams;
    nl_plugin_slot plugins[NL_PLUGIN_MAX];
    nl_send_fn send;
    void *send_context;
    nl_log_fn log;
    void *log_context;
    bool dispatching;
    bool sending;
    bool lifecycle_busy;
    bool logging;
};

nl_status nl_host_init(nl_host *host, uint8_t origin, uint64_t idle_timeout_us, nl_send_fn send, void *context);
void nl_host_set_logger(nl_host *host, nl_log_fn log, void *context);
/** Run start synchronously. Failed start releases all claims; plugin ID is unchanged on failure. */
nl_status nl_host_register(nl_host *host, const nl_plugin *plugin, nl_plugin_id *id);
/** Run stop, release claims and free the slot. Registry mutation during callbacks is rejected. */
nl_status nl_host_unregister(nl_host *host, nl_plugin_id plugin);
nl_status nl_host_claim(nl_host *host, nl_plugin_id plugin, uint8_t zone, nl_zone_mode mode);
nl_status nl_host_release(nl_host *host, nl_plugin_id plugin, uint8_t zone);
/** Send one payload, up to 100 bytes. Advance sequence only when transport accepts it.
 * Startup callbacks may claim zones but may not send. Larger application messages
 * require a plugin-specific fragmentation format (no implicit truncation).
 */
nl_status nl_host_send(nl_host *host, nl_plugin_id plugin, uint8_t zone, uint8_t flags,
                       const uint8_t *payload, size_t size);
nl_status nl_host_receive(nl_host *host, const nl_fragment *fragment, uint64_t now_us);
/** Only accept a radio-to-host FRAGMENT frame; reject requests in this direction. */
nl_status nl_host_receive_frame(nl_host *host, const nl_frame *frame, uint64_t now_us);
nl_status nl_host_tick(nl_host *host, uint64_t now_us);

#endif
