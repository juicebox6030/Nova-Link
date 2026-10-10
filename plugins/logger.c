#include "nova_link/logger_plugin.h"

static nl_status start(nl_host *host, nl_plugin_id plugin, void *context)
{
    nl_logger_context *logger = context;
    if (logger == NULL || logger->callback == NULL) return NL_ERR_ARGUMENT;
    return nl_host_attach_logger(host, plugin, logger->callback, logger->context);
}

static void stop(nl_host *host, nl_plugin_id plugin, void *context)
{
    (void)context;
    /* The host checks the exact registration owner. Failed duplicate startup
     * must never detach the existing service, even with shared context storage.
     */
    (void)nl_host_detach_logger(host, plugin);
}

nl_status nl_logger_init(nl_logger_context *logger, nl_log_fn callback, void *context)
{
    if (logger == NULL || callback == NULL) return NL_ERR_ARGUMENT;
    logger->callback = callback;
    logger->context = context;
    return NL_OK;
}

nl_plugin nl_logger_plugin(nl_logger_context *logger)
{
    nl_plugin plugin = {.start = start, .stop = stop, .context = logger};
    return plugin;
}

nl_module nl_logger_module(nl_logger_context *logger)
{
    nl_module module = {.name = "logger", .version = "1", .kind = NL_MODULE_SERVICE,
                        .service = logger, .hooks = nl_logger_plugin(logger)};
    return module;
}
