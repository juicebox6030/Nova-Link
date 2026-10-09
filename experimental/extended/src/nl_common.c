/**
 * @file nl_common.c
 * @brief Status strings and the logging hook.
 */
#include "nova_link/nl_common.h"
#include "nova_link/nl_log.h"

#include <stdio.h>

static nl_log_sink_t s_sink;
static void *s_sink_user;
static nl_log_level_t s_level = NL_LOG_INFO;

const char *nl_status_str(int status)
{
    switch (status) {
    case NL_OK: return "ok";
    case NL_ERR_ARG: return "invalid argument";
    case NL_ERR_SIZE: return "size out of range";
    case NL_ERR_FULL: return "full";
    case NL_ERR_EMPTY: return "empty";
    case NL_ERR_PERM: return "not permitted";
    case NL_ERR_CONFLICT: return "conflict";
    case NL_ERR_NOT_FOUND: return "not found";
    case NL_ERR_CRC: return "crc mismatch";
    case NL_ERR_PROTO: return "protocol error";
    case NL_ERR_IO: return "i/o error";
    default: return status > 0 ? "ok" : "unknown error";
    }
}

void nl_log_set_sink(nl_log_sink_t sink, void *user)
{
    s_sink = sink;
    s_sink_user = user;
}

void nl_log_set_level(nl_log_level_t level)
{
    s_level = level;
}

const char *nl_log_level_str(nl_log_level_t level)
{
    switch (level) {
    case NL_LOG_DEBUG: return "DEBUG";
    case NL_LOG_INFO: return "INFO";
    case NL_LOG_WARN: return "WARN";
    case NL_LOG_ERROR: return "ERROR";
    default: return "?";
    }
}

void nl_log(nl_log_level_t level, const char *module, const char *fmt, ...)
{
    if (s_sink == NULL || level < s_level) {
        return;
    }
    char buf[160];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);
    s_sink(level, module, buf, s_sink_user);
}
