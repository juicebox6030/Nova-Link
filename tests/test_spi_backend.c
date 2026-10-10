#include <string.h>
#include "test.h"
#include "nova_link/spi_backend.h"

typedef struct {
    nl_radio radio;
    nl_spi_backend *backend;
    const uint8_t *owned;
    uint8_t snapshot[NL_FRAME_MAX];
    size_t size;
    nl_spi_transaction transaction;
    nl_frame prepared;
    nl_pull_token receipt;
    unsigned starts, stops, begins, finishes, accepted, settles;
    unsigned delay, fail_begin, fail_finish, fail_settle;
    bool fail_start, corrupt, uncertain, uncertain_before, malformed_push, stale;
} driver_state;

typedef struct {
    nl_host host;
    nl_spi_backend backend;
    nl_radio_link link;
    nl_radio_link_config config;
    nl_module backend_module, link_module;
    nl_module_instance instances[2];
    driver_state driver;
} fixture;

static nl_status driver_start(void *context)
{
    driver_state *state = context;
    ++state->starts;
    return state->fail_start ? NL_ERR_FORMAT : NL_OK;
}

static void driver_stop(void *context)
{
    driver_state *state = context;
    ++state->stops;
    state->owned = NULL;
    state->receipt = 0;
}

static nl_status driver_ready(void *context, bool *ready)
{
    driver_state *state = context;
    *ready = nl_radio_ready(&state->radio);
    return NL_OK;
}

static nl_status driver_begin(void *context, const uint8_t *bytes, size_t size,
                             nl_spi_transaction transaction, uint64_t now_us)
{
    driver_state *state = context;
    (void)now_us;
    ++state->begins;
    CHECK(state->owned == NULL);
    if (state->fail_begin != 0u) {
        --state->fail_begin;
        return NL_ERR_BUSY;
    }
    CHECK(transaction != 0u && transaction > state->transaction);
    CHECK(size <= sizeof(state->snapshot));
    state->transaction = transaction;
    state->owned = bytes;
    state->size = size;
    memcpy(state->snapshot, bytes, size);
    return NL_OK;
}

static nl_status driver_finish(void *context, nl_spi_transaction transaction,
                              uint64_t now_us, uint8_t *bytes, size_t capacity,
                              size_t *size, nl_pull_token *receipt, bool *uncertain)
{
    driver_state *state = context;
    nl_frame request, response = {0};
    nl_pull_token token = 0;
    nl_status status;
    (void)now_us;
    ++state->finishes;
    CHECK(state->owned != NULL && transaction == state->transaction);
    CHECK(memcmp(state->snapshot, state->owned, state->size) == 0);
    STATUS(nl_spi_backend_resolve_tx(state->backend, false), NL_ERR_BUSY);
    if (state->delay != 0u) {
        --state->delay;
        return NL_ERR_BUSY;
    }
    state->owned = NULL;
    if (state->fail_finish != 0u) {
        --state->fail_finish;
        return NL_ERR_FULL;
    }
    STATUS(nl_frame_decode(state->snapshot, state->size, &request), NL_OK);
    if (request.command == NL_COMMAND_PUSH && state->uncertain_before) {
        state->uncertain_before = false;
        *uncertain = true;
        return NL_ERR_FORMAT;
    }
    status = nl_radio_handle_frame(&state->radio, &request, &response, &token);
    if (status != NL_OK) return status;
    if (request.command == NL_COMMAND_PUSH) {
        ++state->accepted;
        if (state->uncertain) {
            state->uncertain = false;
            *uncertain = true;
            return NL_ERR_FORMAT;
        }
        if (state->malformed_push) {
            state->malformed_push = false;
            bytes[0] = 0;
            *size = 1;
        }
        return NL_OK;
    }
    state->prepared = response;
    state->receipt = token;
    *receipt = token;
    STATUS(nl_frame_encode(&response, bytes, capacity, size), NL_OK);
    if (state->corrupt) {
        state->corrupt = false;
        --*size;
    }
    return NL_OK;
}

