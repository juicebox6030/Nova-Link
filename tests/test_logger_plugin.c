#include "test.h"
#include "nova_link/logger_plugin.h"

typedef struct {
    nl_host *host;
    nl_plugin_id observer;
    unsigned events[4];
    nl_log_event last_event;
    nl_status last_status;
    nl_plugin_id last_plugin;
    uint8_t last_zone;
    bool exercise_reentry;
} observations;

static nl_status send_full(void *context, const nl_fragment *value)
{
    (void)context;
    (void)value;
    return NL_ERR_FULL;
}

static void observe(void *context, nl_log_event event, nl_status status,
                    nl_plugin_id plugin, uint8_t zone)
{
    observations *state = context;
    CHECK((unsigned)event < 4u);
    ++state->events[event];
    state->last_event = event;
    state->last_status = status;
    state->last_plugin = plugin;
    state->last_zone = zone;
    if (state->exercise_reentry) {
        nl_plugin empty = {0};
        nl_plugin_id id = NL_PLUGIN_ID_NONE;
        nl_fragment incoming = fragment(2, 0, 1);
        nl_log_fn saved = state->host->log;
        STATUS(nl_host_register(state->host, &empty, &id), NL_ERR_BUSY);
        STATUS(nl_host_unregister(state->host, state->observer), NL_ERR_BUSY);
        STATUS(nl_host_attach_logger(state->host, state->observer, observe, state), NL_ERR_BUSY);
        STATUS(nl_host_detach_logger(state->host, state->observer), NL_ERR_BUSY);
        STATUS(nl_host_claim(state->host, state->observer, 1, NL_ZONE_READ_ONLY), NL_ERR_BUSY);
        STATUS(nl_host_release(state->host, state->observer, 1), NL_ERR_BUSY);
        STATUS(nl_host_send(state->host, state->observer, 0, 0, NULL, 0), NL_ERR_BUSY);
        STATUS(nl_host_receive(state->host, &incoming, 0), NL_ERR_BUSY);
        STATUS(nl_host_tick(state->host, 0), NL_ERR_BUSY);
        STATUS(nl_host_poll(state->host, 0), NL_ERR_BUSY);
        nl_host_set_logger(state->host, NULL, NULL);
        CHECK(state->host->log == saved);
    }
}

static void receive(nl_host *host, nl_plugin_id id, const nl_fragment *value, void *context)
{
    unsigned *received = context;
    (void)host;
    (void)id;
    (void)value;
    ++*received;
}

static void lifecycle_and_observation(void)
{
    nl_host host;
    nl_logger_context logger;
    observations events = {0}, replacement_events = {0};
    nl_logger_context replacement;
    nl_plugin plugin, reader;
    nl_plugin_id logger_id, reader_id, duplicate = NL_PLUGIN_ID_NONE, replacement_id;
    nl_fragment incoming = fragment(2, 0, 1);
    unsigned received = 0, count;
    STATUS(nl_logger_init(NULL, observe, &events), NL_ERR_ARGUMENT);
    STATUS(nl_logger_init(&logger, NULL, &events), NL_ERR_ARGUMENT);
    STATUS(nl_logger_init(&logger, observe, &events), NL_OK);
    STATUS(nl_host_init(&host, 1, 100, send_full, NULL), NL_OK);
    events.host = &host;
    plugin = nl_logger_plugin(&logger);
    STATUS(nl_host_register(&host, &plugin, &logger_id), NL_OK);
    CHECK(events.events[NL_LOG_START] == 1 && events.last_plugin == logger_id);
    events.observer = logger_id;
    events.exercise_reentry = true;
    reader = (nl_plugin){.receive = receive, .context = &received};
    STATUS(nl_host_register(&host, &reader, &reader_id), NL_OK);
    CHECK(events.events[NL_LOG_START] == 2);
    STATUS(nl_host_send(&host, reader_id, 1, 0, NULL, 0), NL_ERR_ACCESS);
    CHECK(events.events[NL_LOG_ACCESS] == 1 && events.last_zone == 1);
    CHECK(events.last_status == NL_ERR_ACCESS && events.last_plugin == reader_id);
    STATUS(nl_host_send(&host, reader_id, 0, 0, NULL, 0), NL_ERR_FULL);
    CHECK(events.events[NL_LOG_SEND] == 1 && events.last_status == NL_ERR_FULL);
    STATUS(nl_host_receive(&host, &incoming, 1), NL_OK);
    STATUS(nl_host_receive(&host, &incoming, 2), NL_ERR_DUPLICATE);
    CHECK(received == 1 && events.events[NL_LOG_RECEIVE] == 1);
    CHECK(events.last_plugin == NL_PLUGIN_ID_NONE && events.last_status == NL_ERR_DUPLICATE);
    STATUS(nl_host_register(&host, &plugin, &duplicate), NL_ERR_CONFLICT);
    CHECK(duplicate == NL_PLUGIN_ID_NONE);
    CHECK(host.log == observe && host.log_context == &events);
    STATUS(nl_host_detach_logger(&host, reader_id), NL_ERR_ACCESS);
    nl_host_set_logger(&host, NULL, NULL);
    CHECK(host.log == observe && host.log_context == &events);
    STATUS(nl_host_unregister(&host, logger_id), NL_OK);
    CHECK(host.log == NULL && host.log_context == NULL);
    count = events.events[NL_LOG_SEND];
    STATUS(nl_host_send(&host, reader_id, 0, 0, NULL, 0), NL_ERR_FULL);
    CHECK(events.events[NL_LOG_SEND] == count);
    STATUS(nl_logger_init(&replacement, observe, &replacement_events), NL_OK);
    plugin = nl_logger_plugin(&replacement);
    STATUS(nl_host_register(&host, &plugin, &replacement_id), NL_OK);
    CHECK(replacement_id != logger_id && replacement_events.events[NL_LOG_START] == 1);
    STATUS(nl_host_detach_logger(&host, logger_id), NL_ERR_NOT_FOUND);
    STATUS(nl_host_attach_logger(&host, logger_id, observe, &events), NL_ERR_NOT_FOUND);
    CHECK(host.log == observe && host.log_context == &replacement_events);
    STATUS(nl_host_unregister(&host, replacement_id), NL_OK);
    STATUS(nl_host_unregister(&host, reader_id), NL_OK);
}

