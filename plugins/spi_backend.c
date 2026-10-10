#include <string.h>
#include "nova_link/spi_backend.h"

static nl_status driver_settle(nl_spi_backend *backend, bool consume)
{
    nl_status status;
    backend->calling = true;
    status = backend->driver.settle(backend->driver.context, backend->receipt, consume);
    backend->calling = false;
    backend->last_status = status;
    if (status != NL_OK && status != NL_ERR_STALE && status != NL_ERR_EMPTY)
        ++backend->stats.driver_errors;
    return status;
}

static bool released(nl_status status)
{
    return status == NL_OK || status == NL_ERR_STALE || status == NL_ERR_EMPTY;
}

static nl_status backend_exchange(void *context, const nl_frame *request,
                                  nl_frame *response, nl_pull_token *token)
{
    nl_spi_backend *backend = context;
    uint8_t bytes[NL_FRAME_MAX];
    size_t size = 0;
    nl_status status;
    if (backend == NULL || request == NULL || response == NULL || token == NULL)
        return NL_ERR_ARGUMENT;
    if (!backend->running) return NL_ERR_NOT_FOUND;
    if (backend->calling) return NL_ERR_BUSY;
    status = nl_frame_validate(request);
    if (status != NL_OK) return status;
    if (request->command == NL_COMMAND_PULL) {
        if (!backend->rx_pending) return NL_ERR_EMPTY;
        *response = backend->rx_frame;
        *token = backend->receipt;
        return NL_OK;
    }
    if (request->command != NL_COMMAND_PUSH) return NL_ERR_UNSUPPORTED;
    if (backend->tx_pending) return NL_ERR_BUSY;
    status = nl_frame_encode(request, bytes, sizeof(bytes), &size);
    if (status != NL_OK) return status;
    memcpy(backend->tx, bytes, size);
    backend->tx_size = size;
    backend->tx_pending = true;
    ++backend->stats.tx_accepted;
    return NL_OK;
}

static nl_status backend_commit(void *context, const nl_frame *response,
                                nl_pull_token token)
{
    nl_spi_backend *backend = context;
    nl_status status;
    if (backend == NULL || response == NULL) return NL_ERR_ARGUMENT;
    if (!backend->running) return NL_ERR_NOT_FOUND;
    if (backend->calling) return NL_ERR_BUSY;
    if (!backend->rx_pending || token != backend->receipt) return NL_ERR_STALE;
    if (response->command != backend->rx_frame.command ||
        response->data_size != backend->rx_frame.data_size ||
        memcmp(response->data, backend->rx_frame.data, backend->rx_frame.data_size) != 0)
        return NL_ERR_STALE;
    status = driver_settle(backend, true);
    if (released(status)) {
        backend->rx_pending = false;
        backend->receipt = 0;
        if (status == NL_OK) ++backend->stats.rx_committed;
    }
    return status;
}

static nl_status backend_idle(void *context)
{
    nl_spi_backend *backend = context;
    nl_status status = NL_OK;
    if (backend == NULL) return NL_ERR_ARGUMENT;
    if (backend->calling || backend->tx_pending || backend->inflight ||
        backend->rx_pending || backend->abort_pending) return NL_ERR_BUSY;
    if (backend->driver.can_stop != NULL) {
        backend->calling = true;
        status = backend->driver.can_stop(backend->driver.context);
        backend->calling = false;
    }
    return status;
}

static nl_status start(nl_host *host, nl_plugin_id plugin, void *context)
{
    nl_spi_backend *backend = context;
    nl_status status = NL_OK;
    if (backend == NULL || backend->driver.begin == NULL ||
        backend->driver.finish == NULL || backend->driver.ready == NULL ||
        backend->driver.stop == NULL || backend->driver.settle == NULL)
        return NL_ERR_ARGUMENT;
    if (backend->host != NULL) return NL_ERR_BUSY;
    backend->host = host;
    backend->plugin = plugin;
    backend->started = true;
    if (backend->driver.start != NULL) {
        backend->calling = true;
        status = backend->driver.start(backend->driver.context);
        backend->calling = false;
    }
    backend->running = status == NL_OK;
    backend->last_status = status;
    return status;
}

