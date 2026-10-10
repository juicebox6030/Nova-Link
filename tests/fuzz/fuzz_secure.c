/* AES-CCM air security. Fuzzed bytes must never open under a fixed key; a
 * fragment sealed from the input must open to itself; any single bit flip
 * must be rejected; a replay through the radio path must never be delivered.
 */
#include "fuzz.h"
#include "nova_link/secure.h"

static const uint8_t key[16] = {0x2b, 0x7e, 0x15, 0x16, 0x28, 0xae, 0xd2, 0xa6,
                                0xab, 0xf7, 0x15, 0x88, 0x09, 0xcf, 0x4f, 0x3c};

static void forged(nl_secure *rx, const uint8_t *data, size_t size)
{
    nl_fragment fragment;
    uint32_t counter;
    nl_status status;
    memset(&fragment, 0, sizeof(fragment));
    status = nl_secure_open(rx, data, size, &fragment, &counter);
    REQUIRE(status == NL_ERR_INTEGRITY);
    REQUIRE(fragment.payload_size == 0);
}

int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size)
{
    static nl_radio radio;
    nl_secure tx, rx;
    nl_fragment input, output;
    uint8_t sealed[NL_SECURE_AIR_MAX], plain[NL_FRAGMENT_MAX];
    size_t sealed_size, plain_size, bit;
    uint32_t counter;
    nl_status status;
    fuzz_input in = {data, size};
    nl_secure_mode mode = (take(&in) & 1u) ? NL_SECURE_ENCRYPT : NL_SECURE_AUTH;
    uint32_t start = take32(&in);
    REQUIRE(nl_secure_init(&rx, key, mode, 0, NULL, NULL) == NL_OK);
    forged(&rx, in.data, in.size);

    plain_size = take_bytes(&in, plain, NL_FRAGMENT_MAX);
    if (nl_fragment_decode(plain, plain_size, &input) != NL_OK) return 0;
    REQUIRE(nl_secure_init(&tx, key, mode, start, NULL, NULL) == NL_OK);
    status = nl_secure_seal(&tx, &input, sealed, sizeof(sealed), &sealed_size);
    if (start == UINT32_MAX) {
        REQUIRE(status == NL_ERR_FULL);
        return 0;
    }
    REQUIRE(status == NL_OK && sealed_size == plain_size + NL_SECURE_OVERHEAD);
    REQUIRE(nl_secure_open(&rx, sealed, sealed_size, &output, &counter) == NL_OK);
    REQUIRE(counter == start && fragments_equal(&input, &output));
    if (mode == NL_SECURE_ENCRYPT && input.payload_size >= 8u)
        REQUIRE(memcmp(sealed + 6, input.payload, input.payload_size) != 0);

    bit = ((size_t)take(&in) << 8 | take(&in)) % (sealed_size * 8u);
    sealed[bit / 8u] ^= (uint8_t)(1u << (bit % 8u));
    REQUIRE(nl_secure_open(&rx, sealed, sealed_size, &output, &counter) == NL_ERR_INTEGRITY);
    sealed[bit / 8u] ^= (uint8_t)(1u << (bit % 8u));
    /* Truncation and extension are forgeries too. */
    REQUIRE(nl_secure_open(&rx, sealed, sealed_size - 1u, &output, &counter) == NL_ERR_INTEGRITY);

    /* Through the radio: first copy may be consumed, the replay never is. */
    if (nl_radio_init(&radio, 0xFF, 1000, 1000, 1000000) != NL_OK) return 0;
    status = nl_radio_receive_sealed(&radio, &rx, sealed, sealed_size, 10);
    REQUIRE(status != NL_ERR_INTEGRITY);
    if (status != NL_ERR_FULL) {
        status = nl_radio_receive_sealed(&radio, &rx, sealed, sealed_size, 20);
        REQUIRE(status == NL_ERR_DUPLICATE || status == NL_ERR_STALE);
    }
    nl_secure_wipe(&tx);
    nl_secure_wipe(&rx);
    return 0;
}
