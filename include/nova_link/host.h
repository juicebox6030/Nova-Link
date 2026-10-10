#ifndef NOVA_LINK_HOST_H
#define NOVA_LINK_HOST_H

#include "nova_link/stream.h"
#include "nova_link/transport.h"
#include "nova_link/zones.h"

/** @file host.h Static plugin lifecycle, access-controlled send, and per-stream deduplicated dispatch. */
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
    /** Poll transport/service input before application ticks. May dispatch RX;
     * registry mutation and recursive poll/tick are prohibited. Optional.
     */
    void (*poll)(nl_host *host, nl_plugin_id plugin, uint64_t now_us, void *context);
    /** Optional shutdown veto. Return BUSY while dependents/work need the plugin.
     * Called before stop with lifecycle mutation guarded. Must not send/dispatch.
     */
    nl_status (*can_stop)(nl_host *host, nl_plugin_id plugin, void *context);
} nl_plugin;
typedef enum { NL_PLUGIN_FREE, NL_PLUGIN_STARTING, NL_PLUGIN_ACTIVE, NL_PLUGIN_STOPPING } nl_plugin_state;
typedef struct { nl_plugin callbacks; nl_plugin_state state; uint32_t generation; } nl_plugin_slot;

struct nl_host {
    uint8_t origin;
    uint64_t callback_now_us; /**< Receive/tick timestamp for plugin callbacks. */
    uint8_t next_sequence[8];
    nl_zone_table zones;
    nl_stream_tracker streams;
    nl_plugin_slot plugins[NL_PLUGIN_MAX];
    nl_send_fn send;
    void *send_context;
    nl_plugin_id transport_owner; /**< NONE for legacy callback or no transport. */
    nl_log_fn log;
    void *log_context;
    nl_plugin_id logger_owner; /**< NONE for legacy callback or no logger. */
    bool dispatching;
    bool sending;
    bool lifecycle_busy;
    bool logging;
    bool polling;
    bool poll_callback;
};

nl_status nl_host_init(nl_host *host, uint8_t origin, uint64_t idle_timeout_us, nl_send_fn send, void *context);
/** Initialize a plugin-only base. No send transport until a plugin attaches one. */
nl_status nl_host_init_plugins(nl_host *host, uint8_t origin, uint64_t idle_timeout_us);
/** Attach one transport during plugin startup or active operation. An existing
 * callback/provider cannot be replaced. Lifetime belongs to the registration.
 */
nl_status nl_host_attach_transport(nl_host *host, nl_plugin_id plugin,
                                   nl_send_fn send, void *context);
/** Only the owning provider may detach, including during stop. */
nl_status nl_host_detach_transport(nl_host *host, nl_plugin_id plugin);
void nl_host_set_logger(nl_host *host, nl_log_fn log, void *context);
/** Lifecycle-managed observer. Refuse displacement of an existing callback. */
nl_status nl_host_attach_logger(nl_host *host, nl_plugin_id plugin,
                               nl_log_fn log, void *context);
/** Remove only this registration's observer, including during stop. */
nl_status nl_host_detach_logger(nl_host *host, nl_plugin_id plugin);
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
/** Poll registered transport/services, allowing RX dispatch, then tick plugins.
 * One serialized event-loop call. Does not read a clock or perform device I/O.
 * Provider-specific polling errors are reported by provider context/observers.
 */
nl_status nl_host_poll(nl_host *host, uint64_t now_us);

#endif
