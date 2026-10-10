#include <limits.h>
#include <string.h>
#include "nova_link/fault_backend.h"

nl_status nl_fault_profile_options(nl_fault_profile profile, nl_fault_options *options)
{
    nl_fault_options result = {.active_mask = 2, .slot_us = 1000, .connected = true};
    if (options == NULL) return NL_ERR_ARGUMENT;
    switch (profile) {
    case NL_FAULT_CLEAN: break;
    case NL_FAULT_DELAYED: result.transfer_delay_us = 400; result.commit_delay_us = 900; break;
    case NL_FAULT_DISCONNECTED: result.connected = false; break;
    case NL_FAULT_CONGESTED: result.transfer_delay_us = 400; result.commit_delay_us = 4000; break;
    case NL_FAULT_COMMIT_RETRY: result.commit_failures = 3; break;
    default: return NL_ERR_ARGUMENT;
    }
    *options = result;
    return NL_OK;
}

nl_status nl_fault_backend_init(nl_fault_backend *backend, const nl_fault_options *options)
{
    nl_fault_backend result;
    nl_status status;
    if (backend == NULL || options == NULL) return NL_ERR_ARGUMENT;
    memset(&result, 0, sizeof(result));
    status = nl_radio_init(&result.radio, options->active_mask, options->slot_us, 0, 0);
    if (status != NL_OK) return status;
    result.options = *options;
    result.connected = options->connected;
    result.commit_failures = options->commit_failures;
    *backend = result;
    /* nl_radio queues reference their caller-owned radio storage. */
    for (uint8_t zone = 0; zone < NL_ZONE_COUNT; ++zone)
        backend->radio.tx[zone].storage = backend->radio.tx_storage[zone];
    backend->radio.rx.storage = backend->radio.rx_storage;
    return NL_OK;
}

nl_status nl_fault_backend_set_time(nl_fault_backend *backend, uint64_t now_us)
{
    if (backend == NULL || now_us < backend->now) return NL_ERR_ARGUMENT;
    backend->now = now_us;
    return NL_OK;
}

void nl_fault_backend_set_connected(nl_fault_backend *backend, bool connected)
{
    if (backend != NULL) backend->connected = connected;
}

void nl_fault_backend_fail_commits(nl_fault_backend *backend, uint32_t attempts)
{
    if (backend != NULL) backend->commit_failures = attempts;
}

bool nl_fault_backend_drained(const nl_fault_backend *backend)
{
    if (backend == NULL || backend->committing || backend->in_flight || backend->incoming != 0u ||
        backend->radio.rx.count != 0u) return false;
    for (uint8_t zone = 0; zone < NL_ZONE_COUNT; ++zone)
        if (backend->radio.tx[zone].count != 0u) return false;
    return true;
}

static nl_status start(void *context)
{
    nl_fault_backend *backend = context;
    if (backend == NULL) return NL_ERR_ARGUMENT;
    if (backend->started) return NL_ERR_BUSY;
    backend->started = true;
    ++backend->stats.starts;
    return NL_OK;
}

static nl_status can_stop(void *context)
{
    return nl_fault_backend_drained(context) ? NL_OK : NL_ERR_BUSY;
}

static void stop(void *context)
{
    nl_fault_backend *backend = context;
    if (backend == NULL || !backend->started) return;
    /* Normal module shutdown is gated by can_stop. Startup rollback must not
     * create transfers: only the driver event loop submits those after start. */
    backend->started = false;
    for (uint8_t zone = 0; zone < NL_ZONE_COUNT; ++zone) {
        backend->stats.canceled_pushes += backend->radio.tx[zone].count;
        backend->radio.tx[zone].head = backend->radio.tx[zone].count = 0;
    }
    backend->stats.canceled_receipts += backend->radio.rx.count;
    backend->radio.rx.head = backend->radio.rx.count = 0;
    backend->committing = false;
    ++backend->stats.stops;
}

