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
 * Slots in the SPI ISR -> main loop handoff (nl_radio_spi_isr()). One is
 * enough when the host waits for each reply; two absorb a request that
 * arrives while the previous one is still being processed.
 */
#ifndef NL_RADIO_SPI_SLOTS
#define NL_RADIO_SPI_SLOTS 2
#endif

/**
 * Set to 1 for a build whose core code may run in interrupt context (the
 * radio firmware calling nl_radio_spi_complete() from the SPI ISR). It
 * compiles out every NL_LOG* call, including NL_LOGE, by defaulting
 * NL_LOG_MIN_LEVEL to 4 (NL_LOG_NONE): nl_log() formats with vsnprintf
 * into a 160-byte stack buffer and calls an arbitrary sink. Rejected
 * frames are still counted in nl_radio_t.
 */
#ifndef NL_ISR_BUILD
#define NL_ISR_BUILD 0
#endif

/**
 * Logging on the radio's SPI request path (frame parsing and the link
 * command handlers behind nl_radio_spi_complete() / nl_radio_poll()),
 * which runs in the SPI ISR on the direct path. 0 (default) compiles those
 * NL_LOG* calls out; the events are still counted (nl_radio_t spi_rejected,
 * spi_crc_errors). Set to 1 when that path runs in task context and the
 * warnings are wanted. Task-context logging elsewhere is unaffected.
 */
#ifndef NL_LOG_IN_ISR
#define NL_LOG_IN_ISR 0
#endif

/**
 * Compile-time log floor; messages below this level are compiled out.
 * 0=DEBUG 1=INFO 2=WARN 3=ERROR 4=off (numeric so it works in preprocessor
 * tests).
 */
#ifndef NL_LOG_MIN_LEVEL
#if NL_ISR_BUILD
#define NL_LOG_MIN_LEVEL 4
#else
#define NL_LOG_MIN_LEVEL 0
#endif
#endif

/**
 * Compiler barrier: stops the compiler from moving memory accesses across
 * it. It does not order the CPU; on a single-core Cortex-M (CC1352R's M4F)
 * that is enough, because an interrupt observes the core's own accesses in
 * program order. A port with a write buffer or a second core that shares
 * the data must define it as a hardware barrier, e.g. `__DMB()`.
 */
#ifndef NL_COMPILER_BARRIER
#if defined(__GNUC__) || defined(__clang__)
#define NL_COMPILER_BARRIER() __asm__ __volatile__("" ::: "memory")
#else
#error "define NL_COMPILER_BARRIER() for this compiler"
#endif
#endif

/**
 * Critical sections around the few shared-state updates the main loop and
 * an interrupt can race on: queue counts/indices, the params/plan swap and
 * the SPI outbox hand-over. Bodies are a handful of loads and stores; no
 * call made inside one can block or log.
 *
 * Nest-safe by design: ENTER saves the previous interrupt state into a
 * local and masks, EXIT restores what was saved instead of unconditionally
 * unmasking, so a section inside another one (or inside an ISR) never
 * re-enables interrupts early. The defaults are no-ops, which is correct
 * when the core only ever runs in one context (the host, the simulator, a
 * radio that calls nl_radio_spi_complete() from its main loop). A Cortex-M
 * port that runs SPI handling in an ISR defines:
 *
 * @code
 * #define NL_IRQ_STATE_T uint32_t
 * #define NL_CRITICAL_ENTER(s) do { (s) = __get_PRIMASK(); __disable_irq(); } while (0)
 * #define NL_CRITICAL_EXIT(s)  __set_PRIMASK(s)
 * @endcode
 *
 * (or raises BASEPRI to the SPI interrupt's priority, to leave the RF core
 * interrupts alone).
 */
#ifndef NL_IRQ_STATE_T
#define NL_IRQ_STATE_T unsigned int
#endif
typedef NL_IRQ_STATE_T nl_irq_state_t;

#ifndef NL_CRITICAL_ENTER
#define NL_CRITICAL_ENTER(s) ((s) = 0u)
#endif
#ifndef NL_CRITICAL_EXIT
#define NL_CRITICAL_EXIT(s) ((void)(s))
#endif

/**
 * Hooks around every plugin callback the host makes (init, deinit,
 * on_meta, on_fragment, on_tick), with the plugin slot as @p id. Meant for
 * an MPU port that opens the plugin's memory region on enter and closes it
 * on exit, or for profiling. Pairs nest when a plugin calls
 * nl_host_register()/nl_host_unregister() from its own callback. The
 * application callbacks (monitor, meta hook) are not wrapped.
 *
 * The core places no stack canary around plugin calls: a plugin runs on
 * the caller's stack, so a canary checked on return only reports an
 * overflow after the return address and the host's frames are already
 * overwritten. Overflow detection belongs to the toolchain and RTOS
 * (-fstack-protector, FreeRTOS stack watchpoints on the ESP32-S3, an MPU
 * guard region), which these hooks can arm per plugin.
 */
#ifndef NL_PLUGIN_ENTER
#define NL_PLUGIN_ENTER(id) ((void)0)
#endif
#ifndef NL_PLUGIN_EXIT
#define NL_PLUGIN_EXIT(id) ((void)0)
#endif

/* Overrides are checked against the field widths that hold them: plugin
 * slots, queue indices/counts and the CCA defer counter are uint8_t, the
 * meta queue fill level is uint16_t, and a segment index is 4 bits with a
 * uint16_t received-mask. NL_LINK_MAX_DATA is checked in nl_link.h. */
#if NL_MAX_PLUGINS < 1 || NL_MAX_PLUGINS > 255
#error "NL_MAX_PLUGINS must be 1..255"
#endif
#if NL_META_QUEUE_BYTES < 1 || NL_META_QUEUE_BYTES > 65535
#error "NL_META_QUEUE_BYTES must be 1..65535"
#endif
#if NL_RADIO_TXQ_DEPTH < 1 || NL_RADIO_TXQ_DEPTH > 255
#error "NL_RADIO_TXQ_DEPTH must be 1..255"
#endif
#if NL_RADIO_CCA_MAX_DEFERS > 255
#error "NL_RADIO_CCA_MAX_DEFERS must be at most 255"
#endif
#if NL_RADIO_RXQ_DEPTH < 1 || NL_RADIO_RXQ_DEPTH > 255
#error "NL_RADIO_RXQ_DEPTH must be 1..255"
#endif
#if NL_RADIO_SPI_SLOTS < 1 || NL_RADIO_SPI_SLOTS > 16
#error "NL_RADIO_SPI_SLOTS must be 1..16"
#endif
#if (NL_RADIO_SPI_SLOTS & (NL_RADIO_SPI_SLOTS - 1)) != 0
#error "NL_RADIO_SPI_SLOTS must be a power of two (free-running uint8_t index)"
#endif
#if NL_SEG_MAX_SEGMENTS < 1 || NL_SEG_MAX_SEGMENTS > 16
#error "NL_SEG_MAX_SEGMENTS must be 1..16"
#endif

#endif /* NL_CONFIG_H */
