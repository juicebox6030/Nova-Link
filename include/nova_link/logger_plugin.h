#ifndef NOVA_LINK_LOGGER_PLUGIN_H
#define NOVA_LINK_LOGGER_PLUGIN_H

#include "nova_link/module.h"

/** @file logger_plugin.h Lifecycle-managed host event observer service.
 * The application supplies the observer and owns its storage/output. This
 * service allocates no memory and performs no I/O itself.
 */
typedef struct {
    nl_log_fn callback;
    void *context;
} nl_logger_context;

/** Initialize caller-owned storage. callback must be non-NULL. Keep both this
 * storage and callback context alive and unchanged until unregistration.
 * Observers run synchronously and must not re-enter host APIs; mutating host
 * calls return BUSY during notification. Do not reinitialize a live context.
 */
nl_status nl_logger_init(nl_logger_context *logger, nl_log_fn callback, void *context);
/** Attach the observer during startup and detach it on stop. Existing legacy
 * observers and logger plugins cannot be displaced by registration.
 */
nl_plugin nl_logger_plugin(nl_logger_context *logger);
/** Default service manifest, named "logger", version "1". Applications may
 * depend on that name; logger has no required providers. Replace the descriptor
 * name before registration when an application uses another service name.
 */
nl_module nl_logger_module(nl_logger_context *logger);

#endif