static nl_status driver_settle(void *context, nl_pull_token receipt, bool consume)
{
    driver_state *state = context;
    nl_status status = NL_OK;
    ++state->settles;
    CHECK(receipt == state->receipt && receipt != 0u);
    if (state->fail_settle != 0u) {
        --state->fail_settle;
        return NL_ERR_BUSY;
    }
    if (state->stale) {
        state->stale = false;
        status = NL_ERR_STALE;
    } else if (consume) status = nl_radio_commit_pull(&state->radio, &state->prepared, receipt);
    state->receipt = 0;
    return status;
}

static void initialize(fixture *f)
{
    const nl_spi_driver driver = {
        .start = driver_start, .stop = driver_stop, .ready = driver_ready,
        .begin = driver_begin, .finish = driver_finish, .settle = driver_settle,
        .context = &f->driver
    };
    memset(f, 0, sizeof(*f));
    f->driver.backend = &f->backend;
    STATUS(nl_radio_init(&f->driver.radio, 0x02, 100, 100, 1000), NL_OK);
    STATUS(nl_host_init_plugins(&f->host, 1, 1000), NL_OK);
    STATUS(nl_spi_backend_init(&f->backend, &driver), NL_OK);
    STATUS(nl_spi_backend_link_config(&f->backend, 1, &f->config), NL_OK);
    STATUS(nl_radio_link_init(&f->link, &f->config), NL_OK);
    f->backend_module = nl_spi_backend_module(&f->backend);
    f->link_module = nl_spi_backend_link_module(&f->link);
}

static nl_status begin_manifest(fixture *f)
{
    const nl_module *const modules[] = {&f->link_module, &f->backend_module};
    return nl_modules_start(&f->host, modules, f->instances, 2);
}

static void poll_at(fixture *f, uint64_t now_us)
{
    STATUS(nl_host_poll(&f->host, now_us), NL_OK);
}

static void send(fixture *f)
{
    const nl_fragment fragment = {
        .origin = 1, .zone = 1, .sequence = 4,
        .payload_size = 2, .payload = {0xAA, 0xFF}
    };
    nl_frame request, response = {0};
    nl_pull_token receipt = 0;
    STATUS(nl_frame_from_fragment(NL_COMMAND_PUSH, &fragment, &request), NL_OK);
    STATUS(f->config.exchange(f->config.context, &request, &response, &receipt), NL_OK);
}

static void test_tx(void)
{
    fixture f;
    nl_frame request = {.command = NL_COMMAND_PULL}, response = {0};
    nl_pull_token receipt = 0;
    initialize(&f);
    STATUS(begin_manifest(&f), NL_OK);
    send(&f);
    STATUS(nl_modules_stop(f.instances, 2), NL_ERR_BUSY);
    f.driver.fail_begin = 1;
    poll_at(&f, 1);
    CHECK(!f.backend.inflight && f.backend.tx_pending);
    poll_at(&f, 2);
    CHECK(f.backend.inflight);
    f.driver.delay = 1;
    poll_at(&f, 3);
    CHECK(f.backend.inflight);
    f.driver.fail_finish = 1;
    poll_at(&f, 4);
    CHECK(f.backend.tx_pending && f.driver.accepted == 0);
    poll_at(&f, 5);
    poll_at(&f, 6);
    CHECK(!f.backend.tx_pending && f.driver.accepted == 1);
    CHECK(f.backend.stats.tx_accepted == 1 && f.backend.stats.tx_completed == 1);
    CHECK(f.backend.stats.tx_retries == 2);
    STATUS(f.config.exchange(f.config.context, &request, &response, &receipt), NL_ERR_EMPTY);
    poll_at(&f, 5);
    CHECK(f.backend.stats.backward_clocks == 1);
    f.backend.next_transaction = UINT64_MAX;
    send(&f);
    poll_at(&f, 7);
    CHECK(f.backend.last_status == NL_ERR_FULL && f.driver.begins == 3);
    /* No API automatically cancels accepted TX; this exhaustion test restores
     * a safe unused token so the owned TX can drain before shutdown. */
    f.backend.next_transaction = f.driver.transaction + 1u;
    poll_at(&f, 8);
    poll_at(&f, 9);
    STATUS(nl_modules_stop(f.instances, 2), NL_OK);
    CHECK(f.driver.stops == 1);
    STATUS(begin_manifest(&f), NL_OK);
    send(&f);
    poll_at(&f, 0);
    poll_at(&f, 1);
    STATUS(nl_modules_stop(f.instances, 2), NL_OK);
    CHECK(f.driver.accepted == 3);
}

