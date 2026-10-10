#include "test.h"
#include "nova_link/plugin_conformance.h"

/* Trusted compiled examples with actual broken behavior. The adapter observes
 * their private state; it does not fabricate a failed conformance result. */
typedef enum {
    GOOD,
    LEAK_STOP,
    LEAK_START_ROLLBACK,
    LEAK_MANIFEST_ROLLBACK,
    IGNORE_PENDING,
    MUTATE_REJECTED_BYTES,
    ADVANCE_REJECTED_CURSOR,
    DROP_REJECTED_WORK,
    EXCEED_BUDGET,
    ACCEPT_UNDER_PRESSURE,
    DUPLICATE_RECOVERY,
    STALE_RESTART
} defect;

typedef struct {
    nl_host *bound_host;
    nl_plugin_id bound_id;
    bool owned_work;
    bool pressure;
    uint64_t attempts, accepted;
    uint8_t delivered[8][8];
} test_backend;

typedef struct {
    test_backend backend;
    nl_module module;
    bool running, queued;
    uint8_t retained[8];
    unsigned cursor, session;
} tiny_plugin;

typedef struct {
    defect defect;
    nl_conformance_case test_case;
    tiny_plugin plugin;
    unsigned prepares, finishes, triggered;
    bool cleanup_complete;
    bool malformed_name;
} fixture_context;

static const uint8_t workload[8] = {0, 0xff, 0x81, 0x13, 0x42, 0x09, 0xa5, 0x7e};

static bool defective(const fixture_context *state, defect selected)
{
    if (state->defect != selected) return false;
    if (selected == LEAK_STOP) return state->test_case == NL_CONFORMANCE_LIFECYCLE;
    if (selected == LEAK_START_ROLLBACK)
        return state->test_case == NL_CONFORMANCE_START_ROLLBACK;
    if (selected == LEAK_MANIFEST_ROLLBACK)
        return state->test_case == NL_CONFORMANCE_MANIFEST_ROLLBACK;
    if (selected == IGNORE_PENDING) return state->test_case == NL_CONFORMANCE_PENDING_STOP;
    if (selected == STALE_RESTART) return state->test_case == NL_CONFORMANCE_RESTART;
    return state->test_case == NL_CONFORMANCE_BACKPRESSURE;
}

static nl_status tiny_start(nl_host *host, nl_plugin_id id, void *context)
{
    fixture_context *state = context;
    tiny_plugin *plugin = &state->plugin;
    if (plugin->running || plugin->backend.bound_host != NULL) return NL_ERR_BUSY;
    plugin->running = true;
    plugin->backend.bound_host = host;
    plugin->backend.bound_id = id;
    return NL_OK;
}

static void tiny_stop(nl_host *host, nl_plugin_id id, void *context)
{
    fixture_context *state = context;
    tiny_plugin *plugin = &state->plugin;
    CHECK(plugin->backend.bound_host == host && plugin->backend.bound_id == id);
    plugin->running = false;
    plugin->queued = false;
    plugin->backend.owned_work = false;
    if (defective(state, LEAK_STOP) || defective(state, LEAK_START_ROLLBACK) ||
        defective(state, LEAK_MANIFEST_ROLLBACK)) {
        ++state->triggered;
        return; /* An actual external binding survives the host's cleanup. */
    }
    plugin->backend.bound_host = NULL;
    plugin->backend.bound_id = NL_PLUGIN_ID_NONE;
}

static nl_status tiny_can_stop(nl_host *host, nl_plugin_id id, void *context)
{
    fixture_context *state = context;
    CHECK(state->plugin.backend.bound_host == host &&
          state->plugin.backend.bound_id == id);
    if (state->plugin.backend.owned_work && defective(state, IGNORE_PENDING)) {
        ++state->triggered;
        return NL_OK; /* Wrongly approves stop with backend ownership pending. */
    }
    return state->plugin.backend.owned_work ? NL_ERR_BUSY : NL_OK;
}

static nl_status backend_submit(fixture_context *state, const uint8_t *bytes)
{
    test_backend *backend = &state->plugin.backend;
    CHECK(backend->bound_host != NULL && state->plugin.running);
    ++backend->attempts;
    if (backend->pressure && !defective(state, ACCEPT_UNDER_PRESSURE)) return NL_ERR_BUSY;
    if (backend->pressure) ++state->triggered;
    CHECK(backend->accepted < 8u);
    memcpy(backend->delivered[(size_t)backend->accepted], bytes, sizeof(workload));
    ++backend->accepted;
    return NL_OK;
}