static void stop(nl_host *host, nl_plugin_id plugin, void *context)
{
    nl_spi_backend *backend = context;
    if (backend == NULL || backend->host != host || backend->plugin != plugin) return;
    backend->running = false;
    if (backend->started) {
        backend->calling = true;
        backend->driver.stop(backend->driver.context);
        backend->calling = false;
    }
    backend->started = false;
    backend->host = NULL;
    backend->plugin = NL_PLUGIN_ID_NONE;
    backend->tx_pending = false;
    backend->tx_uncertain = false;
    backend->inflight = false;
    backend->rx_pending = false;
    backend->abort_pending = false;
    backend->receipt = 0;
    backend->have_clock = false;
}

static nl_status can_stop(nl_host *host, nl_plugin_id plugin, void *context)
{
    nl_spi_backend *backend = context;
    if (backend == NULL || backend->host != host || backend->plugin != plugin) return NL_OK;
    return backend_idle(backend);
}

static void abort_receipt(nl_spi_backend *backend)
{
    nl_status status = driver_settle(backend, false);
    if (released(status)) {
        backend->abort_pending = false;
        backend->receipt = 0;
        ++backend->stats.rx_aborted;
    }
}

static void complete(nl_spi_backend *backend, uint64_t now_us)
{
    nl_status status;
    size_t size = 0;
    nl_pull_token receipt = 0;
    bool uncertain = false;
    backend->calling = true;
    status = backend->driver.finish(backend->driver.context, backend->transaction,
                                   now_us, backend->response, sizeof(backend->response),
                                   &size, &receipt, &uncertain);
    backend->calling = false;
    backend->last_status = status;
    if (status == NL_ERR_BUSY) return;
    backend->inflight = false;
    if (!backend->pulling && (uncertain || receipt != 0u ||
        (status == NL_OK && size != 0u))) {
        if (status == NL_OK || receipt != 0u) {
            backend->last_status = NL_ERR_FORMAT;
            ++backend->stats.malformed;
        }
        ++backend->stats.driver_errors;
        backend->tx_uncertain = true;
        ++backend->stats.tx_uncertain;
        if (receipt != 0u) {
            backend->receipt = receipt;
            backend->abort_pending = true;
            abort_receipt(backend);
        }
        return;
    }
    if (status == NL_OK && backend->pulling && receipt != 0u && size <= NL_FRAME_MAX) {
        status = nl_frame_decode(backend->response, size, &backend->rx_frame);
        if (status == NL_OK && backend->rx_frame.command != NL_COMMAND_FRAGMENT)
            status = NL_ERR_FORMAT;
        if (status == NL_OK) {
            backend->response_size = size;
            backend->receipt = receipt;
            backend->rx_pending = true;
            ++backend->stats.rx_prepared;
            return;
        }
    } else if (status == NL_OK && !backend->pulling && size == 0u && receipt == 0u) {
        backend->tx_pending = false;
        ++backend->stats.tx_completed;
        return;
    } else if (status == NL_OK) status = NL_ERR_FORMAT;
    backend->last_status = status;
    if (status != NL_ERR_EMPTY) ++backend->stats.driver_errors;
    if (status == NL_ERR_FORMAT || status == NL_ERR_SIZE || status == NL_ERR_ARGUMENT)
        ++backend->stats.malformed;
    if (!backend->pulling) ++backend->stats.tx_retries;
    if (receipt != 0u) {
        backend->receipt = receipt;
        backend->abort_pending = true;
        abort_receipt(backend);
    }
}

