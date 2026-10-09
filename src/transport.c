#include <string.h>
#include "nova_link/transport.h"

nl_status nl_frame_validate(const nl_frame *frame)
{
    if (frame == NULL) return NL_ERR_ARGUMENT;
    switch (frame->command) {
    case NL_COMMAND_PING:
    case NL_COMMAND_PULL:
    case NL_COMMAND_STATUS:
        return frame->data_size == 0u ? NL_OK : NL_ERR_SIZE;
    case NL_COMMAND_PUSH:
    case NL_COMMAND_FRAGMENT:
        return frame->data_size >= NL_FRAGMENT_MIN && frame->data_size <= NL_FRAGMENT_MAX
            ? NL_OK : NL_ERR_SIZE;
    default: return NL_ERR_UNSUPPORTED;
    }
}

nl_status nl_frame_from_fragment(uint8_t command, const nl_fragment *fragment, nl_frame *frame)
{
    nl_frame encoded = {0};
    size_t size = 0;
    nl_status status;
    if (frame == NULL) return NL_ERR_ARGUMENT;
    if (command != NL_COMMAND_PUSH && command != NL_COMMAND_FRAGMENT) return NL_ERR_UNSUPPORTED;
    status = nl_fragment_encode(fragment, encoded.data, sizeof(encoded.data), &size);
    if (status != NL_OK) return status;
    encoded.command = command;
    encoded.data_size = (uint8_t)size;
    *frame = encoded;
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
    if (status != NL_OK) return status;
    if (bytes == NULL || size == NULL) return NL_ERR_ARGUMENT;
    required = 3u + frame->data_size;
    if (capacity < required) return NL_ERR_SIZE;
    bytes[0] = NL_TRANSPORT_SYNC;
    bytes[1] = (uint8_t)(1u + frame->data_size);
    bytes[2] = frame->command;
    memcpy(bytes + 3, frame->data, frame->data_size);
    *size = required;
    return NL_OK;
}

nl_status nl_frame_decode(const uint8_t *bytes, size_t size, nl_frame *frame)
{
    nl_frame decoded = {0};
    nl_status status;
    if (bytes == NULL || frame == NULL) return NL_ERR_ARGUMENT;
    if (size < 3u || size > NL_FRAME_MAX) return NL_ERR_SIZE;
    if (bytes[0] != NL_TRANSPORT_SYNC) return NL_ERR_FORMAT;
    if (bytes[1] == 0u || bytes[1] > NL_FRAME_BODY_MAX || size != (size_t)bytes[1] + 2u)
        return NL_ERR_SIZE;
    decoded.command = bytes[2];
    decoded.data_size = (uint8_t)(bytes[1] - 1u);
    memcpy(decoded.data, bytes + 3, decoded.data_size);
    status = nl_frame_validate(&decoded);
    if (status != NL_OK) return status;
    *frame = decoded;
    return NL_OK;
}

void nl_parser_reset(nl_parser *parser)
{
    if (parser != NULL) memset(parser, 0, sizeof(*parser));
}

nl_parse_result nl_parser_feed(nl_parser *parser, uint8_t byte, nl_frame *frame)
{
    nl_frame decoded = {0};
    if (parser == NULL || frame == NULL) return NL_PARSE_REJECTED;
    if (parser->state == 0u) {
        if (byte == NL_TRANSPORT_SYNC) parser->state = 1;
        return NL_PARSE_WAIT;
    }
    if (parser->state == 1u) {
        if (byte == 0u || byte > NL_FRAME_BODY_MAX) {
            nl_parser_reset(parser);
            if (byte == NL_TRANSPORT_SYNC) parser->state = 1;
            return NL_PARSE_REJECTED;
        }
        parser->expected = byte;
        parser->used = 0;
        parser->state = 2;
        return NL_PARSE_WAIT;
    }
    parser->body[parser->used++] = byte;
    if (parser->used != parser->expected) return NL_PARSE_WAIT;
    decoded.command = parser->body[0];
    decoded.data_size = (uint8_t)(parser->expected - 1u);
    memcpy(decoded.data, parser->body + 1, decoded.data_size);
    nl_parser_reset(parser);
    if (nl_frame_validate(&decoded) != NL_OK) return NL_PARSE_REJECTED;
    *frame = decoded;
    return NL_PARSE_READY;
}
