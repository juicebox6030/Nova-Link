#include "test.h"
#include "nova_link/radio_plugin.h"

typedef struct {
    nl_radio radio;
    unsigned starts, stops, pulls, pushes, commit_calls;
    unsigned fail_commits;
    bool fail_start, veto_stop, transfer_on_pull, corrupt_response;
    nl_frame prepared;
    nl_pull_token prepared_token;
} backend;

typedef struct {
    unsigned received, ticks, received_at_tick;
    bool reply;
    nl_fragment last;
} application;

static nl_status backend_start(void *context)
{
    backend *state = context;
    ++state->starts;
    return state->fail_start ? NL_ERR_FORMAT : NL_OK;
}

static void backend_stop(void *context)
{
    backend *state = context;
    ++state->stops;
}

static nl_status backend_can_stop(void *context)
{
    backend *state = context;
    return state->veto_stop ? NL_ERR_BUSY : NL_OK;
}

static nl_status backend_exchange(void *context, const nl_frame *request,
                                  nl_frame *response, nl_pull_token *token)
{
    backend *state = context;
    nl_frame decoded;
    uint8_t bytes[NL_FRAME_MAX];
    size_t size = 0;
    nl_status status;
    STATUS(nl_frame_encode(request, bytes, sizeof(bytes), &size), NL_OK);
    STATUS(nl_frame_decode(bytes, size, &decoded), NL_OK);
    if (decoded.command == NL_COMMAND_PUSH) ++state->pushes;
    else if (decoded.command == NL_COMMAND_PULL) ++state->pulls;
    else CHECK(false);
    status = nl_radio_handle_frame(&state->radio, &decoded, response, token);
    if (status != NL_OK || decoded.command == NL_COMMAND_PUSH) return status;
    STATUS(nl_frame_encode(response, bytes, sizeof(bytes), &size), NL_OK);
    STATUS(nl_frame_decode(bytes, size, response), NL_OK);
    state->prepared = *response;
    state->prepared_token = *token;
    if (state->transfer_on_pull)
        STATUS(nl_radio_commit_pull(&state->radio, response, *token), NL_OK);
    if (state->corrupt_response) response->command = NL_COMMAND_STATUS;
    return status;
}

static nl_status backend_commit(void *context, const nl_frame *response, nl_pull_token token)
{
    backend *state = context;
    ++state->commit_calls;
    CHECK(token == state->prepared_token);
    if (state->fail_commits != 0u) {
        --state->fail_commits;
        return NL_ERR_BUSY;
    }
    /* The backend can discard a corrupted envelope using its local receipt. */
    return nl_radio_commit_pull(&state->radio,
        state->corrupt_response ? &state->prepared : response, token);
}

static nl_status app_start(nl_host *host, nl_plugin_id plugin, void *context)
{
    (void)context;
    return nl_host_claim(host, plugin, 1, NL_ZONE_READ_ONLY);
}

static void app_receive(nl_host *host, nl_plugin_id plugin, const nl_fragment *value, void *context)
{
    application *state = context;
    nl_plugin empty = {0};
    nl_plugin_id unused = NL_PLUGIN_ID_NONE;
    ++state->received;
    state->last = *value;
    STATUS(nl_host_register(host, &empty, &unused), NL_ERR_BUSY);
    STATUS(nl_host_poll(host, 0), NL_ERR_BUSY);
    if (state->reply)
        STATUS(nl_host_send(host, plugin, 0, 0, value->payload, value->payload_size), NL_OK);
}

static void app_tick(nl_host *host, nl_plugin_id plugin, uint64_t now_us, void *context)
{
    application *state = context;
    (void)host;
    (void)plugin;
    (void)now_us;
    ++state->ticks;
    state->received_at_tick = state->received;
}

static nl_plugin app_plugin(application *state)
{
    nl_plugin plugin = {
        .start = app_start, .receive = app_receive, .tick = app_tick, .context = state
    };
    return plugin;
}

static void initialize(backend *state, nl_radio_link *link, uint16_t budget)
{
    const nl_radio_link_config config = {
        .exchange = backend_exchange,
        .commit = backend_commit,
        .start = backend_start,
        .stop = backend_stop,
        .can_stop = backend_can_stop,
        .context = state,
        .poll_budget = budget
    };
    memset(state, 0, sizeof(*state));
    STATUS(nl_radio_init(&state->radio, 0xFEu, 1000, 0, 100000), NL_OK);
    STATUS(nl_radio_link_init(link, &config), NL_OK);
}

