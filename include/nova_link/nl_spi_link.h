/**
 * @file nl_spi_link.h
 * @brief Host-side SPI master driver for the link protocol.
 *
 * Implements nl_link_ops_t over a minimal full-duplex SPI HAL, using the
 * two-phase exchange described in nl_link.h: one transaction carries the
 * request, a second one (after a turnaround delay) clocks out filler zeros
 * and reads the response frame the radio prepared.
 *
 * PULL is never retried: the radio dequeues the fragment when it answers,
 * so a retry after a corrupted response would skip a fragment rather than
 * repeat it. PING and STATUS are idempotent and are retried.
 */
#ifndef NL_SPI_LINK_H
#define NL_SPI_LINK_H

#include "nl_host.h"
#include "nl_link.h"

#ifdef __cplusplus
extern "C" {
#endif

/** Platform SPI access. Only @c transfer is required. */
typedef struct {
    /** Full-duplex transfer of @p len bytes with chip select asserted. */
    int (*transfer)(void *ctx, const uint8_t *tx, uint8_t *rx, size_t len);
    /** Level of the radio's INT_READY line (NULL = unknown). */
    bool (*int_ready)(void *ctx);
    /** Busy-wait or sleep (NULL = no delay). */
    void (*delay_us)(void *ctx, uint32_t us);
    void *ctx;
} nl_spi_hal_t;

/** Driver counters. */
typedef struct {
    uint32_t transactions;
    uint32_t crc_errors;   /**< Response frame failed its checksum. */
    uint32_t proto_errors; /**< No frame, or unexpected response code. */
    uint32_t io_errors;    /**< HAL transfer failures. */
    uint32_t retries;
} nl_spi_link_stats_t;

typedef struct {
    nl_spi_hal_t hal;
    uint32_t turnaround_us; /**< Gap between request and response read. */
    uint8_t retries;        /**< Extra attempts for PING / STATUS. */
    uint8_t tx[NL_LINK_FRAME_MAX];
    uint8_t rx[NL_LINK_FRAME_MAX];
    nl_spi_link_stats_t stats;
} nl_spi_link_t;

/** Default turnaround: generous for a CC1352R running its SPI ISR. */
#define NL_SPI_DEFAULT_TURNAROUND_US 50u

void nl_spi_link_init(nl_spi_link_t *l, const nl_spi_hal_t *hal);

/** Fill @p ops so a host can use this driver. */
void nl_spi_link_ops(nl_spi_link_t *l, nl_link_ops_t *ops);

int nl_spi_link_ping(nl_spi_link_t *l, nl_link_pong_t *out);
int nl_spi_link_push(nl_spi_link_t *l, const uint8_t *frag, size_t len);
/** @return fragment length (> 0), 0 if the radio had nothing, or < 0. */
int nl_spi_link_pull(nl_spi_link_t *l, uint8_t *buf, size_t cap);
int nl_spi_link_status(nl_spi_link_t *l, nl_radio_status_t *out);
/** Send RADIO_CONFIG then ZONE_CONFIG (either may be NULL). */
int nl_spi_link_configure(nl_spi_link_t *l, const nl_radio_params_t *params,
                          const nl_zone_plan_t *plan);

#ifdef __cplusplus
}
#endif

#endif /* NL_SPI_LINK_H */
