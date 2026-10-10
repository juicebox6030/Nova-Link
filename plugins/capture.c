#include <string.h>
#include "nova_link/capture_plugin.h"

typedef struct { char *data; size_t size, limit; bool full; } writer;

static void character(writer *out, char value)
{
    if (out->size == out->limit) { out->full = true; return; }
    if (out->data != NULL) out->data[out->size] = value;
    ++out->size;
}

static void literal(writer *out, const char *value)
{
    while (*value != '\0' && !out->full) character(out, *value++);
}

static void integer(writer *out, uint64_t value)
{
    char digits[20];
    size_t count = 0;
    do { digits[count++] = (char)('0' + (value % 10u)); value /= 10u; } while (value != 0u);
    while (count != 0u) character(out, digits[--count]);
}

static bool overlaps(const void *a, size_t a_size, const void *b, size_t b_size)
{
    uintptr_t x = (uintptr_t)a, y = (uintptr_t)b;
    if (a_size == 0u || b_size == 0u) return false;
    return x <= y ? y - x < a_size : x - y < b_size;
}

/* Match the analyzer's Python str.strip() whitespace definition. */
static bool whitespace(uint32_t codepoint)
{
    return (codepoint >= 0x09u && codepoint <= 0x0du) ||
           (codepoint >= 0x1cu && codepoint <= 0x20u) || codepoint == 0x85u ||
           codepoint == 0xa0u || codepoint == 0x1680u ||
           (codepoint >= 0x2000u && codepoint <= 0x200au) ||
           codepoint == 0x2028u || codepoint == 0x2029u || codepoint == 0x202fu ||
           codepoint == 0x205fu || codepoint == 0x3000u;
}

/* Reject malformed UTF-8 so generated JSON is accepted by strict readers. */
static nl_status text_size(const char *text, size_t limit, size_t *size)
{
    size_t i = 0;
    unsigned remaining = 0;
    uint32_t codepoint = 0, minimum = 0;
    bool nonblank = false;
    if (text == NULL) return NL_ERR_ARGUMENT;
    while (i < limit && text[i] != '\0') {
        unsigned byte = (unsigned char)text[i++];
        if (remaining != 0u) {
            if ((byte & 0xc0u) != 0x80u) return NL_ERR_ARGUMENT;
            codepoint = (codepoint << 6u) | (byte & 0x3fu);
            --remaining;
            if (remaining == 0u && (codepoint < minimum || codepoint > 0x10ffffu ||
                (codepoint >= 0xd800u && codepoint <= 0xdfffu))) return NL_ERR_ARGUMENT;
            if (remaining == 0u && !whitespace(codepoint)) nonblank = true;
        } else if (byte >= 0x80u) {
            if (byte >= 0xc2u && byte <= 0xdfu) { remaining = 1; codepoint = byte & 0x1fu; minimum = 0x80u; }
            else if (byte >= 0xe0u && byte <= 0xefu) { remaining = 2; codepoint = byte & 0x0fu; minimum = 0x800u; }
            else if (byte >= 0xf0u && byte <= 0xf4u) { remaining = 3; codepoint = byte & 0x07u; minimum = 0x10000u; }
            else return NL_ERR_ARGUMENT;
        } else if (!whitespace(byte)) {
            nonblank = true;
        }
    }
    if (i == limit) return NL_ERR_SIZE;
    if (!nonblank || remaining != 0u) return NL_ERR_ARGUMENT;
    *size = i;
    return NL_OK;
}

static void string(writer *out, const char *value)
{
    static const char hex[] = "0123456789abcdef";
    character(out, '"');
    while (*value != '\0' && !out->full) {
        unsigned byte = (unsigned char)*value++;
        if (byte == '"' || byte == '\\') { character(out, '\\'); character(out, (char)byte); }
        else if (byte < 0x20u) {
            literal(out, "\\u00");
            character(out, hex[byte >> 4u]); character(out, hex[byte & 0x0fu]);
        } else character(out, (char)byte);
    }
    character(out, '"');
}

static void record(writer *out, const nl_capture_observation *observation, const char *stimulus)
{
    static const char hex[] = "0123456789abcdef";
    const char *crc = observation->crc == NL_CAPTURE_CRC_OK ? "ok" :
                      observation->crc == NL_CAPTURE_CRC_BAD ? "bad" : "unknown";
    size_t i;
    literal(out, "{\"timestamp_us\":"); integer(out, observation->timestamp_us);
    literal(out, ",\"frequency_hz\":"); integer(out, observation->frequency_hz);
    literal(out, ",\"profile\":"); string(out, observation->profile);
    literal(out, ",\"stimulus\":"); string(out, stimulus);
    literal(out, ",\"payload_hex\":\"");
    for (i = 0; i < observation->payload_length && !out->full; ++i) {
        character(out, hex[observation->payload[i] >> 4u]);
        character(out, hex[observation->payload[i] & 0x0fu]);
    }
    literal(out, "\",\"crc\":"); string(out, crc);
    literal(out, ",\"rssi_dbm\":");
    if (!observation->has_rssi) literal(out, "null");
    else {
        int32_t rssi = observation->rssi_dbm;
        if (rssi < 0) { character(out, '-'); rssi = -rssi; }
        integer(out, (uint64_t)rssi);
    }
    literal(out, "}\n");
}

nl_status nl_capture_init(nl_capture_context *capture, const nl_capture_config *config)
{
    nl_capture_config saved;
    if (capture == NULL || config == NULL || config->buffer == NULL ||
        config->capacity == 0u || config->output == NULL ||
        overlaps(capture, sizeof(*capture), config->buffer, config->capacity)) return NL_ERR_ARGUMENT;
    saved = *config;
    memset(capture, 0, sizeof(*capture));
    capture->config = saved;
    capture->plugin = NL_PLUGIN_ID_NONE;
    capture->config.buffer[0] = '\0';
    return NL_OK;
}

