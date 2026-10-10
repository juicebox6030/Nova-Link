#include "test.h"
#include "../src/secure_internal.h"

static const uint8_t test_key[16] = {0x2b, 0x7e, 0x15, 0x16, 0x28, 0xae, 0xd2, 0xa6,
                                     0xab, 0xf7, 0x15, 0x88, 0x09, 0xcf, 0x4f, 0x3c};

static void aes_vectors(void)
{
    /* FIPS-197 appendix C.1. */
    static const uint8_t expected[16] = {0x69, 0xc4, 0xe0, 0xd8, 0x6a, 0x7b, 0x04, 0x30,
                                         0xd8, 0xcd, 0xb7, 0x80, 0x70, 0xb4, 0xc5, 0x5a};
    uint8_t state[NL_AES_STATE_SIZE], key[16], block[16];
    unsigned i;
    for (i = 0; i < 16u; ++i) {
        key[i] = (uint8_t)i;
        block[i] = (uint8_t)(i * 0x11u);
    }
    nl_aes128_init(state, key);
    nl_aes128_encrypt(state, block, block);
    CHECK(memcmp(block, expected, 16) == 0);
}

static void ccm_vectors(void)
{
    /* RFC 3610 packet vector #1. */
    static const uint8_t nonce[13] = {0x00, 0x00, 0x00, 0x03, 0x02, 0x01, 0x00,
                                      0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5};
    static const uint8_t expected[31] = {
        0x58, 0x8C, 0x97, 0x9A, 0x61, 0xC6, 0x63, 0xD2, 0xF0, 0x66, 0xD0, 0xC2, 0xC0, 0xF9, 0x89, 0x80,
        0x6D, 0x5F, 0x6B, 0x61, 0xDA, 0xC3, 0x84, 0x17, 0xE8, 0xD1, 0x2C, 0xFD, 0xF9, 0x26, 0xE0};
    uint8_t state[NL_AES_STATE_SIZE], key[16], aad[8], data[23], mic[8], check[8];
    unsigned i;
    for (i = 0; i < 16u; ++i) key[i] = (uint8_t)(0xC0u + i);
    for (i = 0; i < 8u; ++i) aad[i] = (uint8_t)i;
    for (i = 0; i < 23u; ++i) data[i] = (uint8_t)(8u + i);
    nl_aes128_init(state, key);
    nl_aes128_ccm8(state, nonce, aad, sizeof(aad), data, sizeof(data), true, mic);
    CHECK(memcmp(data, expected, 23) == 0 && memcmp(mic, expected + 23, 8) == 0);
    nl_aes128_ccm8(state, nonce, aad, sizeof(aad), data, sizeof(data), false, check);
    CHECK(memcmp(check, mic, 8) == 0);
    for (i = 0; i < 23u; ++i) CHECK(data[i] == 8u + i);
}

static nl_fragment sample(uint8_t origin, uint8_t sequence, uint8_t size)
{
    nl_fragment value = fragment(origin, 1, sequence);
    uint8_t i;
    value.payload_size = size;
    for (i = 0; i < size; ++i) value.payload[i] = (uint8_t)(i * 7u + sequence);
    return value;
}

static void round_trip(nl_secure_mode mode)
{
    nl_secure tx, rx;
    nl_fragment value, output;
    uint8_t air[NL_SECURE_AIR_MAX], sizes[] = {0, 1, 15, 16, 17, 99, NL_PAYLOAD_MAX};
    size_t size, i;
    uint32_t counter;
    STATUS(nl_secure_init(&tx, test_key, mode, 7, NULL, NULL), NL_OK);
    STATUS(nl_secure_init(&rx, test_key, mode, 0, NULL, NULL), NL_OK);
    for (i = 0; i < sizeof(sizes); ++i) {
        value = sample(3, (uint8_t)i, sizes[i]);
        value.flags = NL_FLAG_BURST;
        STATUS(nl_secure_seal(&tx, &value, air, sizes[i] + NL_SECURE_AIR_MIN - 1u, &size), NL_ERR_SIZE);
        STATUS(nl_secure_seal(&tx, &value, air, sizeof(air), &size), NL_OK);
        CHECK(size == sizes[i] + NL_SECURE_AIR_MIN);
        CHECK(air[0] == (uint8_t)(3u << 5 | 1u << 2 | NL_FLAG_BURST) && air[1] == (uint8_t)i);
        if (sizes[i] >= 16u) {
            bool readable = memcmp(air + 6, value.payload, sizes[i]) == 0;
            CHECK(readable == (mode == NL_SECURE_AUTH));
        }
        STATUS(nl_secure_open(&rx, air, size, &output, &counter), NL_OK);
        CHECK(counter == 7u + i);
        same_fragment(&output, &value);
        nl_secure_accept(&rx, output.origin, counter);
    }
    CHECK(tx.stats.sealed == sizeof(sizes) && rx.stats.opened == sizeof(sizes));
    nl_secure_wipe(&tx);
    for (i = 0; i < sizeof(tx); ++i) CHECK(((const uint8_t *)&tx)[i] == 0u);
}