static nl_status exchange(void *context, const nl_frame *request,
                          nl_frame *response, nl_pull_token *token)
{
    nl_fault_backend *backend = context;
    uint8_t bytes[NL_FRAME_MAX];
    nl_frame decoded;
    size_t size;
    nl_status status;
    bool push;
    if (backend == NULL || request == NULL || response == NULL || token == NULL)
        return NL_ERR_ARGUMENT;
    if (!backend->started) return NL_ERR_NOT_FOUND;
    push = request->command == NL_COMMAND_PUSH;
    if (!backend->connected) {
        if (push) { ++backend->stats.offline_pushes; ++backend->stats.rejected_pushes; }
        return NL_ERR_BUSY;
    }
    if (!push && backend->committing) return NL_ERR_BUSY;
    if (request->command == NL_COMMAND_PULL &&
        backend->now > UINT64_MAX - backend->options.commit_delay_us) return NL_ERR_SIZE;
    status = nl_frame_encode(request, bytes, sizeof(bytes), &size);
    if (status == NL_OK) status = nl_frame_decode(bytes, size, &decoded);
    if (status == NL_OK) status = nl_radio_handle_frame(&backend->radio, &decoded, response, token);
    if (push) {
        if (status == NL_OK) ++backend->stats.pushes;
        else ++backend->stats.rejected_pushes;
        return status;
    }
    if (status != NL_OK) return status;
    status = nl_frame_encode(response, bytes, sizeof(bytes), &size);
    if (status == NL_OK) status = nl_frame_decode(bytes, size, response);
    if (status != NL_OK) return status;
    backend->committing = true;
    backend->receipt = *response;
    backend->receipt_token = *token;
    backend->commit_at = backend->now + backend->options.commit_delay_us;
    ++backend->stats.receipts;
    return NL_OK;
}

static nl_status commit(void *context, const nl_frame *response, nl_pull_token token)
{
    nl_fault_backend *backend = context;
    uint8_t expected[NL_FRAME_MAX], actual[NL_FRAME_MAX];
    size_t expected_size, actual_size;
    nl_status status;
    if (backend == NULL || response == NULL) return NL_ERR_ARGUMENT;
    if (!backend->started) return NL_ERR_NOT_FOUND;
    if (!backend->committing || token != backend->receipt_token) {
        ++backend->stats.stale_commits;
        return NL_ERR_STALE;
    }
    status = nl_frame_encode(&backend->receipt, expected, sizeof(expected), &expected_size);
    if (status == NL_OK) status = nl_frame_encode(response, actual, sizeof(actual), &actual_size);
    if (status != NL_OK) return status;
    if (actual_size != expected_size || memcmp(actual, expected, actual_size) != 0)
        return NL_ERR_CONFLICT;
    if (!backend->connected || backend->now < backend->commit_at) {
        ++backend->stats.commit_retries;
        return NL_ERR_BUSY;
    }
    if (backend->commit_failures != 0u) {
        --backend->commit_failures;
        ++backend->stats.commit_retries;
        return NL_ERR_BUSY;
    }
    status = nl_radio_commit_pull(&backend->radio, response, token);
    if (status == NL_OK) { backend->committing = false; ++backend->stats.commits; }
    else if (status == NL_ERR_STALE || status == NL_ERR_EMPTY) {
        backend->committing = false;
        ++backend->stats.stale_commits;
    }
    return status;
}

nl_radio_link_config nl_fault_backend_link_config(nl_fault_backend *backend, uint16_t poll_budget)
{
    nl_radio_link_config config = {.exchange = exchange, .commit = commit, .start = start,
        .stop = stop, .can_stop = can_stop, .context = backend, .poll_budget = poll_budget};
    return config;
}

nl_status nl_fault_adapter_init(nl_fault_adapter *adapter, nl_fault_backend *backend,
                                uint16_t poll_budget)
{
    if (adapter == NULL || backend == NULL || poll_budget == 0u) return NL_ERR_ARGUMENT;
    memset(adapter, 0, sizeof(*adapter));
    adapter->backend = backend;
    adapter->config = nl_fault_backend_link_config(backend, poll_budget);
    return NL_OK;
}

nl_status nl_fault_adapter_start(void *context)
{
    nl_fault_adapter *adapter = context;
    nl_status status;
    if (adapter == NULL) return NL_ERR_ARGUMENT;
    if (adapter->owns_backend) return NL_ERR_BUSY;
    status = start(adapter->backend);
    if (status == NL_OK) adapter->owns_backend = true;
    return status;
}

void nl_fault_adapter_stop(void *context)
{
    nl_fault_adapter *adapter = context;
    if (adapter == NULL || !adapter->owns_backend) return;
    stop(adapter->backend);
    adapter->owns_backend = false;
    adapter->pending = adapter->settled = false;
}