static void poll(nl_host *host, nl_plugin_id plugin, uint64_t now_us, void *context)
{
    nl_spi_backend *backend = context;
    nl_status status;
    bool ready = false;
    const nl_frame pull = {.command = NL_COMMAND_PULL};
    if (backend == NULL || backend->host != host || backend->plugin != plugin ||
        !backend->running || backend->calling) return;
    if (backend->have_clock && now_us < backend->now_us) {
        backend->last_status = NL_ERR_ARGUMENT;
        ++backend->stats.backward_clocks;
        return;
    }
    backend->have_clock = true;
    backend->now_us = now_us;
    if (backend->abort_pending) {
        abort_receipt(backend);
        return;
    }
    if (backend->inflight) {
        complete(backend, now_us);
        return;
    }
    if (backend->next_transaction == UINT64_MAX) {
        backend->last_status = NL_ERR_FULL;
        return;
    }
    /* A cached receipt settles before another device operation. Alternating
     * direction prevents application ticks refilling TX from starving READY. */
    if (backend->rx_pending) return;
    if (!backend->tx_pending || backend->prefer_rx || backend->tx_uncertain) {
        backend->calling = true;
        status = backend->driver.ready(backend->driver.context, &ready);
        backend->calling = false;
        backend->last_status = status;
        if (status != NL_OK) {
            ++backend->stats.driver_errors;
            return;
        }
    }
    if (ready) {
        status = nl_frame_encode(&pull, backend->request, sizeof(backend->request),
                                 &backend->request_size);
        if (status != NL_OK) {
            backend->last_status = status;
            return;
        }
        backend->pulling = true;
    } else {
        if (!backend->tx_pending || backend->tx_uncertain) return;
        memcpy(backend->request, backend->tx, backend->tx_size);
        backend->request_size = backend->tx_size;
        backend->pulling = false;
    }
    backend->transaction = backend->next_transaction++;
    backend->calling = true;
    status = backend->driver.begin(backend->driver.context, backend->request,
                                  backend->request_size, backend->transaction, now_us);
    backend->calling = false;
    backend->last_status = status;
    if (status == NL_OK) {
        backend->inflight = true;
        backend->prefer_rx = !backend->pulling;
    }
    else {
        ++backend->stats.driver_errors;
        if (!backend->pulling) ++backend->stats.tx_retries;
    }
}

nl_status nl_spi_backend_init(nl_spi_backend *backend, const nl_spi_driver *driver)
{
    nl_spi_backend initialized;
    if (backend == NULL || driver == NULL || driver->stop == NULL ||
        driver->ready == NULL || driver->begin == NULL || driver->finish == NULL ||
        driver->settle == NULL) return NL_ERR_ARGUMENT;
    memset(&initialized, 0, sizeof(initialized));
    initialized.driver = *driver;
    initialized.plugin = NL_PLUGIN_ID_NONE;
    initialized.next_transaction = 1;
    *backend = initialized;
    return NL_OK;
}

nl_module nl_spi_backend_module(nl_spi_backend *backend)
{
    const nl_module module = {
        .name = "spi-backend", .version = "1", .kind = NL_MODULE_SERVICE,
        .service = backend,
        .hooks = {.start = start, .stop = stop, .context = backend,
                  .poll = poll, .can_stop = can_stop}
    };
    return module;
}

nl_status nl_spi_backend_link_config(nl_spi_backend *backend, uint16_t poll_budget,
                                     nl_radio_link_config *config)
{
    const nl_radio_link_config configured = {
        .exchange = backend_exchange, .commit = backend_commit,
        .can_stop = backend_idle, .context = backend, .poll_budget = poll_budget
    };
    if (backend == NULL || config == NULL || poll_budget == 0u) return NL_ERR_ARGUMENT;
    *config = configured;
    return NL_OK;
}

nl_module nl_spi_backend_link_module(nl_radio_link *link)
{
    static const char *const dependencies[] = {"spi-backend"};
    nl_module module = nl_radio_link_module(link);
    module.requires = dependencies;
    module.require_count = 1;
    return module;
}

nl_status nl_spi_backend_resolve_tx(nl_spi_backend *backend, bool retry)
{
    if (backend == NULL) return NL_ERR_ARGUMENT;
    if (!backend->running) return NL_ERR_NOT_FOUND;
    if (backend->calling || backend->inflight || backend->host->polling ||
        backend->host->dispatching || backend->host->sending ||
        backend->host->logging || backend->host->lifecycle_busy) return NL_ERR_BUSY;
    if (!backend->tx_uncertain) return NL_ERR_EMPTY;
    backend->tx_uncertain = false;
    if (!retry) {
        backend->tx_pending = false;
        ++backend->stats.tx_discarded;
    }
    return NL_OK;
}