static void forgery(void)
{
    nl_secure tx, rx, other;
    nl_fragment value = sample(2, 9, 40), output;
    uint8_t air[NL_SECURE_AIR_MAX], tampered[NL_SECURE_AIR_MAX], other_key[16];
    size_t size, i;
    unsigned bit;
    uint32_t counter;
    STATUS(nl_secure_init(&tx, test_key, NL_SECURE_ENCRYPT, 1, NULL, NULL), NL_OK);
    STATUS(nl_secure_init(&rx, test_key, NL_SECURE_ENCRYPT, 0, NULL, NULL), NL_OK);
    STATUS(nl_secure_seal(&tx, &value, air, sizeof(air), &size), NL_OK);
    /* Every single-bit change anywhere, including header and counter, fails. */
    for (i = 0; i < size; ++i) {
        for (bit = 0; bit < 8u; ++bit) {
            memcpy(tampered, air, size);
            tampered[i] ^= (uint8_t)(1u << bit);
            output.payload_size = 0xEE;
            STATUS(nl_secure_open(&rx, tampered, size, &output, &counter), NL_ERR_INTEGRITY);
            CHECK(output.payload_size == 0u);
        }
    }
    STATUS(nl_secure_open(&rx, air, size - 1u, &output, &counter), NL_ERR_INTEGRITY);
    STATUS(nl_secure_open(&rx, air, NL_SECURE_AIR_MIN - 1u, &output, &counter), NL_ERR_INTEGRITY);
    STATUS(nl_secure_open(&rx, air, NL_SECURE_AIR_MAX + 1u, &output, &counter), NL_ERR_INTEGRITY);
    CHECK(rx.stats.auth_failed == size * 8u + 3u && rx.stats.opened == 0u);
    /* Wrong key and wrong mode both fail. */
    memcpy(other_key, test_key, 16);
    other_key[15] ^= 1u;
    STATUS(nl_secure_init(&other, other_key, NL_SECURE_ENCRYPT, 0, NULL, NULL), NL_OK);
    STATUS(nl_secure_open(&other, air, size, &output, &counter), NL_ERR_INTEGRITY);
    STATUS(nl_secure_init(&other, test_key, NL_SECURE_AUTH, 0, NULL, NULL), NL_OK);
    STATUS(nl_secure_open(&other, air, size, &output, &counter), NL_ERR_INTEGRITY);
    STATUS(nl_secure_open(&rx, air, size, &output, &counter), NL_OK);
    same_fragment(&output, &value);
}

static void replay(void)
{
    nl_secure tx, rx;
    nl_fragment value = sample(5, 0, 4), output;
    uint8_t air[40][NL_SECURE_AIR_MAX];
    size_t size[40], i;
    uint32_t counter;
    STATUS(nl_secure_init(&tx, test_key, NL_SECURE_AUTH, 100, NULL, NULL), NL_OK);
    STATUS(nl_secure_init(&rx, test_key, NL_SECURE_AUTH, 0, NULL, NULL), NL_OK);
    for (i = 0; i < 40u; ++i) {
        value.sequence = (uint8_t)i;
        STATUS(nl_secure_seal(&tx, &value, air[i], sizeof(air[i]), &size[i]), NL_OK);
    }
    /* open() alone never records a counter. */
    STATUS(nl_secure_open(&rx, air[5], size[5], &output, &counter), NL_OK);
    STATUS(nl_secure_open(&rx, air[5], size[5], &output, &counter), NL_OK);
    nl_secure_accept(&rx, 5, counter);
    STATUS(nl_secure_open(&rx, air[5], size[5], &output, &counter), NL_ERR_DUPLICATE);
    /* Reordering inside the window is fine; each counter only once. */
    STATUS(nl_secure_open(&rx, air[3], size[3], &output, &counter), NL_OK);
    nl_secure_accept(&rx, 5, counter);
    STATUS(nl_secure_open(&rx, air[3], size[3], &output, &counter), NL_ERR_DUPLICATE);
    STATUS(nl_secure_open(&rx, air[4], size[4], &output, &counter), NL_OK);
    STATUS(nl_secure_open(&rx, air[39], size[39], &output, &counter), NL_OK);
    nl_secure_accept(&rx, 5, counter);
    STATUS(nl_secure_open(&rx, air[8], size[8], &output, &counter), NL_OK);
    nl_secure_accept(&rx, 5, counter);
    STATUS(nl_secure_open(&rx, air[8], size[8], &output, &counter), NL_ERR_DUPLICATE);
    STATUS(nl_secure_open(&rx, air[7], size[7], &output, &counter), NL_ERR_STALE);
    STATUS(nl_secure_open(&rx, air[39], size[39], &output, &counter), NL_ERR_DUPLICATE);
    CHECK(rx.stats.replayed == 4u && rx.stats.too_old == 1u);
    /* A rebooted receiver restores a floor instead of trusting the first frame. */
    STATUS(nl_secure_init(&rx, test_key, NL_SECURE_AUTH, 0, NULL, NULL), NL_OK);
    STATUS(nl_secure_set_rx_floor(&rx, 5, 135), NL_OK);
    STATUS(nl_secure_set_rx_floor(&rx, NL_ORIGIN_COUNT, 0), NL_ERR_ARGUMENT);
    STATUS(nl_secure_open(&rx, air[30], size[30], &output, &counter), NL_ERR_DUPLICATE);
    STATUS(nl_secure_open(&rx, air[0], size[0], &output, &counter), NL_ERR_STALE);
    STATUS(nl_secure_open(&rx, air[36], size[36], &output, &counter), NL_OK);
}

