#ifndef NOVA_LINK_SECURE_H
#define NOVA_LINK_SECURE_H

#include "nova_link/fragment.h"
#include "nova_link/radio.h"

/** @file secure.h Optional AES-128-CCM air security (build with NOVA_SECURITY=ON).
 *
 * Sealed air fragment, 14..114 bytes:
 *
 *     [header][sequence][counter:4 BE][payload][MIC:8]
 *
 * Header and sequence stay readable so receivers can schedule and deduplicate,
 * but they, the counter and the payload are all authenticated. In
 * NL_SECURE_ENCRYPT mode the payload is also encrypted. The CCM nonce is
 * origin | counter | mode, so every origin must be unique per key and its
 * counter must never repeat: persist reservations (see nl_secure_persist_fn).
 *
 * Cost per fragment: 12 extra air bytes, plus 2 + ceil((6 + payload) / 16)
 * AES blocks (AUTH) or 3 + 2 * ceil(payload / 16) blocks (ENCRYPT), each way.
 */
#define NL_SECURE_COUNTER_SIZE 4u
#define NL_SECURE_MIC_SIZE 8u
#define NL_SECURE_OVERHEAD (NL_SECURE_COUNTER_SIZE + NL_SECURE_MIC_SIZE)
#define NL_SECURE_AIR_MIN (NL_FRAGMENT_MIN + NL_SECURE_OVERHEAD)
#define NL_SECURE_AIR_MAX (NL_FRAGMENT_MAX + NL_SECURE_OVERHEAD)
/** Counters reserved per persist call; a reboot skips at most this many. */
#ifndef NL_SECURE_RESERVE
#define NL_SECURE_RESERVE 1024u
#endif
/** Size of the expanded key. A hardware port may shrink it (see NL_SECURE_EXTERNAL_AES). */
#ifndef NL_AES_STATE_SIZE
#define NL_AES_STATE_SIZE 176u
#endif

typedef enum {
    NL_SECURE_AUTH = 1,   /**< Authenticate everything; payload readable on air. */
    NL_SECURE_ENCRYPT = 2 /**< Authenticate and encrypt the payload. */
} nl_secure_mode;

/** Store `reserved_until` in non-volatile memory before returning NL_OK. At the
 * next boot pass the stored value as `tx_counter` to nl_secure_init(). Any
 * other result blocks sealing, so a failed write can never reuse a nonce.
 */
typedef nl_status (*nl_secure_persist_fn)(void *context, uint32_t reserved_until);

typedef struct {
    uint64_t sealed;
    uint64_t opened;
    uint64_t auth_failed; /**< Bad MIC, wrong key/mode, or malformed sealed frame. */
    uint64_t replayed;    /**< Authentic but already seen counter. */
    uint64_t too_old;     /**< Authentic but older than the replay window. */
} nl_secure_stats;

typedef struct nl_secure {
    uint8_t key[NL_AES_STATE_SIZE];
    nl_secure_mode mode;
    uint32_t tx_counter;
    uint32_t tx_limit;
    nl_secure_persist_fn persist;
    void *persist_context;
    uint32_t rx_top[NL_ORIGIN_COUNT];    /**< Highest accepted counter per origin. */
    uint32_t rx_window[NL_ORIGIN_COUNT]; /**< Bit i: counter top - i was accepted. */
    uint8_t rx_known;                    /**< Origins with replay state. */
    nl_secure_stats stats;
} nl_secure;

/** Expand `key` and reset replay state. `persist` may be NULL only when the key
 * is never reused across reboots (e.g. a fresh session key per power cycle).
 */
nl_status nl_secure_init(nl_secure *secure, const uint8_t key[16], nl_secure_mode mode,
                         uint32_t tx_counter, nl_secure_persist_fn persist, void *context);
/** Overwrite key material and counters (call before releasing the memory). */
void nl_secure_wipe(nl_secure *secure);
/** Reject counters <= `counter` from `origin`, e.g. restored after a receiver reboot. */
nl_status nl_secure_set_rx_floor(nl_secure *secure, uint8_t origin, uint32_t counter);
/** Seal one fragment with the next counter. FULL once the counter space is spent. */
nl_status nl_secure_seal(nl_secure *secure, const nl_fragment *fragment,
                         uint8_t *bytes, size_t capacity, size_t *size);
/** Verify and decode without changing replay state. On success `fragment` and
 * `counter` are written; on failure `fragment` holds no plaintext.
 * Returns INTEGRITY (forged/corrupt), DUPLICATE or STALE (replay).
 */
nl_status nl_secure_open(nl_secure *secure, const uint8_t *bytes, size_t size,
                         nl_fragment *fragment, uint32_t *counter);
/** Record an opened counter as used once the frame has been consumed. */
void nl_secure_accept(nl_secure *secure, uint8_t origin, uint32_t counter);

/** Open a sealed air frame and hand it to the radio. The counter is recorded
 * only once the radio consumed the frame (anything but NL_ERR_FULL), so a
 * replayed or forged BURST can never trigger a hold. A late counter (below one
 * already accepted from that origin) is delivered only while the radio still
 * tracks its stream; once the stream is unknown or idle-expired it would look
 * like a fresh start, so it is refused as STALE and burned. This stops an
 * attacker from holding a frame back and injecting it out of order later.
 * Use on the side that owns the key (radio adapter / co-processor), from the
 * radio's single task.
 */
nl_status nl_radio_receive_sealed(nl_radio *radio, nl_secure *secure, const uint8_t *bytes,
                                  size_t size, uint64_t now_us);

/** Block cipher used by the CCM layer. Define NL_SECURE_EXTERNAL_AES and supply
 * both functions to use a hardware engine; `state` is NL_AES_STATE_SIZE bytes.
 */
void nl_aes128_init(uint8_t *state, const uint8_t key[16]);
void nl_aes128_encrypt(const uint8_t *state, const uint8_t in[16], uint8_t out[16]);

#endif
