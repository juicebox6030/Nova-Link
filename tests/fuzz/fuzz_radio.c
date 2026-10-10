/* Stateful radio: the input is a script of SPI requests, air receptions,
 * pulls and clock jumps. Sanitizers catch memory and UB faults; the checks
 * below catch anything the radio hands out that would not survive the wire.
 */
#include "fuzz.h"

enum { OP_FRAME, OP_RECEIVE, OP_COMMIT, OP_WINDOW, OP_TX, OP_PULL, OP_TIME, OP_CONFIG, OP_COUNT };

static void spi_request(nl_radio *radio, fuzz_input *in, nl_frame *last, nl_pull_token *token, int *pending)
{
    nl_frame request, response;
    nl_pull_token next;
    nl_status status;
    request.command = take(in);
    request.data_size = (uint8_t)(take(in) % (NL_FRAGMENT_MAX + 1u));
    request.data_size = (uint8_t)take_bytes(in, request.data, request.data_size);
    status = nl_radio_handle_frame(radio, &request, &response, &next);
    if (status == NL_OK && request.command == NL_COMMAND_PULL) {
        REQUIRE(nl_frame_validate(&response) == NL_OK);
        *last = response;
        *token = next;
        *pending = 1;
    }
}

static void air_receive(nl_radio *radio, fuzz_input *in, uint64_t now)
{
    uint8_t bytes[NL_FRAGMENT_MAX];
    nl_fragment fragment;
    size_t size = take_bytes(in, bytes, NL_FRAGMENT_MIN + take(in) % (NL_PAYLOAD_MAX + 1u));
    if (nl_fragment_decode(bytes, size, &fragment) == NL_OK) (void)nl_radio_receive(radio, &fragment, now);
}

int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size)
{
    static nl_radio radio; /* ~4 KiB: keep it off the fuzzer's stack */
    fuzz_input in = {data, size};
    nl_frame last;
    nl_fragment fragment;
    nl_window window;
    nl_pull_token token = 0;
    uint64_t now = 0;
    int pending = 0;
    unsigned steps = 0;
    uint32_t slot = 1u + take(&in) * 37u;
    if (nl_radio_init(&radio, take(&in), slot, take(&in) % (slot + 1u), take32(&in)) != NL_OK) return 0;
    while (in.size > 0 && ++steps < 4096) {
        switch (take(&in) % OP_COUNT) {
        case OP_FRAME: spi_request(&radio, &in, &last, &token, &pending); break;
        case OP_RECEIVE: air_receive(&radio, &in, now); break;
        case OP_COMMIT:
            /* Commit the last prepared pull, or a forged token when none is pending. */
            if (pending) (void)nl_radio_commit_pull(&radio, &last, (take(&in) & 1u) ? token : token + 1u);
            pending = 0;
            break;
        case OP_WINDOW:
            if (nl_radio_next_window(&radio, now, &window) == NL_OK) REQUIRE(window.zone < NL_ZONE_COUNT);
            break;
        case OP_TX:
            if (nl_radio_prepare_tx(&radio, now, &fragment, &window) == NL_OK)
                REQUIRE(nl_fragment_validate(&fragment) == NL_OK && fragment.zone == window.zone);
            break;
        case OP_PULL:
            if (nl_radio_pull(&radio, &fragment) == NL_OK) REQUIRE(nl_fragment_validate(&fragment) == NL_OK);
            break;
        case OP_TIME:
            /* Mostly small steps, occasionally huge ones to hit idle expiry and overflow edges. */
            now += (take(&in) & 0x80u) ? (uint64_t)take32(&in) << 16 : take(&in) * 50u;
            break;
        default:
            switch (take(&in) % 4u) {
            case 0: (void)nl_radio_set_active(&radio, take(&in)); break;
            case 1: (void)nl_radio_set_rx_policy(&radio, (nl_rx_policy)(take(&in) % 3u)); break;
            case 2: nl_radio_request_management(&radio); break;
            default: (void)nl_radio_ready(&radio); break;
            }
            break;
        }
    }
    return 0;
}