nl_status nl_fault_adapter_can_stop(void *context)
{
    nl_fault_adapter *adapter = context;
    if (adapter == NULL) return NL_ERR_ARGUMENT;
    if (!adapter->owns_backend) return NL_OK;
    if (adapter->pending) return NL_ERR_BUSY;
    return can_stop(adapter->backend);
}

nl_status nl_fault_adapter_send(void *context, const nl_fragment *fragment)
{
    nl_fault_adapter *adapter = context;
    nl_frame request, response;
    nl_pull_token token;
    nl_status status;
    if (adapter == NULL) return NL_ERR_ARGUMENT;
    if (!adapter->owns_backend) return NL_ERR_NOT_FOUND;
    status = nl_frame_from_fragment(NL_COMMAND_PUSH, fragment, &request);
    if (status == NL_OK) status = exchange(adapter->backend, &request, &response, &token);
    if (status == NL_OK) ++adapter->stats.tx_accepted;
    else ++adapter->stats.tx_errors;
    return status;
}

void nl_fault_adapter_poll(nl_host *host, uint64_t now_us, void *context)
{
    nl_fault_adapter *adapter = context;
    const nl_frame request = {.command = NL_COMMAND_PULL};
    nl_status status;
    if (adapter == NULL || !adapter->owns_backend || host == NULL ||
        nl_fault_backend_set_time(adapter->backend, now_us) != NL_OK) return;
    for (uint16_t attempt = 0; attempt < adapter->config.poll_budget; ++attempt) {
        if (!adapter->pending) {
            status = exchange(adapter->backend, &request, &adapter->response, &adapter->token);
            if (status != NL_OK) {
                if (status != NL_ERR_EMPTY) ++adapter->stats.exchange_errors;
                return;
            }
            adapter->pending = true;
            adapter->settled = false;
            ++adapter->stats.rx_pulled;
        }
        if (!adapter->settled) {
            status = nl_host_receive_frame(host, &adapter->response, now_us);
            if (status == NL_ERR_BUSY) { ++adapter->stats.receive_retries; return; }
            adapter->settled = true;
            if (status == NL_OK) ++adapter->stats.rx_delivered;
            else ++adapter->stats.rx_discarded;
        }
        status = commit(adapter->backend, &adapter->response, adapter->token);
        if (status != NL_OK) {
            ++adapter->stats.commit_errors;
            if (status != NL_ERR_STALE && status != NL_ERR_EMPTY) return;
            ++adapter->stats.commit_abandoned;
        } else ++adapter->stats.commits;
        adapter->pending = adapter->settled = false;
    }
}

static nl_status scoped_exchange(void *context, const nl_frame *request,
                                 nl_frame *response, nl_pull_token *token)
{
    nl_fault_adapter *adapter = context;
    if (adapter == NULL || !adapter->owns_backend) return NL_ERR_NOT_FOUND;
    return exchange(adapter->backend, request, response, token);
}

static nl_status scoped_commit(void *context, const nl_frame *response, nl_pull_token token)
{
    nl_fault_adapter *adapter = context;
    if (adapter == NULL || !adapter->owns_backend) return NL_ERR_NOT_FOUND;
    return commit(adapter->backend, response, token);
}

nl_radio_link_config nl_fault_adapter_link_config(nl_fault_adapter *adapter)
{
    nl_radio_link_config config = {.exchange = scoped_exchange, .commit = scoped_commit,
        .start = nl_fault_adapter_start, .stop = nl_fault_adapter_stop,
        .can_stop = nl_fault_adapter_can_stop, .context = adapter,
        .poll_budget = adapter == NULL ? 0u : adapter->config.poll_budget};
    return config;
}

nl_status nl_fault_backend_invalidate_receipt(nl_fault_backend *backend)
{
    nl_status status;
    if (backend == NULL) return NL_ERR_ARGUMENT;
    if (!backend->committing) return NL_ERR_EMPTY;
    status = nl_radio_commit_pull(&backend->radio, &backend->receipt, backend->receipt_token);
    if (status != NL_OK) return status;
    backend->committing = false;
    ++backend->stats.invalidations;
    return NL_OK;
}

