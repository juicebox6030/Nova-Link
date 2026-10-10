#include <string.h>
#include "nova_link/secure.h"
#include "internal.h"
#include "secure_internal.h"

NL_STATIC_ASSERT(NL_SECURE_RESERVE >= 1u, secure_reserve_nonzero);

#define CCM_FLAGS_MAC 0x59u /* Adata | M=8 -> (8-2)/2 << 3 | L=2 -> L-1 */
#define CCM_FLAGS_CTR 0x01u /* L-1 */
#define HEADER_SIZE (NL_FRAGMENT_MIN + NL_SECURE_COUNTER_SIZE)

#ifndef NL_SECURE_EXTERNAL_AES
/* Byte-oriented AES-128 (FIPS-197), encryption only: CCM never decrypts with
 * the block cipher. One 256-byte table; xtime is branch-free. The S-box lookup
 * is data-dependent, which is constant-time on cacheless MCUs only; use a
 * hardware engine (NL_SECURE_EXTERNAL_AES) on cores with a data cache.
 */
static const uint8_t sbox[256] = {
    0x63, 0x7c, 0x77, 0x7b, 0xf2, 0x6b, 0x6f, 0xc5, 0x30, 0x01, 0x67, 0x2b, 0xfe, 0xd7, 0xab, 0x76,
    0xca, 0x82, 0xc9, 0x7d, 0xfa, 0x59, 0x47, 0xf0, 0xad, 0xd4, 0xa2, 0xaf, 0x9c, 0xa4, 0x72, 0xc0,
    0xb7, 0xfd, 0x93, 0x26, 0x36, 0x3f, 0xf7, 0xcc, 0x34, 0xa5, 0xe5, 0xf1, 0x71, 0xd8, 0x31, 0x15,
    0x04, 0xc7, 0x23, 0xc3, 0x18, 0x96, 0x05, 0x9a, 0x07, 0x12, 0x80, 0xe2, 0xeb, 0x27, 0xb2, 0x75,
    0x09, 0x83, 0x2c, 0x1a, 0x1b, 0x6e, 0x5a, 0xa0, 0x52, 0x3b, 0xd6, 0xb3, 0x29, 0xe3, 0x2f, 0x84,
    0x53, 0xd1, 0x00, 0xed, 0x20, 0xfc, 0xb1, 0x5b, 0x6a, 0xcb, 0xbe, 0x39, 0x4a, 0x4c, 0x58, 0xcf,
    0xd0, 0xef, 0xaa, 0xfb, 0x43, 0x4d, 0x33, 0x85, 0x45, 0xf9, 0x02, 0x7f, 0x50, 0x3c, 0x9f, 0xa8,
    0x51, 0xa3, 0x40, 0x8f, 0x92, 0x9d, 0x38, 0xf5, 0xbc, 0xb6, 0xda, 0x21, 0x10, 0xff, 0xf3, 0xd2,
    0xcd, 0x0c, 0x13, 0xec, 0x5f, 0x97, 0x44, 0x17, 0xc4, 0xa7, 0x7e, 0x3d, 0x64, 0x5d, 0x19, 0x73,
    0x60, 0x81, 0x4f, 0xdc, 0x22, 0x2a, 0x90, 0x88, 0x46, 0xee, 0xb8, 0x14, 0xde, 0x5e, 0x0b, 0xdb,
    0xe0, 0x32, 0x3a, 0x0a, 0x49, 0x06, 0x24, 0x5c, 0xc2, 0xd3, 0xac, 0x62, 0x91, 0x95, 0xe4, 0x79,
    0xe7, 0xc8, 0x37, 0x6d, 0x8d, 0xd5, 0x4e, 0xa9, 0x6c, 0x56, 0xf4, 0xea, 0x65, 0x7a, 0xae, 0x08,
    0xba, 0x78, 0x25, 0x2e, 0x1c, 0xa6, 0xb4, 0xc6, 0xe8, 0xdd, 0x74, 0x1f, 0x4b, 0xbd, 0x8b, 0x8a,
    0x70, 0x3e, 0xb5, 0x66, 0x48, 0x03, 0xf6, 0x0e, 0x61, 0x35, 0x57, 0xb9, 0x86, 0xc1, 0x1d, 0x9e,
    0xe1, 0xf8, 0x98, 0x11, 0x69, 0xd9, 0x8e, 0x94, 0x9b, 0x1e, 0x87, 0xe9, 0xce, 0x55, 0x28, 0xdf,
    0x8c, 0xa1, 0x89, 0x0d, 0xbf, 0xe6, 0x42, 0x68, 0x41, 0x99, 0x2d, 0x0f, 0xb0, 0x54, 0xbb, 0x16};

