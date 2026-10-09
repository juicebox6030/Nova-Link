#ifndef NOVA_LINK_STATUS_H
#define NOVA_LINK_STATUS_H

/** @file status.h Shared error codes. No API allocates memory or performs I/O. */
typedef enum {
    NL_OK = 0,
    NL_ERR_ARGUMENT,
    NL_ERR_SIZE,
    NL_ERR_FORMAT,
    NL_ERR_ACCESS,
    NL_ERR_CONFLICT,
    NL_ERR_FULL,
    NL_ERR_EMPTY,
    NL_ERR_DUPLICATE,
    NL_ERR_STALE,
    NL_ERR_BUSY,
    NL_ERR_UNSUPPORTED,
    NL_ERR_NOT_FOUND
} nl_status;

/** Return a static, human-readable name for a status code. */
const char *nl_status_name(nl_status status);

#endif