nl_status nl_fault_backend_restart(nl_fault_backend *backend)
{
    nl_pull_token next;
    nl_status status;
    if (backend == NULL) return NL_ERR_ARGUMENT;
    if (backend->started || !nl_fault_backend_drained(backend)) return NL_ERR_BUSY;
    next = backend->radio.next_rx_token;
    status = nl_radio_init(&backend->radio, backend->options.active_mask,
                           backend->options.slot_us, 0, 0);
    if (status != NL_OK) return status;
    backend->radio.next_rx_token = next;
    ++backend->stats.restarts;
    return NL_OK;
}

nl_status nl_fault_transfer_init(nl_fault_transfer *transfer, uint64_t delay_us)
{
    if (transfer == NULL) return NL_ERR_ARGUMENT;
    memset(transfer, 0, sizeof(*transfer));
    transfer->delay = delay_us;
    return NL_OK;
}

nl_status nl_fault_transfer_step(nl_fault_backend *sender, nl_fault_backend *receiver,
                                 nl_fault_transfer *transfer, uint64_t now_us)
{
    nl_fragment head, received;
    nl_window window;
    uint8_t bytes[NL_FRAGMENT_MAX];
    size_t size;
    nl_status status;
    if (sender == NULL || receiver == NULL || transfer == NULL || sender == receiver ||
        now_us < sender->now || now_us < receiver->now) return NL_ERR_ARGUMENT;
    if (transfer->pending && (transfer->sender != sender || transfer->receiver != receiver))
        return NL_ERR_CONFLICT;
    if (!sender->started || !receiver->started) return NL_ERR_NOT_FOUND;
    sender->now = receiver->now = now_us;
    if (!transfer->pending) {
        if (sender->in_flight || !sender->connected) return NL_ERR_BUSY;
        if (receiver->incoming == UINT_MAX) return NL_ERR_SIZE;
        if (now_us > UINT64_MAX - transfer->delay) return NL_ERR_SIZE;
        status = nl_radio_next_window(&sender->radio, now_us, &window);
        if (status != NL_OK && status != NL_ERR_BUSY) return status;
        status = nl_radio_prepare_tx(&sender->radio, now_us, &transfer->outgoing, &window);
        if (status != NL_OK) return status;
        status = nl_radio_peek_tx(&sender->radio, window.zone, &transfer->original);
        if (status != NL_OK) return status;
        status = nl_fragment_encode(&transfer->outgoing, transfer->bytes,
                                     sizeof(transfer->bytes), &transfer->size);
        if (status != NL_OK) return status;
        status = nl_fragment_encode(&transfer->original, transfer->original_bytes,
                                     sizeof(transfer->original_bytes), &transfer->original_size);
        if (status != NL_OK) return status;
        transfer->complete_at = now_us + transfer->delay;
        transfer->sender = sender;
        transfer->receiver = receiver;
        transfer->pending = sender->in_flight = true;
        ++receiver->incoming;
        return NL_ERR_BUSY;
    }
    status = nl_radio_peek_tx(&sender->radio, transfer->original.zone, &head);
    if (status != NL_OK) return NL_ERR_CONFLICT;
    status = nl_fragment_encode(&head, bytes, sizeof(bytes), &size);
    if (status != NL_OK) return status;
    if (size != transfer->original_size || memcmp(bytes, transfer->original_bytes, size) != 0)
        return NL_ERR_CONFLICT;
    status = nl_fragment_encode(&transfer->outgoing, bytes, sizeof(bytes), &size);
    if (status != NL_OK) return status;
    if (size != transfer->size || memcmp(bytes, transfer->bytes, size) != 0)
        return NL_ERR_CONFLICT;
    if (now_us < transfer->complete_at || !sender->connected || !receiver->connected)
        return NL_ERR_BUSY;
    status = nl_fragment_decode(transfer->bytes, transfer->size, &received);
    if (status != NL_OK) return status;
    status = nl_radio_receive(&receiver->radio, &received, now_us);
    if (status == NL_ERR_FULL) { ++transfer->blocked; return status; }
    if (status != NL_OK && status != NL_ERR_DUPLICATE && status != NL_ERR_STALE &&
        status != NL_ERR_ACCESS) return status;
    if (status != NL_OK) ++transfer->rejected;
    status = nl_radio_pop_tx(&sender->radio, transfer->original.zone, &head);
    if (status != NL_OK) return status;
    transfer->pending = sender->in_flight = false;
    --receiver->incoming;
    ++transfer->completed;
    return NL_OK;
}
