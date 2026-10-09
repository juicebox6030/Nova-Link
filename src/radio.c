#include <string.h>
#include "nova_link/radio.h"

nl_status nl_radio_init(nl_radio *radio, uint8_t active_mask, uint32_t slot_us,
                        uint32_t burst_extra_us, uint64_t idle_timeout_us)
{
    uint8_t zone;
    nl_scheduler scheduler;
    nl_status status;
    if (radio == NULL) return NL_ERR_ARGUMENT;
    status = nl_scheduler_init(&scheduler, active_mask, slot_us, burst_extra_us);
    if (status != NL_OK) return status;
    memset(radio, 0, sizeof(*radio));
    radio->scheduler = scheduler;
    nl_stream_init(&radio->streams, idle_timeout_us);
    for (zone = 0; zone < NL_ZONE_COUNT; ++zone)
        (void)nl_queue_init(&radio->tx[zone], radio->tx_storage[zone], NL_RADIO_TX_DEPTH);
    (void)nl_queue_init(&radio->rx, radio->rx_storage, NL_RADIO_RX_DEPTH);
    return NL_OK;
}

nl_status nl_radio_set_active(nl_radio *radio, uint8_t active_mask)
{
    uint8_t zone;
    if (radio == NULL || (active_mask & 1u) != 0u) return NL_ERR_ARGUMENT;
    for (zone = 1; zone < NL_ZONE_COUNT; ++zone)
        if ((active_mask & (uint8_t)(1u << zone)) == 0u && radio->tx[zone].count != 0u)
            return NL_ERR_BUSY;
    return nl_scheduler_set_active(&radio->scheduler, active_mask);
}

nl_status nl_radio_enqueue(nl_radio *radio, const nl_fragment *fragment)
{
    nl_status status = nl_fragment_validate(fragment);
    if (radio == NULL) return NL_ERR_ARGUMENT;
    if (status != NL_OK) return status;
    if (fragment->zone != 0u &&
        (radio->scheduler.active_mask & (uint8_t)(1u << fragment->zone)) == 0u) return NL_ERR_ACCESS;
    status = nl_queue_push(&radio->tx[fragment->zone], fragment);
    if (status == NL_ERR_FULL) ++radio->stats.tx_full;
    if (status == NL_OK && (fragment->flags & NL_FLAG_MGMT_LISTEN) != 0u)
        radio->management_listen = true;
    return status;
}

nl_status nl_radio_set_rx_policy(nl_radio *radio, nl_rx_policy policy)
{
    if (radio == NULL || (policy != NL_RX_FIFO && policy != NL_RX_LATEST_PER_STREAM)) return NL_ERR_ARGUMENT;
    if (radio->rx.count != 0u) return NL_ERR_BUSY;
    radio->rx_policy = policy;
    return NL_OK;
}

nl_status nl_radio_receive(nl_radio *radio, const nl_fragment *fragment, uint64_t now_us)
{
    nl_status control;
    size_t offset;
    nl_status status = nl_fragment_validate(fragment);
    if (radio == NULL) return NL_ERR_ARGUMENT;
    if (status != NL_OK) return status;
    if (fragment->zone != 0u &&
        (radio->scheduler.active_mask & (uint8_t)(1u << fragment->zone)) == 0u) return NL_ERR_ACCESS;
    status = nl_stream_check(&radio->streams, fragment, now_us);
    /* Timing control is independent of RX buffer ownership. Even a duplicate or
     * a fresh frame rejected for congestion can carry the current slot's hold.
     */
    if (status == NL_OK || status == NL_ERR_DUPLICATE) {
        if ((fragment->flags & NL_FLAG_BURST) != 0u) {
            control = nl_scheduler_hold_burst(&radio->scheduler, fragment->zone, now_us);
            if (control != NL_OK && control != NL_ERR_NOT_FOUND) return control;
        }
        if ((fragment->flags & NL_FLAG_MGMT_LISTEN) != 0u) radio->management_listen = true;
    }
    if (status != NL_OK) {
        if (status == NL_ERR_DUPLICATE) ++radio->stats.duplicates;
        if (status == NL_ERR_STALE) ++radio->stats.stale;
        return status;
    }
    if (radio->rx_policy == NL_RX_LATEST_PER_STREAM) {
        for (offset = 0; offset < radio->rx.count; ++offset) {
            size_t index = (radio->rx.head + offset) % radio->rx.capacity;
            nl_fragment *pending = &radio->rx.storage[index];
            if (pending->origin == fragment->origin && pending->zone == fragment->zone) {
                if (radio->next_rx_token == UINT64_MAX) return NL_ERR_SIZE;
                *pending = *fragment;
                radio->rx_tokens[index] = ++radio->next_rx_token;
                (void)nl_stream_accept(&radio->streams, fragment, now_us);
                ++radio->stats.received;
                ++radio->stats.coalesced;
                return NL_OK;
            }
        }
    }
    if (radio->rx.count == radio->rx.capacity) {
        ++radio->stats.rx_full;
        return NL_ERR_FULL;
    }
    if (radio->next_rx_token == UINT64_MAX) return NL_ERR_SIZE;
    status = nl_queue_push(&radio->rx, fragment);
    if (status != NL_OK) {
        if (status == NL_ERR_FULL) ++radio->stats.rx_full;
        return status;
    }
    radio->rx_tokens[(radio->rx.head + radio->rx.count - 1u) % radio->rx.capacity] = ++radio->next_rx_token;
    (void)nl_stream_accept(&radio->streams, fragment, now_us);
    ++radio->stats.received;
    return NL_OK;
}

