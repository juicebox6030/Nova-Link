#ifndef NOVA_LINK_TRANSPORT_H
#define NOVA_LINK_TRANSPORT_H

#include "nova_link/fragment.h"

/** @file transport.h Hardware-independent framing for a byte-stream adapter. */
#define NL_TRANSPORT_SYNC 0xAAu
#define NL_COMMAND_PING 0x01u
#define NL_COMMAND_PULL 0x02u
#define NL_COMMAND_PUSH 0x03u
#define NL_COMMAND_STATUS 0x04u
#define NL_COMMAND_FRAGMENT 0xD0u
#define NL_FRAME_BODY_MAX (1u + NL_FRAGMENT_MAX)
#define NL_FRAME_MAX (2u + NL_FRAME_BODY_MAX)

typedef struct {
    uint8_t command;
    uint8_t data_size;
    uint8_t data[NL_FRAGMENT_MAX];
} nl_frame;

/** Validate command and length; PING, PULL and STATUS are requests without data. */
nl_status nl_frame_validate(const nl_frame *frame);
/** Make a PUSH or FRAGMENT frame from a validated fragment. */
nl_status nl_frame_from_fragment(uint8_t command, const nl_fragment *fragment, nl_frame *frame);
/** Extract a fragment from a PUSH or FRAGMENT frame. */
nl_status nl_frame_to_fragment(const nl_frame *frame, nl_fragment *fragment);
/** Encode [0xAA][body length including command][command][data]. */
nl_status nl_frame_encode(const nl_frame *frame, uint8_t *bytes, size_t capacity, size_t *size);
/** Decode exactly one complete frame. */
nl_status nl_frame_decode(const uint8_t *bytes, size_t size, nl_frame *frame);

typedef enum { NL_PARSE_WAIT, NL_PARSE_READY, NL_PARSE_REJECTED } nl_parse_result;
typedef struct {
    uint8_t state;
    uint8_t expected;
    uint8_t used;
    uint8_t body[NL_FRAME_BODY_MAX];
} nl_parser;

/** Clear partial input, including at an adapter's transaction boundary/timeout. */
void nl_parser_reset(nl_parser *parser);
/** Feed one byte. READY writes a complete frame; other results leave it unchanged. */
nl_parse_result nl_parser_feed(nl_parser *parser, uint8_t byte, nl_frame *frame);

#endif
