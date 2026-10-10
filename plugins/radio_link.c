#include <string.h>
#include "nova_link/radio_plugin.h"

static nl_status exchange(nl_radio_link *link, const nl_frame *request,
                          nl_frame *response, nl_pull_token *token)
{
    nl_status status;
    if (link->exchanging) return NL_ERR_BUSY;
    link->exchanging = true;
    status = link->config.exchange(link->config.context, request, response, token);
    link->exchanging = false;
    link->last_status = status;
    if (status != NL_OK && status != NL_ERR_EMPTY) ++link->stats.exchange_errors;
    return status;
}

static nl_status send_fragment(void *context, const nl_fragment *fragment)
{
    nl_radio_link *link = context;
    nl_frame request, response = {0};
    nl_pull_token token = 0;
    nl_status status;
    if (link == NULL || link->host == NULL) return NL_ERR_NOT_FOUND;
    status = nl_frame_from_fragment(NL_COMMAND_PUSH, fragment, &request);
    if (status == NL_OK) status = exchange(link, &request, &response, &token);
    if (status == NL_OK) ++link->stats.tx_accepted;
    else ++link->stats.tx_errors;
    link->last_status = status;
    return status;
}

static nl_status start(nl_host *host, nl_plugin_id plugin, void *context)
{
    nl_radio_link *link = context;
    nl_status status;
    if (link == NULL || link->config.exchange == NULL || link->config.poll_budget == 0u)
        return NL_ERR_ARGUMENT;
    if (link->host != NULL) return NL_ERR_BUSY;
    status = nl_host_attach_transport(host, plugin, send_fragment, link);
    if (status != NL_OK) return status;
    link->host = host;
    link->plugin = plugin;
    link->backend_started = true;
    if (link->config.start != NULL) {
        link->exchanging = true;
        status = link->config.start(link->config.context);
        link->exchanging = false;
    }
    link->last_status = status;
    return status;
}

static nl_status can_stop(nl_host *host, nl_plugin_id plugin, void *context)
{
    nl_radio_link *link = context;
    nl_status status = NL_OK;
    if (link == NULL || link->host != host || link->plugin != plugin) return NL_OK;
    if (link->pending || link->exchanging) return NL_ERR_BUSY;
    if (link->config.can_stop != NULL) {
        link->exchanging = true;
        status = link->config.can_stop(link->config.context);
        link->exchanging = false;
    }
    return status;
}

static void stop(nl_host *host, nl_plugin_id plugin, void *context)
{
    nl_radio_link *link = context;
    if (link == NULL || link->host != host || link->plugin != plugin) return;
    link->last_status = nl_host_detach_transport(host, plugin);
    if (link->backend_started && link->config.stop != NULL) {
        link->exchanging = true;
        link->config.stop(link->config.context);
        link->exchanging = false;
    }
    link->backend_started = false;
    link->host = NULL;
    link->plugin = NL_PLUGIN_ID_NONE;
}

static void poll(nl_host *host, nl_plugin_id plugin, uint64_t now_us, void *context)
{
    nl_radio_link *link = context;
    const nl_frame request = {.command = NL_COMMAND_PULL};
    uint16_t attempt;
    nl_status status;
    if (link == NULL || link->host != host || link->plugin != plugin || link->exchanging) return;
    for (attempt = 0; attempt < link->config.poll_budget; ++attempt) {
        if (!link->pending) {
            status = exchange(link, &request, &link->pending_response, &link->pending_token);
            if (status != NL_OK) return;
            link->pending = true;
            link->settled = false;
            ++link->stats.rx_pulled;
        }
        if (!link->settled) {
            status = nl_host_receive_frame(host, &link->pending_response, now_us);
            link->last_receive_status = status;
            link->last_status = status;
            if (status == NL_ERR_BUSY) {
                ++link->stats.receive_retries;
                return;
            }
            link->settled = true;
            if (status == NL_OK) ++link->stats.rx_delivered;
            else ++link->stats.rx_discarded;
        }
        if (link->config.commit != NULL) {
            link->exchanging = true;
            status = link->config.commit(link->config.context, &link->pending_response, link->pending_token);
            link->exchanging = false;
            link->last_status = status;
            if (status != NL_OK) {
                ++link->stats.commit_errors;
                if (status != NL_ERR_STALE && status != NL_ERR_EMPTY) return;
                ++link->stats.commit_abandoned;
            } else ++link->stats.commits;
        }
        link->pending = false;
        link->settled = false;
    }
}

nl_status nl_radio_link_init(nl_radio_link *link, const nl_radio_link_config *config)
{
    nl_radio_link initialized;
    if (link == NULL || config == NULL || config->exchange == NULL || config->poll_budget == 0u)
        return NL_ERR_ARGUMENT;
    memset(&initialized, 0, sizeof(initialized));
    initialized.config = *config;
    initialized.plugin = NL_PLUGIN_ID_NONE;
    *link = initialized;
    return NL_OK;
}

nl_plugin nl_radio_link_plugin(nl_radio_link *link)
{
    nl_plugin plugin = {
        .start = start,
        .stop = stop,
        .context = link,
        .poll = poll,
        .can_stop = can_stop
    };
    return plugin;
}

nl_module nl_radio_link_module(nl_radio_link *link)
{
    nl_module module = {
        .name = "radio-link",
        .version = "1",
        .kind = NL_MODULE_TRANSPORT,
        .service = link
    };
    module.hooks = nl_radio_link_plugin(link);
    return module;
}
