#include "test.h"
#include "nova_link/module.h"

typedef struct {
    char events[128];
    size_t used;
    unsigned sends;
} trace;

typedef struct {
    trace *trace;
    char marker;
    const char *provider;
    void *service;
    unsigned starts, stops, ticks, polls, received;
    bool fail, veto;
} context;

static void event(context *state, bool stopping)
{
    CHECK(state->trace->used + 1u < sizeof(state->trace->events));
    state->trace->events[state->trace->used++] = stopping ?
        (char)(state->marker + ('a' - 'A')) : state->marker;
    state->trace->events[state->trace->used] = '\0';
}

static nl_status sender(void *opaque, const nl_fragment *value)
{
    trace *state = opaque;
    (void)value;
    ++state->sends;
    return NL_OK;
}

static nl_status start(nl_host *host, nl_plugin_id id, void *opaque)
{
    context *state = opaque;
    ++state->starts;
    event(state, false);
    if (state->provider != NULL) {
        nl_module_instance *provider = nl_module_find(host, state->provider);
        CHECK(provider != NULL && provider->module.service == state->service);
    }
    STATUS(nl_host_send(host, id, 0, 0, NULL, 0), NL_ERR_BUSY);
    return state->fail ? NL_ERR_FORMAT : NL_OK;
}

static void stop(nl_host *host, nl_plugin_id id, void *opaque)
{
    context *state = opaque;
    ++state->stops;
    event(state, true);
    if (state->provider != NULL) CHECK(nl_module_find(host, state->provider) != NULL);
    STATUS(nl_host_unregister(host, id), NL_ERR_BUSY);
}

static nl_status can_stop(nl_host *host, nl_plugin_id id, void *opaque)
{
    context *state = opaque;
    STATUS(nl_host_unregister(host, id), NL_ERR_BUSY);
    return state->veto ? NL_ERR_BUSY : NL_OK;
}

static void tick(nl_host *host, nl_plugin_id id, uint64_t now_us, void *opaque)
{
    context *state = opaque;
    (void)host; (void)id; (void)now_us;
    ++state->ticks;
}

static void poll(nl_host *host, nl_plugin_id id, uint64_t now_us, void *opaque)
{
    context *state = opaque;
    nl_module_instance attempt = {0};
    nl_module unused = {.name = "reentrant", .version = "1", .kind = NL_MODULE_SERVICE};
    (void)id; (void)now_us;
    ++state->polls;
    STATUS(nl_module_register(host, &unused, &attempt), NL_ERR_BUSY);
    CHECK(attempt.owner == NULL && attempt.module.name == NULL);
}

static void receive(nl_host *host, nl_plugin_id id, const nl_fragment *value, void *opaque)
{
    context *state = opaque;
    (void)value;
    ++state->received;
    STATUS(nl_host_unregister(host, id), NL_ERR_BUSY);
}

static nl_module make_module(const char *name, context *state)
{
    nl_module module = {.name = name, .version = "1", .kind = NL_MODULE_APPLICATION,
        .hooks = {.start = start, .stop = stop, .tick = tick,
                  .receive = receive, .context = state, .poll = poll, .can_stop = can_stop}};
    return module;
}

static void lifecycle(void)
{
    nl_host host;
    trace history = {0};
    context provider = {.trace = &history, .marker = 'P'};
    context middle = {.trace = &history, .marker = 'M', .provider = "provider", .service = &provider};
    context client = {.trace = &history, .marker = 'C', .provider = "middle", .service = &middle};
    const char *middle_requires[] = {"provider"}, *client_requires[] = {"middle"};
    const nl_module_zone read[] = {{2, NL_ZONE_READ_ONLY}};
    nl_module p = make_module("provider", &provider), m = make_module("middle", &middle);
    nl_module c = make_module("client", &client);
    const nl_module *manifest[] = {&c, &m, &p};
    nl_module_instance instances[3] = {{0}}, stale;
    nl_fragment incoming = fragment(2, 2, 1);
    nl_plugin_id provider_id;
    p.kind = NL_MODULE_SERVICE; p.service = &provider;
    m.requires = middle_requires; m.require_count = 1; m.service = &middle;
    c.requires = client_requires; c.require_count = 1; c.zones = read; c.zone_count = 1;
    STATUS(nl_host_init(&host, 1, 100, sender, &history), NL_OK);
    STATUS(nl_modules_start(&host, manifest, instances, 3), NL_OK);
    CHECK(strcmp(history.events, "PMC") == 0);
    CHECK(nl_module_find(&host, "client") == &instances[0]);
    CHECK(nl_module_find(&host, "absent") == NULL && nl_module_find(NULL, "client") == NULL);
    provider_id = instances[2].id;
    STATUS(nl_module_unregister(&instances[2]), NL_ERR_BUSY);
    STATUS(nl_host_unregister(&host, provider_id), NL_ERR_BUSY);
    CHECK(provider.stops == 0 && instances[2].active);
    STATUS(nl_host_send(&host, instances[0].id, 2, 0, NULL, 0), NL_ERR_ACCESS);
    STATUS(nl_host_send(&host, instances[0].id, 0, 0, NULL, 0), NL_OK);
    STATUS(nl_host_receive(&host, &incoming, 10), NL_OK);
    CHECK(client.received == 1 && middle.received == 0 && provider.received == 0);
    STATUS(nl_host_poll(&host, 11), NL_OK);
    CHECK(client.polls == 1 && client.ticks == 1 && provider.polls == 1);
    stale = instances[0];
    STATUS(nl_module_unregister(&stale), NL_ERR_NOT_FOUND);
    STATUS(nl_modules_stop(&instances[2], 1), NL_ERR_BUSY);
    CHECK(strcmp(history.events, "PMC") == 0);
    client.veto = true;
    STATUS(nl_module_unregister(&instances[0]), NL_ERR_BUSY);
    STATUS(nl_modules_stop(instances, 3), NL_ERR_BUSY);
    CHECK(strcmp(history.events, "PMC") == 0 && instances[2].active);
    client.veto = false;
    STATUS(nl_modules_stop(instances, 3), NL_OK);
    CHECK(strcmp(history.events, "PMCcmp") == 0);
    CHECK(nl_zones_active_mask(&host.zones) == 0 && nl_module_find(&host, "provider") == NULL);
    STATUS(nl_module_unregister(&instances[0]), NL_ERR_NOT_FOUND);
    STATUS(nl_modules_stop(instances, 3), NL_OK);
    STATUS(nl_host_unregister(&host, provider_id), NL_ERR_NOT_FOUND);
}