static inline uint8_t xtime(uint8_t x)
{
    return (uint8_t)((uint8_t)(x << 1) ^ (uint8_t)(0x1Bu & (uint8_t)(0u - (unsigned)(x >> 7))));
}

/* One column per word, row r in bits 8r..8r+7, so MixColumns and AddRoundKey
 * work on four bytes at once. Round keys are stored as such words (memcpy into
 * the byte state), which keeps the layout correct on either endianness.
 */
static uint32_t column(const uint8_t *bytes)
{
    return (uint32_t)bytes[0] | (uint32_t)bytes[1] << 8 | (uint32_t)bytes[2] << 16 | (uint32_t)bytes[3] << 24;
}

static uint32_t xtime4(uint32_t x)
{
    return ((x & 0x7F7F7F7Fu) << 1) ^ (((x >> 7) & 0x01010101u) * 0x1Bu);
}

static uint32_t rotate8(uint32_t x) { return (x >> 8) | (x << 24); }

void nl_aes128_init(uint8_t *state, const uint8_t key[16])
{
    uint8_t rcon = 1, t[4];
    unsigned i, j;
    uint32_t word;
    memcpy(state, key, 16);
    for (i = 16; i < 176u; i += 4u) {
        memcpy(t, state + i - 4u, 4);
        if (i % 16u == 0u) {
            uint8_t first = t[0];
            t[0] = (uint8_t)(sbox[t[1]] ^ rcon);
            t[1] = sbox[t[2]];
            t[2] = sbox[t[3]];
            t[3] = sbox[first];
            rcon = xtime(rcon);
        }
        for (j = 0; j < 4u; ++j) state[i + j] = (uint8_t)(state[i + j - 16u] ^ t[j]);
    }
    /* Byte schedule done; repack each column in place as a word. */
    for (i = 0; i < 176u; i += 4u) {
        word = column(state + i);
        memcpy(state + i, &word, 4);
    }
}

void nl_aes128_encrypt(const uint8_t *state, const uint8_t in[16], uint8_t out[16])
{
    uint32_t s[4], t[4], key[4], y;
    unsigned round, c;
    memcpy(key, state, 16);
    for (c = 0; c < 4u; ++c) s[c] = column(in + c * 4u) ^ key[c];
    for (round = 1; round <= 10u; ++round) {
        memcpy(key, state + round * 16u, 16);
        /* SubBytes + ShiftRows: row r of column c comes from column c + r. */
        for (c = 0; c < 4u; ++c)
            t[c] = (uint32_t)sbox[s[c] & 0xFFu] | (uint32_t)sbox[(s[(c + 1u) & 3u] >> 8) & 0xFFu] << 8 |
                   (uint32_t)sbox[(s[(c + 2u) & 3u] >> 16) & 0xFFu] << 16 |
                   (uint32_t)sbox[s[(c + 3u) & 3u] >> 24] << 24;
        for (c = 0; c < 4u; ++c) {
            if (round != 10u) {
                /* Row r: a_r ^ (a_0 ^ a_1 ^ a_2 ^ a_3) ^ xtime(a_r ^ a_r+1). */
                y = t[c] ^ rotate8(t[c]);
                t[c] ^= y ^ (y >> 16 | y << 16) ^ xtime4(y);
            }
            s[c] = t[c] ^ key[c];
        }
    }
    for (c = 0; c < 4u; ++c)
        for (round = 0; round < 4u; ++round) out[c * 4u + round] = (uint8_t)(s[c] >> (round * 8u));
}
#endif

/* Streaming CBC-MAC: absorb bytes into X, encrypting each full block. */
typedef struct { uint8_t x[16]; unsigned used; } cbc_mac;