static void transport_and_budget(void)
{
    backend state;
    nl_radio_link link;
    nl_host host;
    application app = {0};
    nl_plugin plugin;
    nl_plugin_id app_id, link_id;
    nl_fragment outgoing, incoming = fragment(2, 1, 0);
    unsigned i;
    initialize(&state, &link, 2);
    STATUS(nl_host_init_plugins(&host, 1, 100000), NL_OK);
    plugin = app_plugin(&app);
    STATUS(nl_host_register(&host, &plugin, &app_id), NL_OK);
    STATUS(nl_host_send(&host, app_id, 0, 0, NULL, 0), NL_ERR_NOT_FOUND);
    CHECK(host.next_sequence[0] == 0u);
    plugin = nl_radio_link_plugin(&link);
    STATUS(nl_host_register(&host, &plugin, &link_id), NL_OK);
    for (i = 0; i < 5u; ++i) {
        incoming.sequence = (uint8_t)i;
        STATUS(nl_radio_receive(&state.radio, &incoming, i), NL_OK);
    }
    STATUS(nl_host_poll(&host, 10), NL_OK);
    CHECK(app.received == 2u && app.received_at_tick == 2u && state.pulls == 2u);
    CHECK(state.radio.rx.count == 3u && link.stats.rx_delivered == 2u);
    STATUS(nl_host_poll(&host, 20), NL_OK);
    CHECK(app.received == 4u && app.received_at_tick == 4u && state.pulls == 4u);
    app.reply = true;
    STATUS(nl_host_poll(&host, 30), NL_OK);
    CHECK(app.received == 5u && app.received_at_tick == 5u && state.pulls == 6u);
    CHECK(link.stats.commits == 5u && !link.pending);
    STATUS(nl_radio_pop_tx(&state.radio, 0, &outgoing), NL_OK);
    CHECK(outgoing.sequence == 0u && outgoing.payload_size == incoming.payload_size);
    CHECK(memcmp(outgoing.payload, incoming.payload, incoming.payload_size) == 0);
    for (i = 0; i < NL_RADIO_TX_DEPTH; ++i)
        STATUS(nl_host_send(&host, app_id, 0, 0, incoming.payload, incoming.payload_size), NL_OK);
    STATUS(nl_host_send(&host, app_id, 0, 0, NULL, 0), NL_ERR_FULL);
    CHECK(host.next_sequence[0] == 9u && link.stats.tx_errors == 1u);
    STATUS(nl_radio_pop_tx(&state.radio, 0, &outgoing), NL_OK);
    CHECK(outgoing.sequence == 1u);
    STATUS(nl_host_send(&host, app_id, 0, 0, NULL, 0), NL_OK);
    CHECK(host.next_sequence[0] == 10u && link.stats.tx_accepted == 10u);
    while (nl_radio_pop_tx(&state.radio, 0, &outgoing) == NL_OK) {}
    state.veto_stop = true;
    STATUS(nl_host_unregister(&host, link_id), NL_ERR_BUSY);
    CHECK(host.send != NULL && state.stops == 0u);
    state.veto_stop = false;
    STATUS(nl_host_unregister(&host, link_id), NL_OK);
    CHECK(state.stops == 1u && host.send == NULL && link.host == NULL);
    STATUS(nl_host_send(&host, app_id, 0, 0, NULL, 0), NL_ERR_NOT_FOUND);
    STATUS(nl_host_unregister(&host, app_id), NL_OK);
}

