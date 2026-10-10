#include <string.h>
#include "nova_link/module.h"

static nl_status module_start(nl_host *host, nl_plugin_id id, void *context);
static void module_stop(nl_host *host, nl_plugin_id id, void *context);

static nl_module_instance *slot_instance(nl_host *host, size_t index)
{
    nl_plugin_slot *slot = &host->plugins[index];
    nl_module_instance *instance;
    if (slot->state != NL_PLUGIN_ACTIVE || slot->callbacks.start != module_start ||
        slot->callbacks.stop != module_stop) return NULL;
    instance = slot->callbacks.context;
    if (instance == NULL || !instance->active || instance->owner != host ||
        instance->id != ((slot->generation << 8) | (nl_plugin_id)index)) return NULL;
    return instance;
}

static bool live(nl_module_instance *instance)
{
    size_t index;
    if (instance == NULL || !instance->active || instance->owner == NULL) return false;
    index = instance->id & 0xFFu;
    return index < NL_PLUGIN_MAX && slot_instance(instance->owner, index) == instance;
}

static bool requires(const nl_module *module, const char *name)
{
    size_t i;
    for (i = 0; i < module->require_count; ++i)
        if (strcmp(module->requires[i], name) == 0) return true;
    return false;
}

static bool context_in_use(nl_host *host, const nl_module *module)
{
    size_t i;
    void *context = module->hooks.context;
    if (context == NULL) return false;
    for (i = 0; i < NL_PLUGIN_MAX; ++i) {
        nl_plugin_slot *slot = &host->plugins[i];
        if (slot->state == NL_PLUGIN_FREE) continue;
        if (slot->callbacks.start == module_start && slot->callbacks.stop == module_stop) {
            nl_module_instance *instance = slot->callbacks.context;
            if (instance != NULL && instance->module.hooks.context == context &&
                !(module->shared_context && instance->module.shared_context)) return true;
        } else if (slot->callbacks.context == context && !module->shared_context) return true;
    }
    return false;
}

static nl_status validate(const nl_module *module)
{
    size_t i, j;
    if (module == NULL || module->name == NULL || module->name[0] == '\0' ||
        module->version == NULL || module->version[0] == '\0' ||
        (module->kind != NL_MODULE_APPLICATION && module->kind != NL_MODULE_TRANSPORT &&
         module->kind != NL_MODULE_SERVICE) || module->zone_count > 7u ||
        module->require_count > NL_PLUGIN_MAX ||
        (module->zone_count != 0u && module->zones == NULL) ||
        (module->require_count != 0u && module->requires == NULL)) return NL_ERR_ARGUMENT;
    for (i = 0; i < module->zone_count; ++i) {
        if (module->zones[i].zone == 0u || module->zones[i].zone >= NL_ZONE_COUNT ||
            (module->zones[i].mode != NL_ZONE_READ_ONLY &&
             module->zones[i].mode != NL_ZONE_EXCLUSIVE)) return NL_ERR_ARGUMENT;
        for (j = 0; j < i; ++j)
            if (module->zones[i].zone == module->zones[j].zone) return NL_ERR_DUPLICATE;
    }
    for (i = 0; i < module->require_count; ++i) {
        if (module->requires[i] == NULL || module->requires[i][0] == '\0') return NL_ERR_ARGUMENT;
        for (j = 0; j < i; ++j)
            if (strcmp(module->requires[i], module->requires[j]) == 0) return NL_ERR_DUPLICATE;
    }
    return NL_OK;
}

nl_module_instance *nl_module_find(nl_host *host, const char *name)
{
    size_t i;
    if (host == NULL || name == NULL) return NULL;
    for (i = 0; i < NL_PLUGIN_MAX; ++i) {
        nl_module_instance *instance = slot_instance(host, i);
        if (instance != NULL && strcmp(instance->module.name, name) == 0) return instance;
    }
    return NULL;
}

static nl_status module_start(nl_host *host, nl_plugin_id id, void *context)
{
    nl_module_instance *instance = context;
    size_t i;
    instance->owner = host;
    instance->id = id;
    for (i = 0; i < instance->module.zone_count; ++i) {
        const nl_module_zone *zone = &instance->module.zones[i];
        nl_status status = nl_host_claim(host, id, zone->zone, zone->mode);
        if (status != NL_OK) return status;
    }
    instance->start_called = true;
    return instance->module.hooks.start != NULL ?
        instance->module.hooks.start(host, id, instance->module.hooks.context) : NL_OK;
}