static void mac_absorb(cbc_mac *mac, const uint8_t *state, const uint8_t *bytes, size_t size)
{
    size_t i;
    for (i = 0; i < size; ++i) {
        mac->x[mac->used++] ^= bytes[i];
        if (mac->used == 16u) {
            nl_aes128_encrypt(state, mac->x, mac->x);
            mac->used = 0;
        }
    }
}

static void mac_pad(cbc_mac *mac, const uint8_t *state)
{
    if (mac->used != 0u) {
        nl_aes128_encrypt(state, mac->x, mac->x);
        mac->used = 0;
    }
}

/* A_i / B_0 share the layout [flags][nonce:13][16-bit value]. */
static void ccm_block(uint8_t block[16], uint8_t flags, const uint8_t nonce[13], size_t value)
{
    block[0] = flags;
    memcpy(block + 1, nonce, 13);
    block[14] = (uint8_t)(value >> 8);
    block[15] = (uint8_t)value;
}

static void ctr_crypt(const uint8_t *state, const uint8_t nonce[13], uint8_t *data, size_t size)
{
    uint8_t block[16], stream[16];
    size_t i, counter = 1;
    for (i = 0; i < size; ++i) {
        if (i % 16u == 0u) {
            ccm_block(block, CCM_FLAGS_CTR, nonce, counter++);
            nl_aes128_encrypt(state, block, stream);
        }
        data[i] ^= stream[i % 16u];
    }
}

void nl_aes128_ccm8(const uint8_t *state, const uint8_t nonce[13], const uint8_t *aad, size_t aad_size,
                    uint8_t *data, size_t data_size, bool encrypt, uint8_t mic[8])
{
    cbc_mac mac;
    uint8_t length[2], s0[16];
    unsigned i;
    if (!encrypt) ctr_crypt(state, nonce, data, data_size);
    ccm_block(mac.x, (uint8_t)(aad_size != 0u ? CCM_FLAGS_MAC : CCM_FLAGS_MAC & 0x3Fu), nonce, data_size);
    nl_aes128_encrypt(state, mac.x, mac.x);
    mac.used = 0;
    if (aad_size != 0u) {
        length[0] = (uint8_t)(aad_size >> 8);
        length[1] = (uint8_t)aad_size;
        mac_absorb(&mac, state, length, 2);
        mac_absorb(&mac, state, aad, aad_size);
        mac_pad(&mac, state);
    }
    mac_absorb(&mac, state, data, data_size);
    mac_pad(&mac, state);
    ccm_block(s0, CCM_FLAGS_CTR, nonce, 0);
    nl_aes128_encrypt(state, s0, s0);
    for (i = 0; i < 8u; ++i) mic[i] = (uint8_t)(mac.x[i] ^ s0[i]);
    if (encrypt) ctr_crypt(state, nonce, data, data_size);
}

static void make_nonce(uint8_t nonce[13], uint8_t origin, const uint8_t counter[4], nl_secure_mode mode)
{
    memset(nonce, 0, 13);
    nonce[0] = origin;
    memcpy(nonce + 1, counter, 4);
    nonce[5] = (uint8_t)mode;
}

static void wipe(void *memory, size_t size)
{
    volatile uint8_t *bytes = memory;
    while (size-- != 0u) *bytes++ = 0;
}

nl_status nl_secure_init(nl_secure *secure, const uint8_t key[16], nl_secure_mode mode,
                         uint32_t tx_counter, nl_secure_persist_fn persist, void *context)
{
    if (secure == NULL || key == NULL || (mode != NL_SECURE_AUTH && mode != NL_SECURE_ENCRYPT))
        return NL_ERR_ARGUMENT;
    memset(secure, 0, sizeof(*secure));
    nl_aes128_init(secure->key, key);
    secure->mode = mode;
    secure->tx_counter = tx_counter;
    /* With persistence the first seal reserves; without, the key is per-boot. */
    secure->tx_limit = persist != NULL ? tx_counter : UINT32_MAX;
    secure->persist = persist;
    secure->persist_context = context;
    return NL_OK;
}

void nl_secure_wipe(nl_secure *secure)
{
    if (secure != NULL) wipe(secure, sizeof(*secure));
}

