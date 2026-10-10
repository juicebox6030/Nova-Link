#include "test.h"

typedef struct {
    unsigned started, stopped, received, ticks, logs;
    uint8_t zone;
    nl_zone_mode mode;
    bool fail_start, exercise_reentry;
    nl_fragment last;
    nl_host *logged_host;
} plugin_context;
typedef struct { nl_fragment last; unsigned sent; nl_status result; nl_host *host; nl_plugin_id id; } sender;

static nl_status send_fragment(void *context, const nl_fragment *value)
{
    sender *state = context;
    state->last = *value;
    ++state->sent;
    if (state->host != NULL) {
        STATUS(nl_host_send(state->host, state->id, 0, 0, NULL, 0), NL_ERR_BUSY);
        STATUS(nl_host_unregister(state->host, state->id), NL_ERR_BUSY);
    }
    return state->result;
}

static nl_status start(nl_host *host, nl_plugin_id id, void *context)
{
    plugin_context *state = context;
    nl_status status;
    ++state->started;
    STATUS(nl_host_send(host, id, 0, 0, NULL, 0), NL_ERR_BUSY);
    status = nl_host_claim(host, id, state->zone, state->mode);
    return status != NL_OK ? status : state->fail_start ? NL_ERR_FORMAT : NL_OK;
}

static void stop(nl_host *host, nl_plugin_id id, void *context)
{
    plugin_context *state = context;
    ++state->stopped;
    STATUS(nl_host_send(host, id, 0, 0, NULL, 0), NL_ERR_BUSY);
    STATUS(nl_host_unregister(host, id), NL_ERR_BUSY);
}

static void receive(nl_host *host, nl_plugin_id id, const nl_fragment *value, void *context)
{
    plugin_context *state = context;
    ++state->received;
    state->last = *value;
    if (state->exercise_reentry) {
        nl_plugin empty = {0};
        nl_plugin_id new_id = 255;
        STATUS(nl_host_unregister(host, id), NL_ERR_BUSY);
        STATUS(nl_host_register(host, &empty, &new_id), NL_ERR_BUSY);
        STATUS(nl_host_receive(host, value, 10), NL_ERR_BUSY);
        STATUS(nl_host_tick(host, 10), NL_ERR_BUSY);
        STATUS(nl_host_send(host, id, 0, 0, NULL, 0), NL_OK);
    }
}

static void tick(nl_host *host, nl_plugin_id id, uint64_t now_us, void *context)
{
    plugin_context *state = context;
    (void)now_us;
    ++state->ticks;
    STATUS(nl_host_send(host, id, 0, 0, NULL, 0), NL_OK);
}

static void logger(void *context, nl_log_event event, nl_status status, nl_plugin_id plugin, uint8_t zone)
{
    plugin_context *state = context;
    (void)event;
    (void)status;
    (void)plugin;
    (void)zone;
    ++state->logs;
    if (state->logged_host != NULL) STATUS(nl_host_tick(state->logged_host, 0), NL_ERR_BUSY);
}

static nl_plugin make_plugin(plugin_context *context)
{
    nl_plugin plugin = {start, receive, tick, stop, context};
    return plugin;
}