static void module_stop(nl_host *host, nl_plugin_id id, void *context)
{
    nl_module_instance *instance = context;
    if (instance->start_called && instance->module.hooks.stop != NULL)
        instance->module.hooks.stop(host, id, instance->module.hooks.context);
    instance->active = false;
    instance->start_called = false;
    instance->owner = NULL;
    instance->id = NL_PLUGIN_ID_NONE;
}

static void module_receive(nl_host *host, nl_plugin_id id, const nl_fragment *fragment, void *context)
{
    nl_module_instance *instance = context;
    if (instance->module.hooks.receive != NULL)
        instance->module.hooks.receive(host, id, fragment, instance->module.hooks.context);
}

static void module_tick(nl_host *host, nl_plugin_id id, uint64_t now_us, void *context)
{
    nl_module_instance *instance = context;
    if (instance->module.hooks.tick != NULL)
        instance->module.hooks.tick(host, id, now_us, instance->module.hooks.context);
}

static void module_poll(nl_host *host, nl_plugin_id id, uint64_t now_us, void *context)
{
    nl_module_instance *instance = context;
    if (instance->module.hooks.poll != NULL)
        instance->module.hooks.poll(host, id, now_us, instance->module.hooks.context);
}

static nl_status module_can_stop(nl_host *host, nl_plugin_id id, void *context)
{
    nl_module_instance *instance = context;
    size_t i;
    for (i = 0; i < NL_PLUGIN_MAX; ++i) {
        nl_module_instance *other = slot_instance(host, i);
        if (other != NULL && other != instance && requires(&other->module, instance->module.name))
            return NL_ERR_BUSY;
    }
    return !instance->rolling_back && instance->module.hooks.can_stop != NULL ?
        instance->module.hooks.can_stop(host, id, instance->module.hooks.context) : NL_OK;
}

nl_status nl_module_register(nl_host *host, const nl_module *module, nl_module_instance *instance)
{
    nl_plugin plugin;
    nl_module copied;
    nl_plugin_id id = NL_PLUGIN_ID_NONE;
    nl_status status;
    size_t i;
    if (host == NULL || instance == NULL) return NL_ERR_ARGUMENT;
    if (host->dispatching || host->lifecycle_busy || host->sending || host->logging || host->polling) return NL_ERR_BUSY;
    if (instance->active) return live(instance) ? NL_ERR_BUSY : NL_ERR_STALE;
    status = validate(module);
    if (status != NL_OK) return status;
    if (nl_module_find(host, module->name) != NULL) return NL_ERR_DUPLICATE;
    if (context_in_use(host, module)) return NL_ERR_CONFLICT;
    for (i = 0; i < module->require_count; ++i)
        if (nl_module_find(host, module->requires[i]) == NULL) return NL_ERR_NOT_FOUND;
    copied = *module;
    memset(instance, 0, sizeof(*instance));
    instance->id = NL_PLUGIN_ID_NONE;
    instance->module = copied;
    plugin = (nl_plugin){
        .start = module_start,
        .receive = copied.hooks.receive != NULL ? module_receive : NULL,
        .tick = copied.hooks.tick != NULL ? module_tick : NULL,
        .stop = module_stop, .context = instance,
        .poll = copied.hooks.poll != NULL ? module_poll : NULL,
        .can_stop = module_can_stop
    };
    status = nl_host_register(host, &plugin, &id);
    if (status == NL_OK) {
        instance->owner = host;
        instance->id = id;
        instance->active = true;
    }
    return status;
}

nl_status nl_module_unregister(nl_module_instance *instance)
{
    size_t i;
    nl_host *host;
    if (instance == NULL) return NL_ERR_ARGUMENT;
    if (!live(instance)) return NL_ERR_NOT_FOUND;
    host = instance->owner;
    if (host->dispatching || host->lifecycle_busy || host->sending || host->logging || host->polling) return NL_ERR_BUSY;
    for (i = 0; i < NL_PLUGIN_MAX; ++i) {
        nl_module_instance *other = slot_instance(host, i);
        if (other != NULL && other != instance && requires(&other->module, instance->module.name))
            return NL_ERR_BUSY;
    }
    return nl_host_unregister(host, instance->id);
}