nl_status nl_secure_set_rx_floor(nl_secure *secure, uint8_t origin, uint32_t counter)
{
    if (secure == NULL || origin >= NL_ORIGIN_COUNT) return NL_ERR_ARGUMENT;
    secure->rx_known |= (uint8_t)(1u << origin);
    secure->rx_top[origin] = counter;
    secure->rx_window[origin] = UINT32_MAX;
    return NL_OK;
}

nl_status nl_secure_seal(nl_secure *secure, const nl_fragment *fragment,
                         uint8_t *bytes, size_t capacity, size_t *size)
{
    uint8_t nonce[13];
    size_t encoded, payload;
    nl_status status;
    uint32_t counter;
    if (secure == NULL || bytes == NULL || size == NULL) return NL_ERR_ARGUMENT;
    status = nl_fragment_validate(fragment);
    if (status != NL_OK) return status;
    if (capacity < (size_t)fragment->payload_size + NL_SECURE_AIR_MIN) return NL_ERR_SIZE;
    counter = secure->tx_counter;
    if (counter == UINT32_MAX) return NL_ERR_FULL;
    if (counter >= secure->tx_limit) {
        uint32_t limit = counter > UINT32_MAX - NL_SECURE_RESERVE ? UINT32_MAX : counter + NL_SECURE_RESERVE;
        status = secure->persist(secure->persist_context, limit);
        if (status != NL_OK) return status;
        secure->tx_limit = limit;
    }
    (void)nl_fragment_encode(fragment, bytes, capacity, &encoded);
    payload = encoded - NL_FRAGMENT_MIN;
    memmove(bytes + HEADER_SIZE, bytes + NL_FRAGMENT_MIN, payload);
    bytes[2] = (uint8_t)(counter >> 24);
    bytes[3] = (uint8_t)(counter >> 16);
    bytes[4] = (uint8_t)(counter >> 8);
    bytes[5] = (uint8_t)counter;
    make_nonce(nonce, fragment->origin, bytes + 2, secure->mode);
    if (secure->mode == NL_SECURE_ENCRYPT)
        nl_aes128_ccm8(secure->key, nonce, bytes, HEADER_SIZE, bytes + HEADER_SIZE, payload, true,
                       bytes + HEADER_SIZE + payload);
    else
        nl_aes128_ccm8(secure->key, nonce, bytes, HEADER_SIZE + payload, NULL, 0, true,
                       bytes + HEADER_SIZE + payload);
    secure->tx_counter = counter + 1u;
    ++secure->stats.sealed;
    *size = HEADER_SIZE + payload + NL_SECURE_MIC_SIZE;
    return NL_OK;
}

static nl_status replay_check(const nl_secure *secure, uint8_t origin, uint32_t counter)
{
    uint32_t age;
    if ((secure->rx_known & (1u << origin)) == 0u || counter > secure->rx_top[origin]) return NL_OK;
    age = secure->rx_top[origin] - counter;
    if (age >= 32u) return NL_ERR_STALE;
    return (secure->rx_window[origin] & (1u << age)) != 0u ? NL_ERR_DUPLICATE : NL_OK;
}