nl_status nl_capture_submit(nl_capture_context *capture, const nl_capture_observation *observation)
{
    size_t profile_size, stimulus_size;
    const char *stimulus;
    nl_status status;
    writer out;
    if (capture == NULL || observation == NULL) return NL_ERR_ARGUMENT;
    if (capture->outputting || capture->pending) return NL_ERR_BUSY;
    if (capture->host == NULL) return NL_ERR_ACCESS;
    if (observation->frequency_hz < UINT32_C(2400000000) ||
        observation->frequency_hz > UINT32_C(2483500000) ||
        (observation->crc != NL_CAPTURE_CRC_UNKNOWN && observation->crc != NL_CAPTURE_CRC_OK &&
         observation->crc != NL_CAPTURE_CRC_BAD) ||
        (observation->payload_length != 0u && observation->payload == NULL)) return NL_ERR_ARGUMENT;
    if (capture->have_timestamp && observation->timestamp_us < capture->last_timestamp_us) return NL_ERR_STALE;
    if (observation->payload_length > capture->config.capacity / 2u) return NL_ERR_SIZE;
    stimulus = observation->stimulus != NULL ? observation->stimulus : "unspecified";
    status = text_size(observation->profile, capture->config.capacity, &profile_size);
    if (status != NL_OK) return status;
    status = text_size(stimulus, capture->config.capacity, &stimulus_size);
    if (status != NL_OK) return status;
    if (overlaps(observation, sizeof(*observation), capture->config.buffer, capture->config.capacity) ||
        overlaps(observation->profile, profile_size + 1u, capture->config.buffer, capture->config.capacity) ||
        overlaps(stimulus, stimulus_size + 1u, capture->config.buffer, capture->config.capacity) ||
        overlaps(observation->payload, observation->payload_length, capture->config.buffer, capture->config.capacity) ||
        overlaps(observation, sizeof(*observation), capture, sizeof(*capture)) ||
        overlaps(observation->profile, profile_size + 1u, capture, sizeof(*capture)) ||
        overlaps(stimulus, stimulus_size + 1u, capture, sizeof(*capture)) ||
        overlaps(observation->payload, observation->payload_length, capture, sizeof(*capture))) return NL_ERR_ARGUMENT;
    out = (writer){.limit = capture->config.capacity - 1u};
    record(&out, observation, stimulus);
    if (out.full) return NL_ERR_SIZE;
    out = (writer){.data = capture->config.buffer, .limit = capture->config.capacity - 1u};
    record(&out, observation, stimulus);
    capture->config.buffer[out.size] = '\0';
    capture->pending_length = out.size;
    capture->pending = true;
    capture->have_timestamp = true;
    capture->last_timestamp_us = observation->timestamp_us;
    return NL_OK;
}

nl_status nl_capture_flush(nl_capture_context *capture)
{
    nl_status status;
    if (capture == NULL) return NL_ERR_ARGUMENT;
    if (capture->outputting) return NL_ERR_BUSY;
    if (capture->host == NULL) return NL_ERR_ACCESS;
    if (!capture->pending) return NL_ERR_EMPTY;
    capture->outputting = true;
    status = capture->config.output(capture->config.output_context,
                                    capture->config.buffer, capture->pending_length);
    capture->outputting = false;
    capture->last_status = status;
    if (status == NL_OK) { capture->pending = false; capture->pending_length = 0; }
    return status;
}

bool nl_capture_pending(const nl_capture_context *capture)
{
    return capture != NULL && capture->pending;
}

static nl_status start(nl_host *host, nl_plugin_id plugin, void *context)
{
    nl_capture_context *capture = context;
    if (capture == NULL || capture->config.buffer == NULL || capture->config.capacity == 0u ||
        capture->config.output == NULL) return NL_ERR_ARGUMENT;
    if (capture->host != NULL) return NL_ERR_BUSY;
    capture->host = host;
    capture->plugin = plugin;
    return NL_OK;
}

static nl_status can_stop(nl_host *host, nl_plugin_id plugin, void *context)
{
    nl_capture_context *capture = context;
    if (capture == NULL || capture->host != host || capture->plugin != plugin) return NL_OK;
    return capture->pending || capture->outputting ? NL_ERR_BUSY : NL_OK;
}

static void stop(nl_host *host, nl_plugin_id plugin, void *context)
{
    nl_capture_context *capture = context;
    if (capture == NULL || capture->host != host || capture->plugin != plugin || capture->outputting) return;
    capture->host = NULL;
    capture->plugin = NL_PLUGIN_ID_NONE;
    capture->pending = false;
    capture->pending_length = 0;
    capture->have_timestamp = false;
    capture->config.buffer[0] = '\0';
}

static void poll(nl_host *host, nl_plugin_id plugin, uint64_t now_us, void *context)
{
    nl_capture_context *capture = context;
    (void)now_us;
    if (capture != NULL && capture->host == host && capture->plugin == plugin && capture->pending)
        (void)nl_capture_flush(capture);
}

nl_plugin nl_capture_plugin(nl_capture_context *capture)
{
    nl_plugin plugin = {.start = start, .stop = stop, .context = capture, .poll = poll, .can_stop = can_stop};
    return plugin;
}

nl_module nl_capture_module(nl_capture_context *capture)
{
    nl_module module = {.name = "capture", .version = "1", .kind = NL_MODULE_SERVICE,
                        .service = capture, .hooks = nl_capture_plugin(capture)};
    return module;
}