static void rollback_and_shared_context(void)
{
    nl_host host;
    trace history = {0};
    context provider = {.trace = &history, .marker = 'P', .veto = true};
    context client = {.trace = &history, .marker = 'C', .fail = true, .provider = "provider", .service = &provider};
    const char *dependencies[] = {"provider"};
    const nl_module_zone write[] = {{3, NL_ZONE_EXCLUSIVE}};
    const nl_module_zone partial_conflict[] = {{4, NL_ZONE_EXCLUSIVE}, {3, NL_ZONE_EXCLUSIVE}};
    context alias = {.trace = &history, .marker = 'A'};
    nl_module p = make_module("provider", &provider), c = make_module("client", &client);
    const nl_module *manifest[] = {&c, &p};
    nl_module_instance instances[2] = {{0}}, other = {0};
    p.service = &provider; p.zones = write; p.zone_count = 1;
    c.requires = dependencies; c.require_count = 1;
    STATUS(nl_host_init(&host, 1, 0, sender, &history), NL_OK);
    STATUS(nl_modules_start(&host, manifest, instances, 2), NL_ERR_FORMAT);
    CHECK(strcmp(history.events, "PCcp") == 0);
    CHECK(!instances[0].active && !instances[1].active && nl_zones_active_mask(&host.zones) == 0);
    provider.veto = false;
    STATUS(nl_module_register(&host, &p, &instances[1]), NL_OK);
    p.name = "alias";
    p.zones = NULL; p.zone_count = 0;
    STATUS(nl_module_register(&host, &p, &other), NL_ERR_CONFLICT);
    CHECK(provider.starts == 2 && provider.stops == 1);
    p.hooks.context = &alias;
    p.zones = partial_conflict; p.zone_count = 2;
    STATUS(nl_module_register(&host, &p, &other), NL_ERR_CONFLICT);
    CHECK(provider.starts == 2 && provider.stops == 1);
    CHECK(alias.starts == 0 && alias.stops == 0);
    CHECK(instances[1].active && nl_module_find(&host, "provider") == &instances[1]);
    CHECK((nl_zones_active_mask(&host.zones) & (uint8_t)(1u << 4)) == 0u);
    client.fail = false;
    STATUS(nl_module_register(&host, &c, &instances[0]), NL_OK);
    CHECK(client.starts == 2);
    STATUS(nl_modules_stop(instances, 2), NL_OK);
    CHECK(provider.stops == 2 && client.stops == 2);
}

