#include <string.h>
#include "nova_link/fragment.h"

nl_status nl_fragment_validate(const nl_fragment *fragment)
{
    if (fragment == NULL) return NL_ERR_ARGUMENT;
    if (fragment->origin >= NL_ORIGIN_COUNT || fragment->zone >= NL_ZONE_COUNT ||
        (fragment->flags & ~NL_FLAGS_MASK) != 0u) return NL_ERR_ARGUMENT;
    if (fragment->payload_size > NL_PAYLOAD_MAX) return NL_ERR_SIZE;
    return NL_OK;
}

nl_status nl_fragment_encode(const nl_fragment *fragment, uint8_t *bytes,
                             size_t capacity, size_t *size)
{
    nl_status status = nl_fragment_validate(fragment);
    size_t required;
    if (status != NL_OK) return status;
    if (bytes == NULL || size == NULL) return NL_ERR_ARGUMENT;
    required = NL_FRAGMENT_MIN + fragment->payload_size;
    if (capacity < required) return NL_ERR_SIZE;
    bytes[0] = (uint8_t)((fragment->origin << 5) | (fragment->zone << 2) | fragment->flags);
    bytes[1] = fragment->sequence;
    memcpy(bytes + NL_FRAGMENT_MIN, fragment->payload, fragment->payload_size);
    *size = required;
    return NL_OK;
}

nl_status nl_fragment_decode(const uint8_t *bytes, size_t size, nl_fragment *fragment)
{
    nl_fragment decoded = {0};
    if (bytes == NULL || fragment == NULL) return NL_ERR_ARGUMENT;
    if (size < NL_FRAGMENT_MIN || size > NL_FRAGMENT_MAX) return NL_ERR_SIZE;
    decoded.origin = (uint8_t)(bytes[0] >> 5);
    decoded.zone = (uint8_t)((bytes[0] >> 2) & 0x07u);
    decoded.flags = (uint8_t)(bytes[0] & NL_FLAGS_MASK);
    decoded.sequence = bytes[1];
    decoded.payload_size = (uint8_t)(size - NL_FRAGMENT_MIN);
    memcpy(decoded.payload, bytes + NL_FRAGMENT_MIN, decoded.payload_size);
    *fragment = decoded;
    return NL_OK;
}
