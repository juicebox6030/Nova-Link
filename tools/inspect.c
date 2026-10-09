#include <ctype.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "nova_link/nova_link.h"

static void print_fragment(const nl_fragment *fragment)
{
    size_t i;
    printf("{\"origin\":%u,\"zone\":%u,\"sequence\":%u,\"flags\":%u,"
        "\"burst\":%s,\"management_listen\":%s,\"payload_size\":%u,\"payload_hex\":\"",
        (unsigned)fragment->origin, (unsigned)fragment->zone, (unsigned)fragment->sequence,
        (unsigned)fragment->flags, (fragment->flags & NL_FLAG_BURST) != 0u ? "true" : "false",
        (fragment->flags & NL_FLAG_MGMT_LISTEN) != 0u ? "true" : "false",
        (unsigned)fragment->payload_size);
    for (i = 0; i < fragment->payload_size; ++i) printf("%02x", (unsigned)fragment->payload[i]);
    printf("\"}");
}

static void print_frame(const nl_frame *frame)
{
    nl_fragment fragment;
    printf("{\"command\":%u", (unsigned)frame->command);
    if (nl_frame_to_fragment(frame, &fragment) == NL_OK) {
        printf(",\"fragment\":");
        print_fragment(&fragment);
    }
    printf("}\n");
}

static int nibble(unsigned char ch)
{
    if (ch >= '0' && ch <= '9') return ch - '0';
    if (ch >= 'a' && ch <= 'f') return ch - 'a' + 10;
    if (ch >= 'A' && ch <= 'F') return ch - 'A' + 10;
    return -1;
}

static nl_status parse_hex(const char *input, uint8_t *bytes, size_t capacity, size_t *size)
{
    int high = -1;
    size_t used = 0;
    const unsigned char *cursor = (const unsigned char *)input;
    for (; *cursor != 0; ++cursor) {
        int digit;
        if (isspace(*cursor)) continue;
        digit = nibble(*cursor);
        if (digit < 0) return NL_ERR_FORMAT;
        if (high < 0) high = digit;
        else {
            if (used == capacity) return NL_ERR_SIZE;
            bytes[used++] = (uint8_t)(high * 16 + digit);
            high = -1;
        }
    }
    if (high >= 0) return NL_ERR_FORMAT;
    *size = used;
    return NL_OK;
}

static int inspect_stream(const char *path)
{
    FILE *input = strcmp(path, "-") == 0 ? stdin : fopen(path, "rb");
    nl_parser parser;
    nl_frame frame;
    uint64_t offset = 0, frames = 0;
    int byte, failed = 0;
    if (input == NULL) { perror(path); return EXIT_FAILURE; }
    nl_parser_reset(&parser);
    while ((byte = fgetc(input)) != EOF) {
        nl_parse_result result = nl_parser_feed(&parser, (uint8_t)byte, &frame);
        if (result == NL_PARSE_READY) { print_frame(&frame); ++frames; }
        if (result == NL_PARSE_REJECTED) {
            fprintf(stderr, "Malformed frame ending at byte %" PRIu64 "\n", offset);
            failed = 1;
        }
        ++offset;
    }
    if (ferror(input)) { perror("Read stream"); failed = 1; }
    if (parser.state != 0u) { fprintf(stderr, "Truncated frame at end of stream\n"); failed = 1; }
    if (frames == 0u) { fprintf(stderr, "No complete frames\n"); failed = 1; }
    if (input != stdin && fclose(input) != 0) { perror("Close stream"); failed = 1; }
    return failed ? EXIT_FAILURE : EXIT_SUCCESS;
}

int main(int argc, char **argv)
{
    uint8_t bytes[NL_FRAME_MAX];
    size_t size;
    nl_fragment fragment;
    nl_frame frame;
    nl_status status;
    if (argc != 3 || (strcmp(argv[1], "fragment") != 0 && strcmp(argv[1], "frame") != 0 &&
        strcmp(argv[1], "stream") != 0)) {
        fprintf(stderr, "Usage: nova-inspect fragment HEX | frame HEX | stream FILE\n"
            "Use '-' for a binary stream from stdin. Output is JSON/JSON Lines.\n");
        return EXIT_FAILURE;
    }
    if (strcmp(argv[1], "stream") == 0) return inspect_stream(argv[2]);
    status = parse_hex(argv[2], bytes, sizeof(bytes), &size);
    if (status == NL_OK && strcmp(argv[1], "fragment") == 0) {
        status = nl_fragment_decode(bytes, size, &fragment);
        if (status == NL_OK) { print_fragment(&fragment); printf("\n"); }
    } else if (status == NL_OK) {
        status = nl_frame_decode(bytes, size, &frame);
        if (status == NL_OK) print_frame(&frame);
    }
    if (status != NL_OK) fprintf(stderr, "Decode failed: %s\n", nl_status_name(status));
    return status == NL_OK ? EXIT_SUCCESS : EXIT_FAILURE;
}
