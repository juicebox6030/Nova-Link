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
/** LEN counts COMMAND + DATA; the 2-byte CRC follows the body and is not counted. */
#define NL_FRAME_BODY_MAX (1u + NL_FRAGMENT_MAX)
#define NL_FRAME_CRC_SIZE 2u
#define NL_FRAME_MIN (2u + 1u + NL_FRAME_CRC_SIZE)
#define NL_FRAME_MAX (2u + NL_FRAME_BODY_MAX + NL_FRAME_CRC_SIZE)

typedef struct {
    uint8_t command;
    uint8_t data_size;
    uint8_t data[NL_FRAGMENT_MAX];
} nl_frame;

/** CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF, no reflection, no xorout).
 * Chain calls by passing the previous result; start with 0xFFFF. Running a
 * message followed by its big-endian CRC through it yields 0.
 */
uint16_t nl_crc16(uint16_t crc, const uint8_t *bytes, size_t size);
/** Validate command and length; PING, PULL and STATUS are requests without data. */
nl_status nl_frame_validate(const nl_frame *frame);
/** Make a PUSH or FRAGMENT frame from a validated fragment. */
nl_status nl_frame_from_fragment(uint8_t command, const nl_fragment *fragment, nl_frame *frame);
/** Extract a fragment from a PUSH or FRAGMENT frame. */
nl_status nl_frame_to_fragment(const nl_frame *frame, nl_fragment *fragment);
/** Encode [0xAA][LEN = 1 + data size][command][data][CRC16 hi][CRC16 lo].
 * The CRC covers LEN, command and data, so a flipped length is also caught.
 */
nl_status nl_frame_encode(const nl_frame *frame, uint8_t *bytes, size_t capacity, size_t *size);
/** Decode exactly one complete frame; a CRC mismatch returns NL_ERR_INTEGRITY. */
nl_status nl_frame_decode(const uint8_t *bytes, size_t size, nl_frame *frame);

typedef enum { NL_PARSE_WAIT, NL_PARSE_READY, NL_PARSE_REJECTED } nl_parse_result;
typedef struct {
    uint8_t state;
    uint8_t expected;
    uint8_t used;
    uint16_t crc;
    uint8_t body[NL_FRAME_BODY_MAX];
} nl_parser;

/** Clear partial input, including at an adapter's transaction boundary/timeout. */
void nl_parser_reset(nl_parser *parser);
/** Feed one byte. READY writes a complete, CRC-checked frame; other results
 * leave it unchanged. CRC bytes are folded into a running CRC, never buffered.
 */
nl_parse_result nl_parser_feed(nl_parser *parser, uint8_t byte, nl_frame *frame);

#endif