static void test_uncertainty(void)
{
    fixture f;
    nl_fragment incoming = {.origin = 2, .zone = 1, .sequence = 1};
    uint8_t original[NL_FRAME_MAX];
    size_t original_size;
    unsigned begins;
    initialize(&f);
    STATUS(begin_manifest(&f), NL_OK);
    f.driver.uncertain_before = true;
    send(&f);
    original_size = f.backend.tx_size;
    memcpy(original, f.backend.tx, original_size);
    poll_at(&f, 1);
    poll_at(&f, 2);
    CHECK(f.backend.tx_uncertain && f.driver.accepted == 0);
    STATUS(nl_radio_receive(&f.driver.radio, &incoming, 2), NL_OK);
    poll_at(&f, 3);
    poll_at(&f, 4);
    CHECK(f.backend.stats.rx_committed == 1 && f.backend.tx_uncertain);
    CHECK(f.driver.accepted == 0);
    STATUS(nl_spi_backend_resolve_tx(&f.backend, true), NL_OK);
    poll_at(&f, 5);
    CHECK(f.driver.size == original_size);
    CHECK(memcmp(f.driver.snapshot, original, original_size) == 0);
    poll_at(&f, 6);
    CHECK(!f.backend.tx_pending && f.driver.accepted == 1);
    f.driver.uncertain = true;
    send(&f);
    poll_at(&f, 7);
    poll_at(&f, 8);
    CHECK(f.backend.tx_uncertain && f.driver.accepted == 2);
    begins = f.driver.begins;
    poll_at(&f, 9);
    poll_at(&f, 10);
    CHECK(f.driver.begins == begins && f.driver.accepted == 2);
    STATUS(nl_modules_stop(f.instances, 2), NL_ERR_BUSY);
    STATUS(nl_spi_backend_resolve_tx(&f.backend, false), NL_OK);
    CHECK(f.backend.stats.tx_discarded == 1);
    f.driver.malformed_push = true;
    send(&f);
    poll_at(&f, 11);
    poll_at(&f, 12);
    CHECK(f.backend.tx_uncertain && f.driver.accepted == 3);
    STATUS(nl_spi_backend_resolve_tx(&f.backend, false), NL_OK);
    STATUS(nl_spi_backend_resolve_tx(&f.backend, false), NL_ERR_EMPTY);
    CHECK(f.backend.stats.tx_uncertain == 3 && f.backend.stats.tx_completed == 1);
    STATUS(nl_modules_stop(f.instances, 2), NL_OK);
}

