#include "nova_link/status.h"

const char *nl_status_name(nl_status status)
{
    switch (status) {
    case NL_OK: return "ok";
    case NL_ERR_ARGUMENT: return "invalid argument";
    case NL_ERR_SIZE: return "invalid size";
    case NL_ERR_FORMAT: return "invalid format";
    case NL_ERR_ACCESS: return "access denied";
    case NL_ERR_CONFLICT: return "conflict";
    case NL_ERR_FULL: return "queue full";
    case NL_ERR_EMPTY: return "empty";
    case NL_ERR_DUPLICATE: return "duplicate";
    case NL_ERR_STALE: return "stale";
    case NL_ERR_BUSY: return "busy";
    case NL_ERR_UNSUPPORTED: return "unsupported";
    case NL_ERR_NOT_FOUND: return "not found";
    default: return "unknown status";
    }
}