typedef struct {
    uint32_t stored;
    unsigned calls;
    nl_status result;
} store;

static nl_status persist(void *context, uint32_t reserved_until)
{
    store *nv = context;
    ++nv->calls;
    if (nv->result == NL_OK) nv->stored = reserved_until;
    return nv->result;
}

static void counters(void)
{
    nl_secure tx;
    store nv = {0, 0, NL_OK};
    nl_fragment value = sample(1, 0, 1);
    uint8_t air[NL_SECURE_AIR_MAX];
    size_t size;
    unsigned i;
    STATUS(nl_secure_init(NULL, test_key, NL_SECURE_AUTH, 0, NULL, NULL), NL_ERR_ARGUMENT);
    STATUS(nl_secure_init(&tx, test_key, (nl_secure_mode)3, 0, NULL, NULL), NL_ERR_ARGUMENT);
    /* A failed write blocks sealing rather than risking nonce reuse. */
    nv.result = NL_ERR_BUSY;
    STATUS(nl_secure_init(&tx, test_key, NL_SECURE_AUTH, 50, persist, &nv), NL_OK);
    STATUS(nl_secure_seal(&tx, &value, air, sizeof(air), &size), NL_ERR_BUSY);
    CHECK(tx.tx_counter == 50u && tx.stats.sealed == 0u);
    nv.result = NL_OK;
    for (i = 0; i < NL_SECURE_RESERVE + 1u; ++i)
        STATUS(nl_secure_seal(&tx, &value, air, sizeof(air), &size), NL_OK);
    CHECK(nv.calls == 3u && nv.stored == 50u + 2u * NL_SECURE_RESERVE);
    /* Reboot from the stored value: never below anything already sent. */
    STATUS(nl_secure_init(&tx, test_key, NL_SECURE_AUTH, nv.stored, persist, &nv), NL_OK);
    STATUS(nl_secure_seal(&tx, &value, air, sizeof(air), &size), NL_OK);
    CHECK(air[2] == 0 && air[5] == (uint8_t)(50u + 2u * NL_SECURE_RESERVE));
    /* Exhaustion: the last usable counter is UINT32_MAX - 1. */
    STATUS(nl_secure_init(&tx, test_key, NL_SECURE_AUTH, UINT32_MAX - 1u, persist, &nv), NL_OK);
    STATUS(nl_secure_seal(&tx, &value, air, sizeof(air), &size), NL_OK);
    CHECK(nv.stored == UINT32_MAX);
    STATUS(nl_secure_seal(&tx, &value, air, sizeof(air), &size), NL_ERR_FULL);
    STATUS(nl_secure_init(&tx, test_key, NL_SECURE_AUTH, UINT32_MAX, NULL, NULL), NL_OK);
    STATUS(nl_secure_seal(&tx, &value, air, sizeof(air), &size), NL_ERR_FULL);
    value.payload_size = NL_PAYLOAD_MAX + 1u;
    STATUS(nl_secure_init(&tx, test_key, NL_SECURE_AUTH, 0, NULL, NULL), NL_OK);
    STATUS(nl_secure_seal(&tx, &value, air, sizeof(air), &size), NL_ERR_SIZE);
}