static void preflight(void)
{
    nl_host host;
    trace history = {0};
    context a_state = {.trace = &history, .marker = 'A'}, b_state = {.trace = &history, .marker = 'B'};
    nl_module a = make_module("a", &a_state), b = make_module("b", &b_state), invalid;
    const char *requires_a[] = {"a"}, *requires_b[] = {"b"}, *missing[] = {"missing"};
    const char *duplicate_requires[] = {"a", "a"};
    const nl_module_zone invalid_zones[] = {{0, NL_ZONE_READ_ONLY}};
    const nl_module_zone duplicate_zones[] = {{1, NL_ZONE_READ_ONLY}, {1, NL_ZONE_EXCLUSIVE}};
    const nl_module *manifest[] = {&a, &b};
    nl_module_instance instances[2] = {{0}};
    nl_plugin empty = {0};
    nl_plugin_id ids[NL_PLUGIN_MAX];
    size_t i;
    STATUS(nl_host_init(&host, 1, 0, sender, &history), NL_OK);
    a.requires = requires_b; a.require_count = 1;
    b.requires = requires_a; b.require_count = 1;
    STATUS(nl_modules_start(&host, manifest, instances, 2), NL_ERR_CONFLICT);
    b.requires = missing;
    STATUS(nl_modules_start(&host, manifest, instances, 2), NL_ERR_NOT_FOUND);
    b.require_count = 0; a.require_count = 0; b.name = "a";
    STATUS(nl_modules_start(&host, manifest, instances, 2), NL_ERR_DUPLICATE);
    b.name = "b";
    b.hooks.context = &a_state;
    STATUS(nl_modules_start(&host, manifest, instances, 2), NL_ERR_CONFLICT);
    b.hooks.context = &b_state;
    invalid = a; invalid.version = NULL;
    STATUS(nl_module_register(&host, &invalid, &instances[0]), NL_ERR_ARGUMENT);
    invalid = a; invalid.kind = (nl_module_kind)99;
    STATUS(nl_module_register(&host, &invalid, &instances[0]), NL_ERR_ARGUMENT);
    invalid = a; invalid.zones = invalid_zones; invalid.zone_count = 1;
    STATUS(nl_module_register(&host, &invalid, &instances[0]), NL_ERR_ARGUMENT);
    invalid = a; invalid.zones = duplicate_zones; invalid.zone_count = 2;
    STATUS(nl_module_register(&host, &invalid, &instances[0]), NL_ERR_DUPLICATE);
    invalid = b; invalid.requires = duplicate_requires; invalid.require_count = 2;
    STATUS(nl_module_register(&host, &invalid, &instances[0]), NL_ERR_DUPLICATE);
    STATUS(nl_modules_start(&host, manifest, instances, NL_PLUGIN_MAX + 1u), NL_ERR_ARGUMENT);
    STATUS(nl_modules_start(&host, NULL, NULL, 0), NL_OK);
    STATUS(nl_modules_stop(NULL, 0), NL_OK);
    CHECK(history.used == 0 && instances[0].module.name == NULL);
    for (i = 0; i < NL_PLUGIN_MAX; ++i) STATUS(nl_host_register(&host, &empty, &ids[i]), NL_OK);
    STATUS(nl_modules_start(&host, manifest, instances, 2), NL_ERR_FULL);
    CHECK(history.used == 0 && instances[0].module.name == NULL);
    for (i = 0; i < NL_PLUGIN_MAX; ++i) STATUS(nl_host_unregister(&host, ids[i]), NL_OK);
    empty.context = &a_state;
    STATUS(nl_host_register(&host, &empty, &ids[0]), NL_OK);
    STATUS(nl_module_register(&host, &a, &instances[0]), NL_ERR_CONFLICT);
    CHECK(a_state.starts == 0 && a_state.stops == 0);
    STATUS(nl_host_unregister(&host, ids[0]), NL_OK);
    STATUS(nl_module_register(&host, &a, &instances[0]), NL_OK);
    STATUS(nl_module_register(&host, &a, &instances[1]), NL_ERR_DUPLICATE);
    STATUS(nl_module_register(&host, &b, &instances[0]), NL_ERR_BUSY);
    STATUS(nl_modules_start(&host, manifest, instances, 2), NL_ERR_BUSY);
    STATUS(nl_host_unregister(&host, instances[0].id), NL_OK);
    CHECK(!instances[0].active && instances[0].owner == NULL);
}

static void shared_stateless_context(void)
{
    nl_host host;
    trace history = {0};
    unsigned shared = 7;
    nl_module a = {.name = "a", .version = "1", .kind = NL_MODULE_SERVICE,
        .hooks = {.context = &shared}, .shared_context = true};
    nl_module b = {.name = "b", .version = "1", .kind = NL_MODULE_SERVICE,
        .hooks = {.context = &shared}};
    const nl_module *manifest[] = {&a, &b};
    nl_module_instance instances[2] = {{0}};
    nl_plugin legacy = {.context = &shared};
    nl_plugin_id legacy_id;
    STATUS(nl_host_init(&host, 1, 0, sender, &history), NL_OK);
    STATUS(nl_modules_start(&host, manifest, instances, 2), NL_ERR_CONFLICT);
    b.shared_context = true;
    STATUS(nl_modules_start(&host, manifest, instances, 2), NL_OK);
    CHECK(shared == 7 && instances[0].active && instances[1].active);
    STATUS(nl_modules_stop(instances, 2), NL_OK);
    STATUS(nl_host_register(&host, &legacy, &legacy_id), NL_OK);
    STATUS(nl_module_register(&host, &a, &instances[0]), NL_OK);
    STATUS(nl_module_unregister(&instances[0]), NL_OK);
    STATUS(nl_host_unregister(&host, legacy_id), NL_OK);
}

int main(void)
{
    lifecycle();
    rollback_and_shared_context();
    preflight();
    shared_stateless_context();
    puts("modules: dependency manifests, rollback, provider guards and callback dispatch passed");
    return EXIT_SUCCESS;
}
