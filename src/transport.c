#include <string.h>
#include "nova_link/transport.h"

/* Nibble-wise CRC-16/CCITT: a 32-byte table instead of 512, two lookups per byte. */
static const uint16_t crc_nibble[16] = {
    0x0000u, 0x1021u, 0x2042u, 0x3063u, 0x4084u, 0x50A5u, 0x60C6u, 0x70E7u,
    0x8108u, 0x9129u, 0xA14Au, 0xB16Bu, 0xC18Cu, 0xD1ADu, 0xE1CEu, 0xF1EFu
};

static inline uint16_t crc_byte(uint16_t crc, uint8_t byte)
{
    crc = (uint16_t)((uint16_t)(crc << 4) ^ crc_nibble[(unsigned)(crc >> 12) ^ (unsigned)(byte >> 4)]);
    return (uint16_t)((uint16_t)(crc << 4) ^ crc_nibble[(unsigned)(crc >> 12) ^ (unsigned)(byte & 0x0Fu)]);
}

uint16_t nl_crc16(uint16_t crc, const uint8_t *bytes, size_t size)
{
    size_t index;
    if (bytes == NULL) return crc;
    for (index = 0; index < size; ++index) crc = crc_byte(crc, bytes[index]);
    return crc;
}

/* Validate a command/length pair before any output is written. */
static nl_status check_frame(uint8_t command, size_t data_size)
{
    switch (command) {
    case NL_COMMAND_PING:
    case NL_COMMAND_PULL:
    case NL_COMMAND_STATUS:
        return data_size == 0u ? NL_OK : NL_ERR_SIZE;
    case NL_COMMAND_PUSH:
    case NL_COMMAND_FRAGMENT:
        return data_size >= NL_FRAGMENT_MIN && data_size <= NL_FRAGMENT_MAX
            ? NL_OK : NL_ERR_SIZE;
    default: return NL_ERR_UNSUPPORTED;
    }
}

nl_status nl_frame_validate(const nl_frame *frame)
{
    if (frame == NULL) return NL_ERR_ARGUMENT;
    return check_frame(frame->command, frame->data_size);
}

nl_status nl_frame_from_fragment(uint8_t command, const nl_fragment *fragment, nl_frame *frame)
{
    size_t size = 0;
    nl_status status;
    if (frame == NULL) return NL_ERR_ARGUMENT;
    if (command != NL_COMMAND_PUSH && command != NL_COMMAND_FRAGMENT) return NL_ERR_UNSUPPORTED;
    /* Encoding validates before writing, so frame stays unchanged on error. */
    status = nl_fragment_encode(fragment, frame->data, sizeof(frame->data), &size);
    if (status != NL_OK) return status;
    frame->command = command;
    frame->data_size = (uint8_t)size;
    return NL_OK;
}

nl_status nl_frame_to_fragment(const nl_frame *frame, nl_fragment *fragment)
{
    nl_status status = nl_frame_validate(frame);
    if (status != NL_OK) return status;
    if (frame->command != NL_COMMAND_PUSH && frame->command != NL_COMMAND_FRAGMENT)
        return NL_ERR_UNSUPPORTED;
    return nl_fragment_decode(frame->data, frame->data_size, fragment);
}

nl_status nl_frame_encode(const nl_frame *frame, uint8_t *bytes, size_t capacity, size_t *size)
{
    nl_status status = nl_frame_validate(frame);
    size_t required;
    uint16_t crc;
    if (status != NL_OK) return status;
    if (bytes == NULL || size == NULL) return NL_ERR_ARGUMENT;
    required = NL_FRAME_MIN + frame->data_size;
    if (capacity < required) return NL_ERR_SIZE;
    bytes[0] = NL_TRANSPORT_SYNC;
    bytes[1] = (uint8_t)(1u + frame->data_size);
    bytes[2] = frame->command;
    memcpy(bytes + 3, frame->data, frame->data_size);
    crc = nl_crc16(0xFFFFu, bytes + 1, required - 3u);
    bytes[required - 2u] = (uint8_t)(crc >> 8);
    bytes[required - 1u] = (uint8_t)crc;
    *size = required;
    return NL_OK;
}

nl_status nl_frame_decode(const uint8_t *bytes, size_t size, nl_frame *frame)
{
    nl_status status;
    uint8_t data_size;
    if (bytes == NULL || frame == NULL) return NL_ERR_ARGUMENT;
    if (size < NL_FRAME_MIN || size > NL_FRAME_MAX) return NL_ERR_SIZE;
    if (bytes[0] != NL_TRANSPORT_SYNC) return NL_ERR_FORMAT;
    if (bytes[1] == 0u || bytes[1] > NL_FRAME_BODY_MAX ||
        size != (size_t)bytes[1] + 2u + NL_FRAME_CRC_SIZE)
        return NL_ERR_SIZE;
    /* Check integrity before interpreting the command byte. */
    if (nl_crc16(0xFFFFu, bytes + 1, size - 1u) != 0u) return NL_ERR_INTEGRITY;
    data_size = (uint8_t)(bytes[1] - 1u);
    status = check_frame(bytes[2], data_size);
    if (status != NL_OK) return status;
    frame->command = bytes[2];
    frame->data_size = data_size;
    memmove(frame->data, bytes + 3, data_size);
    return NL_OK;
}

void nl_parser_reset(nl_parser *parser)
{
    /* Body bytes are only read below `used`, so they need no clearing. */
    if (parser == NULL) return;
    parser->state = 0;
    parser->expected = 0;
    parser->used = 0;
    parser->crc = 0;
}

nl_parse_result nl_parser_feed(nl_parser *parser, uint8_t byte, nl_frame *frame)
{
    uint8_t data_size;
    if (parser == NULL || frame == NULL) return NL_PARSE_REJECTED;
    switch (parser->state) {
    case 0u:
        if (byte == NL_TRANSPORT_SYNC) parser->state = 1;
        return NL_PARSE_WAIT;
    case 1u:
        if (byte == 0u || byte > NL_FRAME_BODY_MAX) {
            parser->state = byte == NL_TRANSPORT_SYNC ? 1u : 0u;
            return NL_PARSE_REJECTED;
        }
        parser->expected = byte;
        parser->used = 0;
        parser->crc = crc_byte(0xFFFFu, byte);
        parser->state = 2;
        return NL_PARSE_WAIT;
    case 2u:
        /* Guard the body index against a corrupted or never-reset parser. */
        if (parser->used >= parser->expected || parser->expected > NL_FRAME_BODY_MAX) break;
        parser->body[parser->used++] = byte;
        parser->crc = crc_byte(parser->crc, byte);
        if (parser->used == parser->expected) parser->state = 3;
        return NL_PARSE_WAIT;
    case 3u:
        parser->crc = crc_byte(parser->crc, byte);
        parser->state = 4;
        return NL_PARSE_WAIT;
    case 4u:
        parser->state = 0;
        if (crc_byte(parser->crc, byte) != 0u) return NL_PARSE_REJECTED;
        data_size = (uint8_t)(parser->expected - 1u);
        if (check_frame(parser->body[0], data_size) != NL_OK) return NL_PARSE_REJECTED;
        frame->command = parser->body[0];
        frame->data_size = data_size;
        memcpy(frame->data, parser->body + 1, data_size);
        return NL_PARSE_READY;
    default:
        break;
    }
    nl_parser_reset(parser);
    return NL_PARSE_REJECTED;
}