static nl_status fail_after_attach(nl_host *host, nl_plugin_id id, void *context)
{
    STATUS(nl_host_attach_logger(host, id, observe, context), NL_OK);
    return NL_ERR_FORMAT;
}

static void startup_and_legacy(void)
{
    nl_host host;
    observations events = {0}, legacy = {0};
    nl_logger_context logger;
    nl_plugin plugin;
    nl_plugin_id id = NL_PLUGIN_ID_NONE;
    STATUS(nl_host_init_plugins(&host, 1, 100), NL_OK);
    STATUS(nl_logger_init(&logger, observe, &events), NL_OK);
    plugin = nl_logger_plugin(NULL);
    STATUS(nl_host_register(&host, &plugin, &id), NL_ERR_ARGUMENT);
    CHECK(host.log == NULL && id == NL_PLUGIN_ID_NONE);
    plugin = (nl_plugin){.start = fail_after_attach, .context = &events};
    STATUS(nl_host_register(&host, &plugin, &id), NL_ERR_FORMAT);
    CHECK(host.log == NULL && host.log_context == NULL && id == NL_PLUGIN_ID_NONE);
    CHECK(events.events[NL_LOG_START] == 0);
    nl_host_set_logger(&host, observe, &legacy);
    plugin = nl_logger_plugin(&logger);
    STATUS(nl_host_register(&host, &plugin, &id), NL_ERR_CONFLICT);
    CHECK(host.log == observe && host.log_context == &legacy);
    CHECK(legacy.events[NL_LOG_START] == 1 && events.events[NL_LOG_START] == 0);
    nl_host_set_logger(&host, NULL, NULL);
    STATUS(nl_host_register(&host, &plugin, &id), NL_OK);
    STATUS(nl_host_unregister(&host, id), NL_OK);
}

static void module_manifest(void)
{
    nl_host host;
    observations events = {0};
    nl_logger_context logger;
    const char *requires[] = {"logger"};
    nl_module service, application = {.name = "application", .version = "1",
        .kind = NL_MODULE_APPLICATION, .requires = requires, .require_count = 1};
    const nl_module *manifest[2];
    nl_module_instance instances[2] = {{0}};
    STATUS(nl_host_init_plugins(&host, 1, 100), NL_OK);
    STATUS(nl_logger_init(&logger, observe, &events), NL_OK);
    service = nl_logger_module(&logger);
    CHECK(strcmp(service.name, "logger") == 0 && strcmp(service.version, "1") == 0);
    CHECK(service.kind == NL_MODULE_SERVICE && service.service == &logger);
    CHECK(service.require_count == 0 && service.zone_count == 0);
    manifest[0] = &application;
    manifest[1] = &service;
    STATUS(nl_modules_start(&host, manifest, instances, 2), NL_OK);
    CHECK(events.events[NL_LOG_START] == 2 && nl_module_find(&host, "logger") == &instances[1]);
    STATUS(nl_module_unregister(&instances[1]), NL_ERR_BUSY);
    STATUS(nl_host_unregister(&host, instances[1].id), NL_ERR_BUSY);
    STATUS(nl_modules_stop(instances, 2), NL_OK);
    CHECK(host.log == NULL && !instances[0].active && !instances[1].active);
    CHECK(nl_module_find(&host, "logger") == NULL);
}

int main(void)
{
    lifecycle_and_observation();
    startup_and_legacy();
    module_manifest();
    puts("logger plugin: observed events, ownership, reentry, rollback and manifests passed");
    return EXIT_SUCCESS;
}