static void radio_integration(void)
{
    nl_secure tx, rx;
    nl_radio radio;
    nl_fragment value = sample(2, 0, 3), output;
    uint8_t air[NL_RADIO_RX_DEPTH + 1u][NL_SECURE_AIR_MAX];
    size_t size[NL_RADIO_RX_DEPTH + 1u], i;
    STATUS(nl_secure_init(&tx, test_key, NL_SECURE_ENCRYPT, 0, NULL, NULL), NL_OK);
    STATUS(nl_secure_init(&rx, test_key, NL_SECURE_ENCRYPT, 0, NULL, NULL), NL_OK);
    STATUS(nl_radio_init(&radio, 0x02, 1000, 1000, 0), NL_OK);
    for (i = 0; i <= NL_RADIO_RX_DEPTH; ++i) {
        value.sequence = (uint8_t)i;
        STATUS(nl_secure_seal(&tx, &value, air[i], sizeof(air[i]), &size[i]), NL_OK);
    }
    for (i = 0; i < NL_RADIO_RX_DEPTH; ++i)
        STATUS(nl_radio_receive_sealed(&radio, &rx, air[i], size[i], i), NL_OK);
    /* A full queue leaves the counter unused so the RF retry still lands. */
    STATUS(nl_radio_receive_sealed(&radio, &rx, air[i], size[i], i), NL_ERR_FULL);
    STATUS(nl_radio_pull(&radio, &output), NL_OK);
    CHECK(output.sequence == 0u && output.payload[0] == value.payload[0]);
    STATUS(nl_radio_receive_sealed(&radio, &rx, air[i], size[i], i), NL_OK);
    /* Replays and forgeries never reach the radio. */
    STATUS(nl_radio_pull(&radio, &output), NL_OK);
    STATUS(nl_radio_receive_sealed(&radio, &rx, air[1], size[1], 50), NL_ERR_DUPLICATE);
    air[0][size[0] - 1u] ^= 1u;
    STATUS(nl_radio_receive_sealed(&radio, &rx, air[0], size[0], 50), NL_ERR_INTEGRITY);
    STATUS(nl_radio_receive_sealed(NULL, &rx, air[0], size[0], 50), NL_ERR_ARGUMENT);
    STATUS(nl_radio_receive_sealed(&radio, NULL, air[0], size[0], 50), NL_ERR_ARGUMENT);
}

/* An attacker who blocks a frame and injects it once the radio has forgotten
 * the stream must not get it delivered out of order.
 */
static void held_back(void)
{
    static const uint8_t zones[6] = {1, 2, 1, 2, 2, 2}, seqs[6] = {0, 0, 1, 1, 2, 3};
    nl_secure tx, rx;
    nl_radio radio;
    nl_fragment value, output;
    uint8_t air[6][NL_SECURE_AIR_MAX];
    size_t size[6], i;
    STATUS(nl_secure_init(&tx, test_key, NL_SECURE_AUTH, 0, NULL, NULL), NL_OK);
    STATUS(nl_secure_init(&rx, test_key, NL_SECURE_AUTH, 0, NULL, NULL), NL_OK);
    STATUS(nl_radio_init(&radio, 0x06, 1000, 1000, 1000), NL_OK);
    for (i = 0; i < 6u; ++i) {
        value = sample(3, seqs[i], 4);
        value.zone = zones[i];
        STATUS(nl_secure_seal(&tx, &value, air[i], sizeof(air[i]), &size[i]), NL_OK);
    }
    STATUS(nl_radio_receive_sealed(&radio, &rx, air[0], size[0], 0), NL_OK);
    STATUS(nl_radio_receive_sealed(&radio, &rx, air[1], size[1], 1), NL_OK);
    /* Reordering across two tracked streams is still legitimate. */
    STATUS(nl_radio_receive_sealed(&radio, &rx, air[3], size[3], 2), NL_OK);
    STATUS(nl_radio_receive_sealed(&radio, &rx, air[2], size[2], 3), NL_OK);
    /* Counter 4 held back past the idle timeout while counter 5 got through. */
    STATUS(nl_radio_receive_sealed(&radio, &rx, air[5], size[5], 10), NL_OK);
    STATUS(nl_radio_receive_sealed(&radio, &rx, air[4], size[4], 5000), NL_ERR_STALE);
    CHECK(rx.stats.too_old == 1u);
    STATUS(nl_radio_receive_sealed(&radio, &rx, air[4], size[4], 5001), NL_ERR_DUPLICATE);
    for (i = 0; i < 5u; ++i) STATUS(nl_radio_pull(&radio, &output), NL_OK);
    STATUS(nl_radio_pull(&radio, &output), NL_ERR_EMPTY);
}

int main(void)
{
    aes_vectors();
    ccm_vectors();
    round_trip(NL_SECURE_AUTH);
    round_trip(NL_SECURE_ENCRYPT);
    forgery();
    replay();
    counters();
    radio_integration();
    held_back();
    puts("secure tests passed");
    return 0;
}