static void test_rx_and_rollback(void)
{
    fixture f;
    nl_fragment fragment = {.origin = 2, .zone = 1, .sequence = 1};
    nl_frame wrong;
    nl_pull_token receipt;
    initialize(&f);
    f.driver.fail_start = true;
    STATUS(begin_manifest(&f), NL_ERR_FORMAT);
    CHECK(f.driver.starts == 1 && f.driver.stops == 1);
    CHECK(!f.backend.running && f.backend.host == NULL && f.host.send == NULL);
    f.driver.fail_start = false;
    STATUS(begin_manifest(&f), NL_OK);
    STATUS(nl_radio_receive(&f.driver.radio, &fragment, 0), NL_OK);
    f.driver.corrupt = true;
    f.driver.fail_settle = 1;
    poll_at(&f, 1);
    poll_at(&f, 2);
    CHECK(f.backend.abort_pending && nl_radio_ready(&f.driver.radio));
    STATUS(nl_modules_stop(f.instances, 2), NL_ERR_BUSY);
    poll_at(&f, 3);
    CHECK(!f.backend.abort_pending && nl_radio_ready(&f.driver.radio));
    poll_at(&f, 4);
    /* Retain valid receipt for commit retries; radio-link may discard no-zone
     * data, but will never repeat delivery during those retries. */
    f.driver.fail_settle = 2;
    poll_at(&f, 5);
    CHECK(f.backend.rx_pending && f.link.pending && f.link.settled);
    wrong = f.backend.rx_frame;
    wrong.command = NL_COMMAND_PUSH;
    receipt = f.backend.receipt;
    STATUS(f.config.commit(f.config.context, &wrong, receipt), NL_ERR_STALE);
    STATUS(f.config.commit(f.config.context, &f.backend.rx_frame, receipt + 1u), NL_ERR_STALE);
    poll_at(&f, 6);
    CHECK(f.backend.rx_pending);
    poll_at(&f, 7);
    CHECK(!f.backend.rx_pending && !nl_radio_ready(&f.driver.radio));
    CHECK(f.backend.stats.rx_aborted == 1 && f.backend.stats.rx_committed == 1);
    fragment.sequence = 2;
    STATUS(nl_radio_receive(&f.driver.radio, &fragment, 8), NL_OK);
    poll_at(&f, 8);
    f.driver.stale = true;
    poll_at(&f, 9);
    CHECK(!f.backend.rx_pending && f.link.stats.commit_abandoned == 1);
    /* STALE callback does not remove native RX; model replacement is pulled
     * again with the same head still present. */
    poll_at(&f, 10);
    poll_at(&f, 11);
    CHECK(!nl_radio_ready(&f.driver.radio));
    STATUS(nl_modules_stop(f.instances, 2), NL_OK);
}

typedef struct { unsigned received, accepted; bool sending; } traffic_app;

static nl_status traffic_start(nl_host *host, nl_plugin_id plugin, void *context)
{
    (void)context;
    return nl_host_claim(host, plugin, 1, NL_ZONE_EXCLUSIVE);
}

static void traffic_receive(nl_host *host, nl_plugin_id plugin,
                            const nl_fragment *fragment, void *context)
{
    traffic_app *app = context;
    (void)host;
    (void)plugin;
    CHECK(fragment->origin == 2);
    ++app->received;
}

static void traffic_tick(nl_host *host, nl_plugin_id plugin,
                         uint64_t now_us, void *context)
{
    traffic_app *app = context;
    const uint8_t payload = (uint8_t)now_us;
    nl_status status;
    if (!app->sending) return;
    status = nl_host_send(host, plugin, 1, 0, &payload, 1);
    CHECK(status == NL_OK || status == NL_ERR_BUSY);
    if (status == NL_OK) ++app->accepted;
}

static void test_bidirectional_fairness(void)
{
    fixture f;
    traffic_app app = {.sending = true};
    const nl_plugin callbacks = {
        .start = traffic_start, .receive = traffic_receive,
        .tick = traffic_tick, .context = &app
    };
    nl_plugin_id id = NL_PLUGIN_ID_NONE;
    nl_fragment fragment = {.origin = 2, .zone = 1, .sequence = 1};
    initialize(&f);
    STATUS(begin_manifest(&f), NL_OK);
    STATUS(nl_host_register(&f.host, &callbacks, &id), NL_OK);
    for (uint8_t sequence = 1; sequence <= 3; ++sequence) {
        fragment.sequence = sequence;
        STATUS(nl_radio_receive(&f.driver.radio, &fragment, 0), NL_OK);
    }
    for (uint64_t now = 0; now < 14; ++now) poll_at(&f, now);
    CHECK(app.received == 3 && app.accepted >= 4);
    CHECK(f.backend.stats.rx_committed == 3 && f.driver.accepted >= 3);
    app.sending = false;
    for (uint64_t now = 14; now < 18; ++now) poll_at(&f, now);
    STATUS(nl_host_unregister(&f.host, id), NL_OK);
    STATUS(nl_modules_stop(f.instances, 2), NL_OK);
}

int main(void)
{
    test_tx();
    test_uncertainty();
    test_rx_and_rollback();
    test_bidirectional_fairness();
    return 0;
}