static void tiny_poll(nl_host *host, nl_plugin_id id, uint64_t now_us, void *context)
{
    fixture_context *state = context;
    tiny_plugin *plugin = &state->plugin;
    unsigned attempt, budget = 1u;
    (void)now_us;
    CHECK(plugin->running && plugin->backend.bound_host == host &&
          plugin->backend.bound_id == id);
    if (defective(state, EXCEED_BUDGET) && plugin->backend.pressure) {
        budget = 3u;
        ++state->triggered;
    }
    for (attempt = 0; attempt < budget && plugin->queued; ++attempt) {
        if (backend_submit(state, plugin->retained) == NL_OK) {
            ++plugin->cursor;
            if (defective(state, DUPLICATE_RECOVERY)) ++state->triggered;
            else plugin->queued = false;
        } else if (defective(state, MUTATE_REJECTED_BYTES)) {
            plugin->retained[3] ^= 1u;
            ++state->triggered;
        } else if (defective(state, ADVANCE_REJECTED_CURSOR)) {
            ++plugin->cursor;
            ++state->triggered;
        } else if (defective(state, DROP_REJECTED_WORK)) {
            plugin->queued = false;
            ++state->triggered;
        }
    }
}

static void make_module(fixture_context *state, nl_conformance_fixture *fixture)
{
    tiny_plugin *plugin = &state->plugin;
    plugin->module = (nl_module){.name = "negative-tiny", .version = "1",
        .kind = NL_MODULE_SERVICE,
        .hooks = {.start = tiny_start, .stop = tiny_stop, .context = state,
                  .poll = tiny_poll, .can_stop = tiny_can_stop}};
    fixture->modules[0] = &plugin->module;
    fixture->count = 1u;
    fixture->subject = 0u;
    fixture->max_attempts_per_poll = 2u;
    fixture->recovery_polls = 4u;
    fixture->expected_accepts = 1u;
}

static nl_status prepare(void *context, nl_conformance_fixture *fixture,
                         nl_conformance_case test_case)
{
    fixture_context *state = context;
    CHECK(state->cleanup_complete);
    memset(&state->plugin, 0, sizeof(state->plugin));
    state->plugin.backend.bound_id = NL_PLUGIN_ID_NONE;
    state->plugin.session = 1u;
    state->test_case = test_case;
    state->cleanup_complete = false;
    ++state->prepares;
    make_module(state, fixture);
    if (state->malformed_name) state->plugin.module.name = NULL;
    return NL_OK;
}

static bool bound_correctly(const tiny_plugin *plugin,
                           const nl_conformance_fixture *fixture)
{
    return plugin->running && plugin->backend.bound_host == &fixture->host &&
        plugin->backend.bound_id == fixture->instances[fixture->subject].id;
}

static nl_status inspect(void *context, const nl_conformance_fixture *fixture,
                         nl_conformance_checkpoint checkpoint)
{
    const fixture_context *state = context;
    const tiny_plugin *plugin = &state->plugin;
    switch (checkpoint) {
    case NL_CONFORMANCE_ACTIVE:
        return bound_correctly(plugin, fixture) ? NL_OK : NL_ERR_CONFLICT;
    case NL_CONFORMANCE_STOPPED:
    case NL_CONFORMANCE_ROLLED_BACK:
        return !plugin->running && !plugin->queued && !plugin->backend.owned_work &&
            plugin->backend.bound_host == NULL &&
            plugin->backend.bound_id == NL_PLUGIN_ID_NONE ? NL_OK : NL_ERR_CONFLICT;
    case NL_CONFORMANCE_BLOCKED:
        if (!bound_correctly(plugin, fixture)) return NL_ERR_CONFLICT;
        if (state->test_case == NL_CONFORMANCE_PENDING_STOP)
            return plugin->backend.owned_work ? NL_OK : NL_ERR_CONFLICT;
        return plugin->queued && plugin->cursor == 0u &&
            memcmp(plugin->retained, workload, sizeof(workload)) == 0 &&
            plugin->backend.accepted == 0u ? NL_OK : NL_ERR_CONFLICT;
    case NL_CONFORMANCE_RECOVERED:
        return bound_correctly(plugin, fixture) && !plugin->queued && plugin->cursor == 1u &&
            plugin->backend.accepted == 1u &&
            memcmp(plugin->backend.delivered[0], workload, sizeof(workload)) == 0 ?
            NL_OK : NL_ERR_CONFLICT;
    case NL_CONFORMANCE_RESTARTED:
        return bound_correctly(plugin, fixture) && plugin->session == 2u &&
            !plugin->queued && !plugin->backend.owned_work && !plugin->backend.pressure &&
            plugin->cursor == 1u && plugin->backend.attempts == 1u &&
            plugin->backend.accepted == 1u &&
            memcmp(plugin->backend.delivered[0], workload, sizeof(workload)) == 0 ?
            NL_OK : NL_ERR_CONFLICT;
    }
    return NL_ERR_ARGUMENT;
}