nl_status nl_modules_start(nl_host *host, const nl_module *const *modules,
                          nl_module_instance *instances, size_t count)
{
    size_t i, j, n, used = 0, free_slots = 0;
    size_t order[NL_PLUGIN_MAX];
    bool ordered[NL_PLUGIN_MAX] = {false};
    nl_status status;
    if (host == NULL || count > NL_PLUGIN_MAX ||
        (count != 0u && (modules == NULL || instances == NULL))) return NL_ERR_ARGUMENT;
    if (host->dispatching || host->lifecycle_busy || host->sending || host->logging || host->polling) return NL_ERR_BUSY;
    for (i = 0; i < count; ++i) {
        if (instances[i].active) return live(&instances[i]) ? NL_ERR_BUSY : NL_ERR_STALE;
        status = validate(modules[i]);
        if (status != NL_OK) return status;
        if (nl_module_find(host, modules[i]->name) != NULL) return NL_ERR_DUPLICATE;
        if (context_in_use(host, modules[i])) return NL_ERR_CONFLICT;
        for (j = 0; j < i; ++j)
            if (strcmp(modules[j]->name, modules[i]->name) == 0) return NL_ERR_DUPLICATE;
        for (j = 0; j < i; ++j)
            if (modules[i]->hooks.context != NULL &&
                modules[j]->hooks.context == modules[i]->hooks.context &&
                !(modules[j]->shared_context && modules[i]->shared_context)) return NL_ERR_CONFLICT;
    }
    for (i = 0; i < count; ++i) {
        for (j = 0; j < modules[i]->require_count; ++j) {
            if (nl_module_find(host, modules[i]->requires[j]) != NULL) continue;
            for (n = 0; n < count; ++n)
                if (strcmp(modules[n]->name, modules[i]->requires[j]) == 0) break;
            if (n == count) return NL_ERR_NOT_FOUND;
        }
    }
    while (used < count) {
        size_t before = used;
        for (i = 0; i < count; ++i) {
            bool ready = true;
            if (ordered[i]) continue;
            for (j = 0; j < count; ++j)
                if (!ordered[j] && requires(modules[i], modules[j]->name)) ready = false;
            if (ready) { ordered[i] = true; order[used++] = i; }
        }
        if (before == used) return NL_ERR_CONFLICT;
    }
    for (i = 0; i < NL_PLUGIN_MAX; ++i)
        if (host->plugins[i].state == NL_PLUGIN_FREE && host->plugins[i].generation <= 0x00FFFFFFu)
            ++free_slots;
    if (free_slots < count) return NL_ERR_FULL;
    for (i = 0; i < count; ++i) {
        size_t index = order[i];
        status = nl_module_register(host, modules[index], &instances[index]);
        if (status != NL_OK) {
            while (i != 0u) {
                --i;
                instances[order[i]].rolling_back = true;
                (void)nl_module_unregister(&instances[order[i]]);
                instances[order[i]].rolling_back = false;
            }
            return status;
        }
    }
    return NL_OK;
}

nl_status nl_modules_stop(nl_module_instance *instances, size_t count)
{
    nl_host *host = NULL;
    size_t i, j, remaining = 0;
    if (count > NL_PLUGIN_MAX || (count != 0u && instances == NULL)) return NL_ERR_ARGUMENT;
    for (i = 0; i < count; ++i) {
        if (!instances[i].active) continue;
        if (!live(&instances[i])) return NL_ERR_NOT_FOUND;
        if (host != NULL && host != instances[i].owner) return NL_ERR_ARGUMENT;
        host = instances[i].owner;
        ++remaining;
    }
    if (host == NULL) return NL_OK;
    if (host->dispatching || host->lifecycle_busy || host->sending || host->logging || host->polling) return NL_ERR_BUSY;
    for (i = 0; i < NL_PLUGIN_MAX; ++i) {
        nl_module_instance *other = slot_instance(host, i);
        bool inside = false;
        if (other == NULL) continue;
        for (j = 0; j < count; ++j) if (other == &instances[j]) inside = true;
        if (inside) continue;
        for (j = 0; j < count; ++j)
            if (instances[j].active && requires(&other->module, instances[j].module.name)) return NL_ERR_BUSY;
    }
    while (remaining != 0u) {
        bool removed = false;
        for (i = count; i != 0u; --i) {
            nl_status status;
            if (!instances[i - 1u].active) continue;
            status = nl_module_unregister(&instances[i - 1u]);
            if (status == NL_ERR_BUSY) continue;
            if (status != NL_OK) return status;
            --remaining;
            removed = true;
        }
        if (!removed) return NL_ERR_BUSY;
    }
    return NL_OK;
}
