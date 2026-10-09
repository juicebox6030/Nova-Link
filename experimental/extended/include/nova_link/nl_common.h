/**
 * @file nl_common.h
 * @brief Shared types, status codes, and protocol constants for NOVA-LINK.
 *
 * Everything in the portable core is plain C99 with no dynamic allocation,
 * so the same sources build for the ESP32-S3 host, the CC1352R radio, and
 * the POSIX simulator / unit tests.
 */
#ifndef NL_COMMON_H
#define NL_COMMON_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "nl_config.h"

#ifdef __cplusplus
extern "C" {
#endif

/** @name Version */
/**@{*/
#define NL_VERSION_MAJOR 0
#define NL_VERSION_MINOR 1
#define NL_VERSION_PATCH 0
/** Version of the host <-> radio link protocol (bumped on wire changes). */
#define NL_LINK_PROTOCOL_VERSION 1
/**@}*/

/** @name Protocol limits (fixed by the wire format, not tunable) */
/**@{*/
#define NL_NUM_ZONES 8           /**< Zones 0..7 (3-bit zoneID). */
#define NL_NUM_ORIGINS 8         /**< Origins 0..7 (3-bit originID). */
#define NL_META_ZONE 0           /**< Zone 0 is the metadata zone. */
#define NL_FRAGMENT_HEADER_SIZE 2 /**< Header byte + seqNum byte. */
#define NL_MAX_PAYLOAD 100       /**< Maximum payload bytes per fragment. */
#define NL_MAX_FRAGMENT (NL_FRAGMENT_HEADER_SIZE + NL_MAX_PAYLOAD)
/**@}*/

/** Result codes. Zero is success, negatives are errors. */
typedef enum {
    NL_OK = 0,
    NL_ERR_ARG = -1,       /**< Invalid argument. */
    NL_ERR_SIZE = -2,      /**< Buffer or payload size out of range. */
    NL_ERR_FULL = -3,      /**< Queue or table is full. */
    NL_ERR_EMPTY = -4,     /**< Nothing available. */
    NL_ERR_PERM = -5,      /**< Operation not permitted (zone claim rules). */
    NL_ERR_CONFLICT = -6,  /**< Conflicting claim already held. */
    NL_ERR_NOT_FOUND = -7, /**< No such item. */
    NL_ERR_CRC = -8,       /**< Link frame checksum mismatch. */
    NL_ERR_PROTO = -9,     /**< Malformed frame or unexpected response. */
    NL_ERR_IO = -10,       /**< Transport/HAL failure. */
} nl_status_t;

/** Return a short constant string describing a status code. */
const char *nl_status_str(int status);

/**
 * Monotonic timestamp in microseconds. Wraps every ~71 minutes, so always
 * compare with nl_time_before() / nl_time_diff() rather than < or >.
 */
typedef uint32_t nl_time_us_t;

/** Signed difference a - b, correct across wraparound. */
static inline int32_t nl_time_diff(nl_time_us_t a, nl_time_us_t b)
{
    return (int32_t)(a - b);
}

/**
 * A duration as a nl_time_diff() bound. Durations above 2^31 - 1 us
 * (about 35 minutes) cannot be compared against a wrapping difference, so
 * they are clamped instead of turning negative in a plain cast.
 */
static inline int32_t nl_time_span(uint32_t us)
{
    return us > (uint32_t)INT32_MAX ? INT32_MAX : (int32_t)us;
}

/** True if a is strictly earlier than b. */
static inline bool nl_time_before(nl_time_us_t a, nl_time_us_t b)
{
    return nl_time_diff(a, b) < 0;
}

/**
 * xorshift32 PRNG for timing jitter (not for anything security related).
 * @p state must be non-zero; nl_rand_seed() guarantees that.
 */
static inline uint32_t nl_rand_next(uint32_t *state)
{
    uint32_t x = *state;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    *state = x;
    return x;
}

/** Scramble @p seed into a valid (non-zero) nl_rand_next() state. */
static inline uint32_t nl_rand_seed(uint32_t seed)
{
    seed = (seed ^ 0x9E3779B9u) * 0x85EBCA6Bu;
    seed ^= seed >> 16;
    return seed != 0 ? seed : 0x6D2B79F5u;
}

/** Uniform-ish value in 0..max inclusive (0 when max is 0). */
static inline uint32_t nl_rand_upto(uint32_t *state, uint32_t max)
{
    if (max == 0) {
        return 0;
    }
    uint32_t r = nl_rand_next(state);
    return max == UINT32_MAX ? r : r % (max + 1u);
}

/** Little-endian helpers used by the wire formats. */
static inline void nl_put_u16le(uint8_t *p, uint16_t v)
{
    p[0] = (uint8_t)v;
    p[1] = (uint8_t)(v >> 8);
}

static inline uint16_t nl_get_u16le(const uint8_t *p)
{
    return (uint16_t)(p[0] | (p[1] << 8));
}

static inline void nl_put_u32le(uint8_t *p, uint32_t v)
{
    p[0] = (uint8_t)v;
    p[1] = (uint8_t)(v >> 8);
    p[2] = (uint8_t)(v >> 16);
    p[3] = (uint8_t)(v >> 24);
}

static inline uint32_t nl_get_u32le(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) |
           ((uint32_t)p[3] << 24);
}

#define NL_ARRAY_SIZE(a) (sizeof(a) / sizeof((a)[0]))

#ifdef __cplusplus
}
#endif

#endif /* NL_COMMON_H */
