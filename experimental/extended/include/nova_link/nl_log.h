/**
 * @file nl_log.h
 * @brief Minimal logging/alert hook.
 *
 * The core never prints directly. Applications install a sink with
 * nl_log_set_sink(); the ESP32 port forwards to ESP_LOG, the simulator to
 * stderr, and tests capture messages to assert on warnings.
 */
#ifndef NL_LOG_H
#define NL_LOG_H

#include <stdarg.h>

#ifdef __cplusplus
extern "C" {
#endif

/** Log severities. */
typedef enum {
    NL_LOG_DEBUG = 0,
    NL_LOG_INFO = 1,
    NL_LOG_WARN = 2,
    NL_LOG_ERROR = 3,
    NL_LOG_NONE = 4,
} nl_log_level_t;

/**
 * Log sink callback.
 * @param level   Message severity.
 * @param module  Short module tag, e.g. "host", "radio", "zone".
 * @param msg     Formatted, NUL-terminated message (no trailing newline).
 * @param user    Pointer passed to nl_log_set_sink().
 */
typedef void (*nl_log_sink_t)(nl_log_level_t level, const char *module,
                              const char *msg, void *user);

/** Install the log sink (NULL disables logging). Not thread-safe. */
void nl_log_set_sink(nl_log_sink_t sink, void *user);

/** Set the runtime minimum level (default NL_LOG_INFO). */
void nl_log_set_level(nl_log_level_t level);

/** printf-style logging entry point; prefer the NL_LOG* macros. */
void nl_log(nl_log_level_t level, const char *module, const char *fmt, ...)
#if defined(__GNUC__)
    __attribute__((format(printf, 3, 4)))
#endif
    ;

/** Return "DEBUG", "INFO", "WARN", or "ERROR". */
const char *nl_log_level_str(nl_log_level_t level);

#include "nl_config.h"

#if NL_LOG_MIN_LEVEL <= 0
#define NL_LOGD(mod, ...) nl_log(NL_LOG_DEBUG, mod, __VA_ARGS__)
#else
#define NL_LOGD(mod, ...) ((void)0)
#endif
#if NL_LOG_MIN_LEVEL <= 1
#define NL_LOGI(mod, ...) nl_log(NL_LOG_INFO, mod, __VA_ARGS__)
#else
#define NL_LOGI(mod, ...) ((void)0)
#endif
#if NL_LOG_MIN_LEVEL <= 2
#define NL_LOGW(mod, ...) nl_log(NL_LOG_WARN, mod, __VA_ARGS__)
#else
#define NL_LOGW(mod, ...) ((void)0)
#endif
#define NL_LOGE(mod, ...) nl_log(NL_LOG_ERROR, mod, __VA_ARGS__)

#ifdef __cplusplus
}
#endif

#endif /* NL_LOG_H */