static void handle_exhaustion(void)
{
    nl_host host;
    sender transport = {0};
    plugin_context failure = {0};
    nl_plugin empty = {0}, failing;
    nl_plugin_id id = NL_PLUGIN_ID_NONE;
    unsigned i;
    STATUS(nl_host_init(&host, 1, 0, send_fragment, &transport), NL_OK);
    /* Reach the last generation directly instead of 2^24 retirements per slot. */
    for (i = 0; i < NL_PLUGIN_MAX; ++i) host.plugins[i].generation = 0x00FFFFFFu;
    failure.zone = 1;
    failure.mode = NL_ZONE_EXCLUSIVE;
    failure.fail_start = true;
    failing = make_plugin(&failure);
    STATUS(nl_host_register(&host, &failing, &id), NL_ERR_FORMAT);
    CHECK(id == NL_PLUGIN_ID_NONE && host.plugins[0].generation == 0x01000000u);
    CHECK(nl_zones_active_mask(&host.zones) == 0);
    for (i = 1; i < NL_PLUGIN_MAX; ++i) {
        STATUS(nl_host_register(&host, &empty, &id), NL_OK);
        CHECK(id == (0xFFFFFF00u | i));
        STATUS(nl_host_claim(&host, id, 1, NL_ZONE_EXCLUSIVE), NL_OK);
        STATUS(nl_host_unregister(&host, id), NL_OK);
        CHECK(host.plugins[i].generation == 0x01000000u);
        STATUS(nl_host_claim(&host, id, 1, NL_ZONE_EXCLUSIVE), NL_ERR_NOT_FOUND);
    }
    id = NL_PLUGIN_ID_NONE;
    STATUS(nl_host_register(&host, &empty, &id), NL_ERR_FULL);
    CHECK(id == NL_PLUGIN_ID_NONE);
    STATUS(nl_host_send(&host, 0, 0, 0, NULL, 0), NL_ERR_NOT_FOUND);
}

