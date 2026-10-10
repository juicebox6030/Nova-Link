#ifndef NOVA_LINK_MODULE_H
#define NOVA_LINK_MODULE_H

#include "nova_link/host.h"

/** @file module.h Declarative, allocation-free plugins and dependency manifests.
 * Descriptors share the existing nl_plugin callbacks and native wire format.
 * Calls must be serialized with all host calls. Modules are compiled into the
 * application; metadata does not make callbacks untrusted or load code.
 */
typedef enum {
    NL_MODULE_APPLICATION,
    NL_MODULE_TRANSPORT,
    NL_MODULE_SERVICE
} nl_module_kind;

typedef struct { uint8_t zone; nl_zone_mode mode; } nl_module_zone;

typedef struct {
    const char *name;             /**< Nonempty, unique within one host. */
    const char *version;          /**< Nonempty informational version string. */
    nl_module_kind kind;
    const nl_module_zone *zones;  /**< Data zones 1..7, with no duplicates. */
    size_t zone_count;
    const char *const *requires;  /**< Names of modules which must be active. */
    size_t require_count;
    void *service;                /**< Optional provider interface/context. */
    nl_plugin hooks;
    /** Opt into sharing hooks.context. Both modules must opt in. Use only for
     * immutable/stateless contexts or callbacks that safely manage independent
     * registrations. For legacy plugins, this asserts their context is also
     * safe to share. Mutable lifecycle contexts normally stay per instance.
     */
    bool shared_context;
} nl_module;

/** Zero-initialize before first registration. Keep this storage at a stable
 * address until unregistered; do not copy a live instance or modify its fields.
 * Registration copies the descriptor, but referenced strings, arrays, service
 * and hooks.context must remain alive and immutable until unregistration.
 * Initialize the host before registering modules; stop modules before host
 * reinitialization. The owner/id binding is valid only in that host lifetime.
 */
typedef struct {
    nl_host *owner;
    nl_plugin_id id;
    nl_module module;
    bool active;
    bool start_called; /**< Internal lifecycle bookkeeping. */
    bool rolling_back; /**< Internal: startup rollback cannot be vetoed. */
} nl_module_instance;

/** Claim declared zones, then invoke hooks.start. Failed starts invoke
 * hooks.stop only if hooks.start was entered (or all claims succeeded when no
 * start hook exists), and release all claims. Already-active instances and
 * duplicate names or shared non-NULL callback contexts without shared_context
 * opt-in are rejected without callbacks or mutation. Existing legacy plugin
 * contexts are also protected unless sharing is explicitly asserted safe.
 */
nl_status nl_module_register(nl_host *host, const nl_module *module,
                             nl_module_instance *instance);
/** Refuse to remove a provider with active module dependents. Raw host
 * unregistration also enforces the wrapper's dependency guard.
 */
nl_status nl_module_unregister(nl_module_instance *instance);
/** Return a live instance owned by this host, or NULL. This also works inside
 * callbacks; the returned instance and service remain owned by the application.
 */
nl_module_instance *nl_module_find(nl_host *host, const char *name);
/** Validate the complete unordered manifest before callbacks: malformed or
 * duplicate names, missing providers and cycles never partially start it.
 * Start providers first; on failure roll back only this manifest in reverse
 * dependency order. Rollback bypasses optional hooks.can_stop vetoes; stop hooks
 * must cancel or drain resources acquired during startup, including pending
 * backend ownership, before releasing their context.
 * Existing providers on the host may satisfy requirements.
 * instances is a zero-initialized array of count entries in manifest order.
 */
nl_status nl_modules_start(nl_host *host, const nl_module *const *modules,
                           nl_module_instance *instances, size_t count);
/** Stop active entries in reverse dependency order. Inactive entries are
 * ignored. External active dependents return NL_ERR_BUSY before any stop.
 * All active instances must belong to the same host. A can_stop veto returns
 * NL_ERR_BUSY; entries already stopped earlier in that call remain stopped.
 */
nl_status nl_modules_stop(nl_module_instance *instances, size_t count);

#endif