static nl_status seed_work(tiny_plugin *plugin)
{
    if (!plugin->running || plugin->queued) return NL_ERR_BUSY;
    memcpy(plugin->retained, workload, sizeof(workload));
    plugin->queued = true;
    plugin->cursor = 0u;
    return NL_OK;
}

static nl_status control(void *context, nl_conformance_fixture *fixture,
                         nl_conformance_action action)
{
    fixture_context *state = context;
    tiny_plugin *plugin = &state->plugin;
    if (!bound_correctly(plugin, fixture)) return NL_ERR_CONFLICT;
    switch (action) {
    case NL_CONFORMANCE_PENDING_ON: plugin->backend.owned_work = true; break;
    case NL_CONFORMANCE_PENDING_OFF: plugin->backend.owned_work = false; break;
    case NL_CONFORMANCE_PRESSURE_ON: plugin->backend.pressure = true; break;
    case NL_CONFORMANCE_PRESSURE_OFF: plugin->backend.pressure = false; break;
    case NL_CONFORMANCE_SEED_WORK: return seed_work(plugin);
    }
    return NL_OK;
}

static nl_status measure(void *context, const nl_conformance_fixture *fixture,
                         nl_conformance_metrics *metrics)
{
    const fixture_context *state = context;
    if (!bound_correctly(&state->plugin, fixture)) return NL_ERR_CONFLICT;
    metrics->attempts = state->plugin.backend.attempts;
    metrics->accepted = state->plugin.backend.accepted;
    return NL_OK;
}

static nl_status seed_restart_work(void *context, nl_conformance_fixture *fixture)
{
    fixture_context *state = context;
    if (!bound_correctly(&state->plugin, fixture)) return NL_ERR_CONFLICT;
    return seed_work(&state->plugin);
}

static nl_status reinitialize(void *context, nl_conformance_fixture *fixture)
{
    fixture_context *state = context;
    bool stale = defective(state, STALE_RESTART);
    CHECK(!state->plugin.running && state->plugin.backend.bound_host == NULL);
    memset(&state->plugin, 0, sizeof(state->plugin));
    state->plugin.backend.bound_id = NL_PLUGIN_ID_NONE;
    state->plugin.session = stale ? 1u : 2u;
    if (stale) ++state->triggered;
    make_module(state, fixture);
    return NL_OK;
}

static void finish(void *context, nl_conformance_fixture *fixture)
{
    fixture_context *state = context;
    defect saved = state->defect;
    size_t i;
    /* Cancel backend work, then unregister while all descriptors remain live.
     * Failed-stop leaks are externally released after unregister, never hidden
     * by overwriting a still-live plugin context. */
    state->plugin.backend.owned_work = false;
    state->defect = GOOD;
    STATUS(nl_modules_stop(fixture->instances, fixture->count), NL_OK);
    state->defect = saved;
    for (i = 0; i < fixture->count; ++i)
        CHECK(!fixture->instances[i].active && fixture->instances[i].owner == NULL);
    state->plugin.backend.bound_host = NULL;
    state->plugin.backend.bound_id = NL_PLUGIN_ID_NONE;
    CHECK(!state->plugin.running && !state->plugin.queued);
    ++state->finishes;
    state->cleanup_complete = true;
}

static nl_conformance_adapter adapter_for(fixture_context *state)
{
    return (nl_conformance_adapter){.name = "compiled-negative-fixture",
        .capabilities = NL_CONFORMANCE_CAN_PENDING | NL_CONFORMANCE_CAN_BACKPRESSURE |
                        NL_CONFORMANCE_CAN_RESTART,
        .context = state, .prepare = prepare, .inspect = inspect, .control = control,
        .measure = measure, .reinitialize = reinitialize, .finish = finish,
        .seed_restart_work = seed_restart_work};
}

static void expect_defect(defect selected, nl_conformance_case expected_case,
                          const char *expected_detail)
{
    fixture_context state = {.defect = selected, .cleanup_complete = true};
    nl_conformance_adapter adapter = adapter_for(&state);
    nl_conformance_result result;
    STATUS(nl_plugin_conformance_run(&adapter, &result, NULL, NULL),
           selected == GOOD ? NL_OK : NL_ERR_CONFLICT);
    CHECK(result.passed + result.failed == NL_CONFORMANCE_CASE_COUNT && result.skipped == 0u);
    CHECK(result.first_failed_case == expected_case);
    CHECK(result.alias_checks == 1u && result.alias_skipped == 0u);
    CHECK(state.prepares == NL_CONFORMANCE_CASE_COUNT && state.finishes == state.prepares &&
          state.cleanup_complete);
    if (selected == GOOD) {
        CHECK(result.failed == 0u && result.first_failure == NULL && state.triggered == 0u);
    } else {
        CHECK(result.failed == 1u && state.triggered > 0u);
        if (result.first_failure == NULL || strcmp(result.first_failure, expected_detail) != 0)
            fprintf(stderr, "defect %u reported: %s\n", (unsigned)selected,
                    result.first_failure == NULL ? "(none)" : result.first_failure);
        CHECK(result.first_failure != NULL && strcmp(result.first_failure, expected_detail) == 0);
    }
}

