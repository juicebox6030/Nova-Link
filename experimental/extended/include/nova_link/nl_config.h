/**
 * @file nl_config.h
 * @brief Compile-time sizing for the NOVA-LINK core.
 *
 * Every value can be overridden with a compiler define (e.g.
 * `-DNL_MAX_PLUGINS=16`) or by providing `nl_config_user.h` on the include
 * path and building with `-DNL_HAVE_CONFIG_USER`.
 */
#ifndef NL_CONFIG_H
#define NL_CONFIG_H

#ifdef NL_HAVE_CONFIG_USER
#include "nl_config_user.h"
#endif

/** Maximum plugins registered on one host. */
#ifndef NL_MAX_PLUGINS
#define NL_MAX_PLUGINS 8
#endif

/** Zone 0 metadata queue size in bytes (TLV records waiting to be sent). */
#ifndef NL_META_QUEUE_BYTES
#define NL_META_QUEUE_BYTES 512
#endif

/**
 * Fragments buffered per zone on the radio, waiting for transmission. Also
 * the largest segmented message the host will send in one go (a 512-channel
 * DMX universe needs 6 segments). When full, the oldest fragment is evicted.
 */
#ifndef NL_RADIO_TXQ_DEPTH
#define NL_RADIO_TXQ_DEPTH 8
#endif

/**
 * Clear-channel checks a fragment may fail in a row before it is sent
 * anyway, so a jammed or permanently busy channel cannot starve the queue.
 */
#ifndef NL_RADIO_CCA_MAX_DEFERS
#define NL_RADIO_CCA_MAX_DEFERS 8
#endif

/** Received fragments buffered on the radio, waiting for the host to pull. */
#ifndef NL_RADIO_RXQ_DEPTH
#define NL_RADIO_RXQ_DEPTH 16
#endif

/** Maximum data bytes in one host <-> radio link frame. */
#ifndef NL_LINK_MAX_DATA
#define NL_LINK_MAX_DATA 128
#endif

/** Maximum segments in one segmented message (wire limit is 16). */
#ifndef NL_SEG_MAX_SEGMENTS
#define NL_SEG_MAX_SEGMENTS 16
#endif

/**
 * Compile-time log floor; messages below this level are compiled out.
 * 0=DEBUG 1=INFO 2=WARN 3=ERROR (numeric so it works in preprocessor tests).
 */
#ifndef NL_LOG_MIN_LEVEL
#define NL_LOG_MIN_LEVEL 0
#endif

#endif /* NL_CONFIG_H */
