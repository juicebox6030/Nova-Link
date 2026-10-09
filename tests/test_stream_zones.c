#include "test.h"

static void sequences(void)
{
    nl_stream_tracker tracker;
    nl_fragment value = fragment(1, 2, 254);
    unsigned old, next;
    nl_stream_init(&tracker, 0);
    STATUS(nl_stream_accept(&tracker, &value, 0), NL_OK);
    STATUS(nl_stream_accept(&tracker, &value, 1), NL_ERR_DUPLICATE);
    value.sequence = 255;
    STATUS(nl_stream_accept(&tracker, &value, 2), NL_OK);
    value.sequence = 0;
    STATUS(nl_stream_accept(&tracker, &value, 3), NL_OK);
    value.sequence = 255;
    STATUS(nl_stream_accept(&tracker, &value, 4), NL_ERR_STALE);
    value.sequence = 128;
    STATUS(nl_stream_accept(&tracker, &value, 5), NL_ERR_STALE);
    value.origin = 2;
    STATUS(nl_stream_accept(&tracker, &value, 6), NL_OK);
    value.zone = 3;
    STATUS(nl_stream_accept(&tracker, &value, 7), NL_OK);
    STATUS(nl_stream_accept(&tracker, &value, 6), NL_ERR_ARGUMENT);
    /* All possible previous/current sequence pairs, including wraparound. */
    for (old = 0; old < 256u; ++old) {
        nl_stream_init(&tracker, 0);
        value.sequence = (uint8_t)old;
        STATUS(nl_stream_accept(&tracker, &value, 0), NL_OK);
        for (next = 0; next < 256u; ++next) {
            uint8_t delta = (uint8_t)(next - old);
            value.sequence = (uint8_t)next;
            STATUS(nl_stream_check(&tracker, &value, 1),
                delta == 0u ? NL_ERR_DUPLICATE : delta < 128u ? NL_OK : NL_ERR_STALE);
        }
    }
    nl_stream_init(&tracker, 100);
    value.sequence = 99;
    STATUS(nl_stream_accept(&tracker, &value, 1000), NL_OK);
    value.sequence = 0;
    STATUS(nl_stream_accept(&tracker, &value, 1099), NL_ERR_STALE);
    STATUS(nl_stream_accept(&tracker, &value, 1100), NL_OK);
    STATUS(nl_stream_reset_origin(&tracker, value.origin), NL_OK);
    STATUS(nl_stream_accept(&tracker, &value, 1101), NL_OK);
    STATUS(nl_stream_reset_origin(&tracker, 8), NL_ERR_ARGUMENT);
}

static void claims(void)
{
    nl_zone_table zones;
    uint8_t plugin;
    nl_zones_init(&zones);
    CHECK(nl_zones_active_mask(&zones) == 0);
    for (plugin = 0; plugin < NL_PLUGIN_MAX; ++plugin) {
        CHECK(nl_zones_can_read(&zones, plugin, 0));
        CHECK(nl_zones_can_write(&zones, plugin, 0));
        STATUS(nl_zones_claim(&zones, plugin, 1, NL_ZONE_READ_ONLY), NL_OK);
        CHECK(nl_zones_can_read(&zones, plugin, 1));
        CHECK(!nl_zones_can_write(&zones, plugin, 1));
    }
    STATUS(nl_zones_claim(&zones, 0, 1, NL_ZONE_EXCLUSIVE), NL_ERR_CONFLICT);
    for (plugin = 1; plugin < NL_PLUGIN_MAX; ++plugin) nl_zones_release_plugin(&zones, plugin);
    STATUS(nl_zones_claim(&zones, 0, 1, NL_ZONE_EXCLUSIVE), NL_OK);
    STATUS(nl_zones_claim(&zones, 0, 1, NL_ZONE_EXCLUSIVE), NL_OK);
    CHECK(nl_zones_can_write(&zones, 0, 1));
    STATUS(nl_zones_claim(&zones, 1, 1, NL_ZONE_READ_ONLY), NL_ERR_CONFLICT);
    STATUS(nl_zones_claim(&zones, 1, 1, NL_ZONE_EXCLUSIVE), NL_ERR_CONFLICT);
    STATUS(nl_zones_claim(&zones, 0, 1, NL_ZONE_READ_ONLY), NL_OK);
    CHECK(!nl_zones_can_write(&zones, 0, 1));
    STATUS(nl_zones_claim(&zones, 15, 7, NL_ZONE_EXCLUSIVE), NL_OK);
    CHECK(nl_zones_active_mask(&zones) == 0x82);
    STATUS(nl_zones_release(&zones, 15, 7), NL_OK);
    STATUS(nl_zones_release(&zones, 15, 7), NL_ERR_NOT_FOUND);
    STATUS(nl_zones_claim(&zones, 0, 0, NL_ZONE_EXCLUSIVE), NL_ERR_ACCESS);
    STATUS(nl_zones_release(&zones, 0, 0), NL_ERR_ACCESS);
    STATUS(nl_zones_claim(&zones, 16, 1, NL_ZONE_EXCLUSIVE), NL_ERR_ARGUMENT);
    STATUS(nl_zones_claim(&zones, 0, 8, NL_ZONE_EXCLUSIVE), NL_ERR_ARGUMENT);
    STATUS(nl_zones_claim(&zones, 0, 1, (nl_zone_mode)99), NL_ERR_ARGUMENT);
    CHECK(!nl_zones_can_read(&zones, 16, 0));
    nl_zones_release_plugin(&zones, 0);
    CHECK(nl_zones_active_mask(&zones) == 0);
}

static void fifo(void)
{
    nl_queue queue;
    nl_fragment storage[3], value = fragment(0, 1, 0), output;
    unsigned iteration;
    STATUS(nl_queue_init(&queue, storage, 0), NL_ERR_ARGUMENT);
    STATUS(nl_queue_init(&queue, storage, 3), NL_OK);
    STATUS(nl_queue_pop(&queue, &output), NL_ERR_EMPTY);
    for (iteration = 0; iteration < 300u; ++iteration) {
        value.sequence = (uint8_t)iteration;
        STATUS(nl_queue_push(&queue, &value), NL_OK);
        STATUS(nl_queue_peek(&queue, &output), NL_OK);
        same_fragment(&value, &output);
        STATUS(nl_queue_pop(&queue, &output), NL_OK);
        same_fragment(&value, &output);
        CHECK(queue.count == 0);
    }
    for (iteration = 0; iteration < 3; ++iteration) {
        value.sequence = (uint8_t)iteration;
        STATUS(nl_queue_push(&queue, &value), NL_OK);
    }
    STATUS(nl_queue_push(&queue, &value), NL_ERR_FULL);
    STATUS(nl_queue_pop(&queue, NULL), NL_ERR_ARGUMENT);
    CHECK(queue.count == 3);
    for (iteration = 0; iteration < 3; ++iteration) {
        STATUS(nl_queue_pop(&queue, &output), NL_OK);
        CHECK(output.sequence == iteration);
    }
}

int main(void)
{
    sequences();
    claims();
    fifo();
    puts("stream/zones: all sequence pairs, claim conflicts and bounded FIFO passed");
    return EXIT_SUCCESS;
}