nl_status nl_secure_open(nl_secure *secure, const uint8_t *bytes, size_t size,
                         nl_fragment *fragment, uint32_t *counter)
{
    uint8_t nonce[13], mic[NL_SECURE_MIC_SIZE], diff = 0;
    size_t payload, i;
    nl_status status;
    uint32_t value;
    if (secure == NULL || bytes == NULL || fragment == NULL || counter == NULL) return NL_ERR_ARGUMENT;
    if (size < NL_SECURE_AIR_MIN || size > NL_SECURE_AIR_MAX) {
        ++secure->stats.auth_failed;
        return NL_ERR_INTEGRITY;
    }
    payload = size - NL_SECURE_AIR_MIN;
    fragment->origin = (uint8_t)(bytes[0] >> 5);
    fragment->zone = (uint8_t)((bytes[0] >> 2) & 7u);
    fragment->flags = (uint8_t)(bytes[0] & NL_FLAGS_MASK);
    fragment->sequence = bytes[1];
    fragment->payload_size = (uint8_t)payload;
    memcpy(fragment->payload, bytes + HEADER_SIZE, payload);
    make_nonce(nonce, fragment->origin, bytes + 2, secure->mode);
    if (secure->mode == NL_SECURE_ENCRYPT)
        nl_aes128_ccm8(secure->key, nonce, bytes, HEADER_SIZE, fragment->payload, payload, false, mic);
    else
        nl_aes128_ccm8(secure->key, nonce, bytes, HEADER_SIZE + payload, NULL, 0, false, mic);
    for (i = 0; i < NL_SECURE_MIC_SIZE; ++i) diff |= (uint8_t)(mic[i] ^ bytes[HEADER_SIZE + payload + i]);
    if (diff != 0u) {
        wipe(fragment->payload, payload);
        fragment->payload_size = 0;
        ++secure->stats.auth_failed;
        return NL_ERR_INTEGRITY;
    }
    value = (uint32_t)bytes[2] << 24 | (uint32_t)bytes[3] << 16 | (uint32_t)bytes[4] << 8 | bytes[5];
    status = replay_check(secure, fragment->origin, value);
    if (status != NL_OK) {
        if (status == NL_ERR_DUPLICATE) ++secure->stats.replayed;
        else ++secure->stats.too_old;
        return status;
    }
    *counter = value;
    ++secure->stats.opened;
    return NL_OK;
}

void nl_secure_accept(nl_secure *secure, uint8_t origin, uint32_t counter)
{
    uint32_t shift;
    if (secure == NULL || origin >= NL_ORIGIN_COUNT) return;
    if ((secure->rx_known & (1u << origin)) == 0u) {
        secure->rx_known |= (uint8_t)(1u << origin);
        secure->rx_top[origin] = counter;
        secure->rx_window[origin] = 1u;
    } else if (counter > secure->rx_top[origin]) {
        shift = counter - secure->rx_top[origin];
        secure->rx_window[origin] = shift >= 32u ? 1u : (secure->rx_window[origin] << shift) | 1u;
        secure->rx_top[origin] = counter;
    } else if (secure->rx_top[origin] - counter < 32u) {
        secure->rx_window[origin] |= 1u << (secure->rx_top[origin] - counter);
    }
}

/* An authentic counter behind one already accepted from that origin, whose
 * stream the radio no longer tracks (never seen, or idle-expired). The radio
 * would treat it as a fresh stream start, so an attacker could hold back a
 * frame and inject it out of order later. Legitimate reordering is bounded by
 * the idle timeout, so only delayed or held-back frames are refused.
 */
static bool late_untracked(const nl_secure *secure, const nl_stream_tracker *streams,
                           const nl_fragment *fragment, uint32_t counter, uint64_t now_us)
{
    uint8_t origin = fragment->origin, zone = fragment->zone;
    if ((secure->rx_known & (1u << origin)) == 0u || counter >= secure->rx_top[origin]) return false;
    if ((streams->seen[origin] & (1u << zone)) == 0u) return true;
    return streams->idle_timeout_us != 0u && now_us >= streams->accepted_at_us[origin][zone] &&
           now_us - streams->accepted_at_us[origin][zone] >= streams->idle_timeout_us;
}

nl_status nl_radio_receive_sealed(nl_radio *radio, nl_secure *secure, const uint8_t *bytes,
                                  size_t size, uint64_t now_us)
{
    nl_fragment fragment;
    uint32_t counter;
    nl_status status;
    if (radio == NULL) return NL_ERR_ARGUMENT;
    status = nl_secure_open(secure, bytes, size, &fragment, &counter);
    if (status != NL_OK) return status;
    if (late_untracked(secure, &radio->streams, &fragment, counter, now_us)) {
        nl_secure_accept(secure, fragment.origin, counter); /* burn it: never valid again */
        ++secure->stats.too_old;
        status = NL_ERR_STALE;
    } else {
        status = nl_radio_receive(radio, &fragment, now_us);
    }
    /* FULL did not consume the frame, so an RF duplicate may still deliver it. */
    if (status != NL_ERR_FULL) nl_secure_accept(secure, fragment.origin, counter);
    wipe(fragment.payload, sizeof(fragment.payload));
    return status;
}