static void invalid_adapters(void)
{
    fixture_context state = {.cleanup_complete = true};
    nl_conformance_adapter valid = adapter_for(&state), invalid;
    nl_conformance_result result;
    STATUS(nl_plugin_conformance_run(NULL, &result, NULL, NULL), NL_ERR_ARGUMENT);
    STATUS(nl_plugin_conformance_run(&valid, NULL, NULL, NULL), NL_ERR_ARGUMENT);
#define INVALID(field, value) do { invalid = valid; invalid.field = value; \
    STATUS(nl_plugin_conformance_run(&invalid, &result, NULL, NULL), NL_ERR_ARGUMENT); \
    CHECK(result.passed == 0u && result.failed == 0u && result.skipped == 0u); } while (0)
    INVALID(name, NULL);
    INVALID(name, "");
    INVALID(prepare, NULL);
    INVALID(inspect, NULL);
    INVALID(finish, NULL);
    INVALID(control, NULL);
    INVALID(measure, NULL);
    INVALID(reinitialize, NULL);
    INVALID(capabilities, 1u << 15);
#undef INVALID
    CHECK(state.prepares == 0u && state.finishes == 0u && state.cleanup_complete);
}

static void malformed_manifest(void)
{
    fixture_context state = {.cleanup_complete = true, .malformed_name = true};
    nl_conformance_adapter adapter = adapter_for(&state);
    nl_conformance_result result;
    adapter.capabilities = 0u;
    STATUS(nl_plugin_conformance_run(&adapter, &result, NULL, NULL), NL_ERR_CONFLICT);
    CHECK(result.failed == 4u && result.passed == 0u && result.skipped == 3u);
    CHECK(result.first_failed_case == NL_CONFORMANCE_LIFECYCLE &&
          strcmp(result.first_failure, "prepare must supply a fresh bounded manifest") == 0);
    CHECK(state.prepares == 4u && state.finishes == 4u && state.cleanup_complete);
}

int main(void)
{
    expect_defect(GOOD, NL_CONFORMANCE_CASE_COUNT, NULL);
    expect_defect(LEAK_STOP, NL_CONFORMANCE_LIFECYCLE,
                  "ordinary actual cleanup leaked resources");
    expect_defect(LEAK_START_ROLLBACK, NL_CONFORMANCE_START_ROLLBACK,
                  "actual startup rollback leaked resources");
    expect_defect(LEAK_MANIFEST_ROLLBACK, NL_CONFORMANCE_MANIFEST_ROLLBACK,
                  "manifest rollback leaked actual resources");
    expect_defect(IGNORE_PENDING, NL_CONFORMANCE_PENDING_STOP,
                  "pending subject ownership failed to veto stop");
    expect_defect(MUTATE_REJECTED_BYTES, NL_CONFORMANCE_BACKPRESSURE,
                  "rejection changed retained bytes/cursor/ownership");
    expect_defect(ADVANCE_REJECTED_CURSOR, NL_CONFORMANCE_BACKPRESSURE,
                  "rejection changed retained bytes/cursor/ownership");
    expect_defect(DROP_REJECTED_WORK, NL_CONFORMANCE_BACKPRESSURE,
                  "rejection changed retained bytes/cursor/ownership");
    expect_defect(EXCEED_BUDGET, NL_CONFORMANCE_BACKPRESSURE,
                  "rejection accepted work, reversed metrics or exceeded poll budget");
    expect_defect(ACCEPT_UNDER_PRESSURE, NL_CONFORMANCE_BACKPRESSURE,
                  "rejection accepted work, reversed metrics or exceeded poll budget");
    expect_defect(DUPLICATE_RECOVERY, NL_CONFORMANCE_BACKPRESSURE,
                  "recovery accepted wrong number of workload fragments");
    expect_defect(STALE_RESTART, NL_CONFORMANCE_RESTART,
                  "restart retained stale ownership/session/state or failed fresh work");
    invalid_adapters();
    malformed_manifest();
    return EXIT_SUCCESS;
}