bool nl_radio_ready(const nl_radio *radio)
{
    return radio != NULL && radio->rx.count != 0u;
}

nl_status nl_radio_pull(nl_radio *radio, nl_fragment *fragment)
{
    if (radio == NULL) return NL_ERR_ARGUMENT;
    return nl_queue_pop(&radio->rx, fragment);
}

nl_status nl_radio_prepare_pull(const nl_radio *radio, nl_frame *response, nl_pull_token *token)
{
    nl_fragment fragment;
    nl_status status;
    if (radio == NULL || response == NULL || token == NULL) return NL_ERR_ARGUMENT;
    status = nl_queue_peek(&radio->rx, &fragment);
    if (status != NL_OK) return status;
    status = nl_frame_from_fragment(NL_COMMAND_FRAGMENT, &fragment, response);
    if (status == NL_OK) *token = radio->rx_tokens[radio->rx.head];
    return status;
}

nl_status nl_radio_commit_pull(nl_radio *radio, const nl_frame *response, nl_pull_token token)
{
    nl_frame expected;
    nl_fragment discarded;
    nl_pull_token expected_token;
    nl_status status;
    if (radio == NULL) return NL_ERR_ARGUMENT;
    status = nl_frame_validate(response);
    if (status != NL_OK) return status;
    if (response->command != NL_COMMAND_FRAGMENT) return NL_ERR_UNSUPPORTED;
    status = nl_radio_prepare_pull(radio, &expected, &expected_token);
    if (status != NL_OK) return status;
    if (token != expected_token || expected.data_size != response->data_size ||
        memcmp(expected.data, response->data, expected.data_size) != 0) return NL_ERR_STALE;
    return nl_queue_pop(&radio->rx, &discarded);
}

nl_status nl_radio_next_window(nl_radio *radio, uint64_t now_us, nl_window *window)
{
    uint8_t zone, burst_mask = 0;
    nl_fragment head;
    nl_status status;
    bool management;
    if (radio == NULL || window == NULL) return NL_ERR_ARGUMENT;
    management = radio->management_listen || radio->tx[0].count != 0u;
    for (zone = 0; zone < NL_ZONE_COUNT; ++zone)
        if (nl_queue_peek(&radio->tx[zone], &head) == NL_OK && (head.flags & NL_FLAG_BURST) != 0u)
            burst_mask |= (uint8_t)(1u << zone);
    status = nl_scheduler_next(&radio->scheduler, now_us, management, burst_mask, window);
    if (status == NL_OK) {
        if (window->zone == 0u) radio->management_listen = false;
    }
    return status;
}

nl_status nl_radio_prepare_tx(nl_radio *radio, uint64_t now_us, nl_fragment *fragment, nl_window *window)
{
    nl_fragment head;
    nl_window current;
    nl_status status;
    if (radio == NULL || fragment == NULL || window == NULL) return NL_ERR_ARGUMENT;
    status = nl_scheduler_current(&radio->scheduler, now_us, &current);
    if (status != NL_OK) return status;
    status = nl_queue_peek(&radio->tx[current.zone], &head);
    if (status != NL_OK) return status;
    if ((head.flags & NL_FLAG_BURST) != 0u) {
        status = nl_scheduler_hold_burst(&radio->scheduler, current.zone, now_us);
        if (status != NL_OK) return status;
        status = nl_scheduler_current(&radio->scheduler, now_us, &current);
        if (status != NL_OK) return status;
    }
    *fragment = head;
    *window = current;
    return NL_OK;
}

nl_status nl_radio_peek_tx(const nl_radio *radio, uint8_t zone, nl_fragment *fragment)
{
    if (radio == NULL || zone >= NL_ZONE_COUNT) return NL_ERR_ARGUMENT;
    return nl_queue_peek(&radio->tx[zone], fragment);
}

nl_status nl_radio_pop_tx(nl_radio *radio, uint8_t zone, nl_fragment *fragment)
{
    if (radio == NULL || zone >= NL_ZONE_COUNT) return NL_ERR_ARGUMENT;
    return nl_queue_pop(&radio->tx[zone], fragment);
}

void nl_radio_request_management(nl_radio *radio)
{
    if (radio != NULL) radio->management_listen = true;
}

nl_status nl_radio_handle_frame(nl_radio *radio, const nl_frame *request, nl_frame *response, nl_pull_token *token)
{
    nl_fragment fragment;
    nl_status status;
    if (radio == NULL) return NL_ERR_ARGUMENT;
    status = nl_frame_validate(request);
    if (status != NL_OK) return status;
    if (request->command == NL_COMMAND_PUSH) {
        status = nl_frame_to_fragment(request, &fragment);
        return status == NL_OK ? nl_radio_enqueue(radio, &fragment) : status;
    }
    if (request->command == NL_COMMAND_PULL) {
        return nl_radio_prepare_pull(radio, response, token);
    }
    return NL_ERR_UNSUPPORTED;
}