int main(void)
{
    nl_host host;
    sender transport = {0};
    plugin_context writer = {0}, reader = {0}, failure = {0};
    nl_plugin plugin;
    nl_plugin_id writer_id = 255, reader_id = 255, failed_id = 255;
    uint8_t bytes[101] = {0};
    nl_fragment incoming = fragment(7, 1, 254);
    unsigned i;
    STATUS(nl_host_init(&host, 8, 0, send_fragment, &transport), NL_ERR_ARGUMENT);
    STATUS(nl_host_init(&host, 1, 0, NULL, &transport), NL_ERR_ARGUMENT);
    STATUS(nl_host_init(&host, 1, 0, send_fragment, &transport), NL_OK);
    nl_host_set_logger(&host, logger, &writer);
    writer.logged_host = &host;
    writer.zone = 1;
    writer.mode = NL_ZONE_EXCLUSIVE;
    writer.exercise_reentry = true;
    plugin = make_plugin(&writer);
    STATUS(nl_host_register(&host, &plugin, &writer_id), NL_OK);
    CHECK(writer_id == 0 && writer.started == 1);
    reader.zone = 1;
    reader.mode = NL_ZONE_READ_ONLY;
    plugin = make_plugin(&reader);
    STATUS(nl_host_register(&host, &plugin, &reader_id), NL_ERR_CONFLICT);
    CHECK(reader_id == 255 && reader.stopped == 1);
    STATUS(nl_host_claim(&host, writer_id, 1, NL_ZONE_READ_ONLY), NL_OK);
    STATUS(nl_host_register(&host, &plugin, &reader_id), NL_OK);
    STATUS(nl_host_send(&host, writer_id, 1, 0, bytes, 1), NL_ERR_ACCESS);
    STATUS(nl_host_send(&host, reader_id, 1, 0, bytes, 1), NL_ERR_ACCESS);
    STATUS(nl_host_receive(&host, &incoming, 0), NL_OK);
    CHECK(writer.received == 1 && reader.received == 1);
    incoming.origin = host.origin;
    STATUS(nl_host_receive(&host, &incoming, 1), NL_ERR_CONFLICT);
    CHECK(writer.received == 1 && reader.received == 1);
    CHECK((host.streams.seen[host.origin] & (1u << incoming.zone)) == 0u);
    incoming.origin = 7;
    STATUS(nl_host_receive(&host, &incoming, 1), NL_ERR_DUPLICATE);
    incoming.sequence = 0;
    STATUS(nl_host_receive(&host, &incoming, 2), NL_OK);
    incoming.sequence = 255;
    STATUS(nl_host_receive(&host, &incoming, 3), NL_ERR_STALE);
    incoming.zone = 2;
    STATUS(nl_host_receive(&host, &incoming, 4), NL_ERR_NOT_FOUND);
    incoming.zone = 0;
    STATUS(nl_host_receive(&host, &incoming, 5), NL_OK);
    CHECK(reader.received == 3 && writer.received == 3);
    STATUS(nl_host_tick(&host, 6), NL_OK);
    CHECK(writer.ticks == 1 && reader.ticks == 1);
    STATUS(nl_host_unregister(&host, reader_id), NL_OK);
    STATUS(nl_host_claim(&host, writer_id, 1, NL_ZONE_EXCLUSIVE), NL_OK);
    transport.host = &host;
    transport.id = writer_id;
    transport.result = NL_ERR_FULL;
    STATUS(nl_host_send(&host, writer_id, 1, 0, bytes, 100), NL_ERR_FULL);
    CHECK(transport.last.sequence == 0);
    transport.result = NL_OK;
    STATUS(nl_host_send(&host, writer_id, 1, NL_FLAG_BURST, bytes, 100), NL_OK);
    CHECK(transport.last.sequence == 0 && transport.last.payload_size == 100);
    for (i = 1; i <= 256u; ++i) {
        STATUS(nl_host_send(&host, writer_id, 1, 0, NULL, 0), NL_OK);
        CHECK(transport.last.sequence == (uint8_t)i);
    }
    STATUS(nl_host_send(&host, writer_id, 1, 0, bytes, 101), NL_ERR_SIZE);
    STATUS(nl_host_send(&host, writer_id, 1, 4, bytes, 1), NL_ERR_ARGUMENT);
    STATUS(nl_host_send(&host, writer_id, 1, 0, NULL, 1), NL_ERR_ARGUMENT);
    failure.zone = 7;
    failure.mode = NL_ZONE_EXCLUSIVE;
    failure.fail_start = true;
    plugin = make_plugin(&failure);
    STATUS(nl_host_register(&host, &plugin, &failed_id), NL_ERR_FORMAT);
    CHECK(failed_id == 255 && failure.stopped == 1);
    CHECK((nl_zones_active_mask(&host.zones) & 0x80u) == 0u);
    failure.fail_start = false;
    STATUS(nl_host_register(&host, &plugin, &failed_id), NL_OK);
    STATUS(nl_host_unregister(&host, failed_id), NL_OK);
    STATUS(nl_host_unregister(&host, writer_id), NL_OK);
    STATUS(nl_host_unregister(&host, writer_id), NL_ERR_NOT_FOUND);
    CHECK(writer.stopped == 1 && writer.logs > 0);
    CHECK(nl_zones_active_mask(&host.zones) == 0);
    plugin = (nl_plugin){0};
    STATUS(nl_host_register(&host, &plugin, &failed_id), NL_OK);
    CHECK(failed_id != writer_id);
    STATUS(nl_host_claim(&host, failed_id, 3, NL_ZONE_EXCLUSIVE), NL_OK);
    STATUS(nl_host_send(&host, writer_id, 3, 0, bytes, 1), NL_ERR_NOT_FOUND);
    STATUS(nl_host_claim(&host, writer_id, 3, NL_ZONE_EXCLUSIVE), NL_ERR_NOT_FOUND);
    STATUS(nl_host_release(&host, writer_id, 3), NL_ERR_NOT_FOUND);
    STATUS(nl_host_unregister(&host, writer_id), NL_ERR_NOT_FOUND);
    transport.id = failed_id;
    STATUS(nl_host_send(&host, failed_id, 3, 0, bytes, 1), NL_OK);
    incoming.origin = host.origin;
    STATUS(nl_host_receive(&host, &incoming, 7), NL_ERR_CONFLICT);
    STATUS(nl_host_unregister(&host, failed_id), NL_OK);
    for (i = 0; i < NL_PLUGIN_MAX; ++i) {
        STATUS(nl_host_register(&host, &plugin, &failed_id), NL_OK);
        CHECK((failed_id & 0xFFu) == i);
    }
    STATUS(nl_host_register(&host, &plugin, &failed_id), NL_ERR_FULL);
    handle_exhaustion();
    puts("host: lifecycle rollback, isolation, callbacks, backpressure and sequence wrap passed");
    return EXIT_SUCCESS;
}