static void pending_and_errors(void)
{
    backend state;
    nl_radio_link link;
    nl_host host;
    application app = {0};
    nl_plugin plugin;
    nl_plugin_id app_id, link_id;
    nl_fragment incoming = fragment(2, 1, 0);
    initialize(&state, &link, 2);
    STATUS(nl_host_init_plugins(&host, 1, 100000), NL_OK);
    plugin = app_plugin(&app);
    STATUS(nl_host_register(&host, &plugin, &app_id), NL_OK);
    plugin = nl_radio_link_plugin(&link);
    STATUS(nl_host_register(&host, &plugin, &link_id), NL_OK);
    STATUS(nl_radio_receive(&state.radio, &incoming, 0), NL_OK);
    /* Exercise the callback under a temporary host dispatch conflict. */
    host.dispatching = true;
    plugin.poll(&host, link_id, 1, &link);
    host.dispatching = false;
    CHECK(link.pending && !link.settled && app.received == 0u);
    CHECK(state.radio.rx.count == 1u && link.stats.receive_retries == 1u);
    STATUS(nl_host_unregister(&host, link_id), NL_ERR_BUSY);
    state.fail_commits = 2;
    STATUS(nl_host_poll(&host, 2), NL_OK);
    CHECK(link.pending && link.settled && app.received == 1u && state.pulls == 1u);
    STATUS(nl_host_poll(&host, 3), NL_OK);
    CHECK(link.pending && app.received == 1u && state.radio.rx.count == 1u);
    STATUS(nl_host_poll(&host, 4), NL_OK);
    CHECK(!link.pending && app.received == 1u && state.radio.rx.count == 0u);
    CHECK(link.stats.commit_errors == 2u && link.stats.commits == 1u);
    incoming.sequence = 1;
    STATUS(nl_host_receive(&host, &incoming, 5), NL_OK);
    STATUS(nl_radio_receive(&state.radio, &incoming, 5), NL_OK);
    STATUS(nl_host_poll(&host, 6), NL_OK);
    CHECK(link.last_receive_status == NL_ERR_DUPLICATE && app.received == 2u);
    incoming.origin = host.origin;
    STATUS(nl_radio_receive(&state.radio, &incoming, 7), NL_OK);
    STATUS(nl_host_poll(&host, 8), NL_OK);
    CHECK(link.last_receive_status == NL_ERR_CONFLICT && app.received == 2u);
    incoming.origin = 2;
    incoming.zone = 2;
    STATUS(nl_radio_receive(&state.radio, &incoming, 9), NL_OK);
    STATUS(nl_host_poll(&host, 10), NL_OK);
    CHECK(link.last_receive_status == NL_ERR_NOT_FOUND && app.received == 2u);
    incoming.zone = 1;
    incoming.sequence = 2;
    state.corrupt_response = true;
    STATUS(nl_radio_receive(&state.radio, &incoming, 11), NL_OK);
    STATUS(nl_host_poll(&host, 12), NL_OK);
    CHECK(link.last_receive_status == NL_ERR_SIZE && app.received == 2u);
    CHECK(link.stats.rx_discarded == 4u && state.radio.rx.count == 0u);
    STATUS(nl_host_unregister(&host, link_id), NL_OK);
    STATUS(nl_host_unregister(&host, app_id), NL_OK);
}

static nl_status legacy_send(void *context, const nl_fragment *value)
{
    (void)context;
    (void)value;
    return NL_OK;
}

static void invalidated_receipts(void)
{
    backend state;
    nl_radio_link link;
    nl_host host;
    application app = {0};
    nl_plugin plugin;
    nl_plugin_id app_id, link_id;
    nl_fragment incoming = fragment(2, 1, 0);
    initialize(&state, &link, 2);
    STATUS(nl_radio_set_rx_policy(&state.radio, NL_RX_LATEST_PER_STREAM), NL_OK);
    STATUS(nl_host_init_plugins(&host, 1, 100000), NL_OK);
    plugin = app_plugin(&app);
    STATUS(nl_host_register(&host, &plugin, &app_id), NL_OK);
    plugin = nl_radio_link_plugin(&link);
    STATUS(nl_host_register(&host, &plugin, &link_id), NL_OK);
    state.fail_commits = 1;
    STATUS(nl_radio_receive(&state.radio, &incoming, 0), NL_OK);
    STATUS(nl_host_poll(&host, 1), NL_OK);
    CHECK(link.pending && app.received == 1u);
    incoming.sequence = 1;
    incoming.payload[0] = 42;
    STATUS(nl_radio_receive(&state.radio, &incoming, 2), NL_OK);
    CHECK(state.radio.rx.count == 1u && state.radio.stats.coalesced == 1u);
    STATUS(nl_host_poll(&host, 3), NL_OK);
    CHECK(!link.pending && app.received == 2u && app.last.payload[0] == 42u);
    CHECK(link.stats.commit_abandoned == 1u && link.stats.commits == 1u);
    CHECK(state.radio.rx.count == 0u);
    /* Another backend consumer irrevocably transfers the prepared head. */
    incoming.sequence = 2;
    state.fail_commits = 1;
    STATUS(nl_radio_receive(&state.radio, &incoming, 4), NL_OK);
    STATUS(nl_host_poll(&host, 5), NL_OK);
    CHECK(link.pending && app.received == 3u);
    STATUS(nl_radio_commit_pull(&state.radio, &state.prepared, state.prepared_token), NL_OK);
    STATUS(nl_host_poll(&host, 6), NL_OK);
    CHECK(!link.pending && app.received == 3u && link.stats.commit_abandoned == 2u);
    CHECK(link.stats.commit_errors == 4u);
    STATUS(nl_host_unregister(&host, link_id), NL_OK);
    STATUS(nl_host_unregister(&host, app_id), NL_OK);
}

static void lifecycle_and_transfer(void)
{
    backend state, other;
    nl_radio_link link, duplicate;
    nl_host host;
    application app = {0};
    nl_plugin plugin;
    nl_plugin_id app_id, link_id, unused = NL_PLUGIN_ID_NONE;
    nl_radio_link_config invalid = {0};
    nl_fragment incoming = fragment(2, 1, 0);
    nl_module module;
    initialize(&state, &link, 2);
    initialize(&other, &duplicate, 2);
    STATUS(nl_radio_link_init(NULL, &link.config), NL_ERR_ARGUMENT);
    STATUS(nl_radio_link_init(&duplicate, NULL), NL_ERR_ARGUMENT);
    STATUS(nl_radio_link_init(&duplicate, &invalid), NL_ERR_ARGUMENT);
    invalid = duplicate.config;
    invalid.poll_budget = 0;
    STATUS(nl_radio_link_init(&duplicate, &invalid), NL_ERR_ARGUMENT);
    module = nl_radio_link_module(&link);
    CHECK(strcmp(module.name, "radio-link") == 0 && strcmp(module.version, "1") == 0);
    CHECK(module.kind == NL_MODULE_TRANSPORT && module.service == &link);
    STATUS(nl_host_init(&host, 1, 0, legacy_send, NULL), NL_OK);
    plugin = nl_radio_link_plugin(&link);
    STATUS(nl_host_register(&host, &plugin, &unused), NL_ERR_CONFLICT);
    CHECK(state.starts == 0u && state.stops == 0u && host.send == legacy_send);
    STATUS(nl_host_init_plugins(&host, 1, 0), NL_OK);
    state.fail_start = true;
    STATUS(nl_host_register(&host, &plugin, &unused), NL_ERR_FORMAT);
    CHECK(state.starts == 1u && state.stops == 1u && host.send == NULL);
    CHECK(link.host == NULL && unused == NL_PLUGIN_ID_NONE);
    state.fail_start = false;
    state.transfer_on_pull = true;
    link.config.commit = NULL;
    STATUS(nl_host_register(&host, &plugin, &link_id), NL_OK);
    STATUS(nl_host_register(&host, &plugin, &unused), NL_ERR_BUSY);
    CHECK(link.plugin == link_id && link.host == &host && state.stops == 1u);
    plugin = nl_radio_link_plugin(&duplicate);
    STATUS(nl_host_register(&host, &plugin, &unused), NL_ERR_CONFLICT);
    CHECK(other.starts == 0u && other.stops == 0u && host.send != NULL);
    plugin = app_plugin(&app);
    STATUS(nl_host_register(&host, &plugin, &app_id), NL_OK);
    STATUS(nl_radio_receive(&state.radio, &incoming, 0), NL_OK);
    STATUS(nl_host_poll(&host, 1), NL_OK);
    CHECK(app.received == 1u && !link.pending && state.radio.rx.count == 0u);
    CHECK(link.stats.commits == 0u);
    STATUS(nl_host_unregister(&host, link_id), NL_OK);
    STATUS(nl_host_unregister(&host, app_id), NL_OK);
    CHECK(state.stops == 2u);
}

int main(void)
{
    transport_and_budget();
    pending_and_errors();
    invalidated_receipts();
    lifecycle_and_transfer();
    puts("radio plugin: framed transport, bounded poll, ownership retry and lifecycle passed");
    return EXIT_SUCCESS;
}
