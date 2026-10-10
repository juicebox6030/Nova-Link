#include <string.h>
#include "nova_link/plugin_conformance.h"

typedef struct {
    nl_plugin actual;
    unsigned starts;
    unsigned stops;
    nl_status actual_status;
} startup_probe;

static nl_status fail_after_start(nl_host *host, nl_plugin_id id, void *context)
{
    startup_probe *probe = context;
    ++probe->starts;
    probe->actual_status = probe->actual.start != NULL ?
        probe->actual.start(host, id, probe->actual.context) : NL_OK;
    return probe->actual_status == NL_OK ? NL_ERR_FORMAT : probe->actual_status;
}

static void stop_actual(nl_host *host, nl_plugin_id id, void *context)
{
    startup_probe *probe = context;
    ++probe->stops;
    if (probe->actual.stop != NULL)
        probe->actual.stop(host, id, probe->actual.context);
}

static nl_status fail_dependent(nl_host *host, nl_plugin_id id, void *context)
{
    (void)host;
    (void)id;
    (void)context;
    return NL_ERR_FORMAT;
}

static bool empty_host(const nl_host *host)
{
    size_t i;
    for (i = 0; i < NL_PLUGIN_MAX; ++i)
        if (host->plugins[i].state != NL_PLUGIN_FREE) return false;
    for (i = 1; i < NL_ZONE_COUNT; ++i)
        if (host->zones.claims[i].readers != 0u ||
            host->zones.claims[i].owner != NL_PLUGIN_NONE) return false;
    return host->send == NULL && host->log == NULL &&
        host->transport_owner == NL_PLUGIN_ID_NONE &&
        host->logger_owner == NL_PLUGIN_ID_NONE;
}

static bool fixture_valid(const nl_conformance_fixture *fixture)
{
    size_t i;
    if (fixture->count == 0u || fixture->count >= NL_PLUGIN_MAX ||
        fixture->subject >= fixture->count || fixture->recovery_polls > 1024u ||
        fixture->restart_polls > 1024u ||
        !empty_host(&fixture->host)) return false;
    for (i = 0; i < fixture->count; ++i)
        if (fixture->modules[i] == NULL || fixture->modules[i]->name == NULL ||
            fixture->modules[i]->name[0] == '\0' ||
            fixture->modules[i]->version == NULL ||
            fixture->modules[i]->version[0] == '\0' ||
            fixture->instances[i].active) return false;
    return true;
}

static bool unbound(const nl_conformance_fixture *fixture)
{
    size_t i;
    if (!empty_host(&fixture->host)) return false;
    for (i = 0; i < fixture->count; ++i)
        if (fixture->instances[i].active || fixture->instances[i].owner != NULL)
            return false;
    return true;
}

/* An application may use the obvious probe name, so reserve a name by extending
 * it with underscores. At most NL_PLUGIN_MAX-1 names exist in a fixture. */
static void unused_name(const nl_conformance_fixture *fixture, char *name)
{
    size_t i, length = 0;
    bool exists;
    strcpy(name, "conformance-probe");
    length = strlen(name);
    for (i = 0; i < NL_PLUGIN_MAX; ++i) {
        size_t j;
        exists = false;
        for (j = 0; j < fixture->count; ++j)
            if (strcmp(fixture->modules[j]->name, name) == 0) exists = true;
        if (!exists) return;
        name[length++] = '_';
        name[length] = '\0';
    }
}

static bool metrics_forward(nl_conformance_metrics before,
                            nl_conformance_metrics after, unsigned bound)
{
    return after.attempts >= before.attempts && after.accepted >= before.accepted &&
        after.accepted <= after.attempts &&
        after.attempts - before.attempts <= bound;
}

static const char *run_case(const nl_conformance_adapter *adapter,
                            nl_conformance_case test_case,
                            nl_conformance_result *result)
{
    nl_conformance_fixture fixture;
    nl_module_instance probe_instance = {0};
    nl_module proxy_module, probe_module;
    startup_probe startup = {0};
    const nl_module *subject;
    const char *dependency[1];
    const char *requirements[NL_PLUGIN_MAX];
    char probe_name[sizeof("conformance-probe") + NL_PLUGIN_MAX];
    const char *failure = NULL;
    nl_status status;
    size_t i;
    nl_conformance_metrics baseline = {0}, previous = {0}, current = {0};
    unsigned polls;
    uint64_t expected;
    uint64_t restart_start;
    bool prepared = false;
#define CHECK(condition, detail) do { if (!(condition)) { failure = detail; goto done; } } while (0)
#define INSPECT(checkpoint, detail) CHECK(adapter->inspect(adapter->context, &fixture, checkpoint) == NL_OK, detail)
    memset(&fixture, 0, sizeof(fixture));
    CHECK(nl_host_init_plugins(&fixture.host, 1u, 1000000u) == NL_OK,
          "host initialization failed");
    prepared = true;
    CHECK(adapter->prepare(adapter->context, &fixture, test_case) == NL_OK,
          "adapter prepare failed");
    CHECK(fixture_valid(&fixture), "prepare must supply a fresh bounded manifest");
    subject = fixture.modules[fixture.subject];

    if (test_case == NL_CONFORMANCE_START_ROLLBACK) {
        startup.actual = subject->hooks;
        proxy_module = *subject;
        proxy_module.hooks = (nl_plugin){.start = fail_after_start,
            .stop = stop_actual, .context = &startup};
        fixture.modules[fixture.subject] = &proxy_module;
        status = nl_modules_start(&fixture.host, fixture.modules,
                                  fixture.instances, fixture.count);
        CHECK(status == NL_ERR_FORMAT && startup.actual_status == NL_OK &&
              startup.starts == 1u && startup.stops == 1u,
              "actual startup must succeed then receive exactly one rollback stop");
        CHECK(unbound(&fixture), "startup rollback left registry/owner bindings");
        INSPECT(NL_CONFORMANCE_ROLLED_BACK, "actual startup rollback leaked resources");
        goto done;
    }

    if (test_case == NL_CONFORMANCE_MANIFEST_ROLLBACK) {
        /* Fail only after every supplied provider/application started. */
        for (i = 0; i < fixture.count; ++i)
            requirements[i] = fixture.modules[i]->name;
        unused_name(&fixture, probe_name);
        probe_module = (nl_module){.name = probe_name, .version = "1",
            .kind = NL_MODULE_SERVICE, .requires = requirements,
            .require_count = fixture.count,
            .hooks = {.start = fail_dependent}};
        fixture.modules[fixture.count] = &probe_module;
        ++fixture.count;
        status = nl_modules_start(&fixture.host, fixture.modules,
                                  fixture.instances, fixture.count);
        CHECK(status == NL_ERR_FORMAT, "dependent failure must abort whole manifest");
        CHECK(unbound(&fixture), "manifest rollback left registry/owner bindings");
        INSPECT(NL_CONFORMANCE_ROLLED_BACK, "manifest rollback leaked actual resources");
        goto done;
    }

    CHECK(nl_modules_start(&fixture.host, fixture.modules,
                           fixture.instances, fixture.count) == NL_OK,
          "actual manifest startup failed");
    for (i = 0; i < fixture.count; ++i)
        CHECK(fixture.instances[i].active && fixture.instances[i].owner == &fixture.host &&
              nl_module_find(&fixture.host, fixture.modules[i]->name) == &fixture.instances[i],
              "active module must retain exact host/instance binding");
    INSPECT(NL_CONFORMANCE_ACTIVE, "actual active state invalid");

    if (test_case == NL_CONFORMANCE_LIFECYCLE) {
        nl_module_instance *instance = &fixture.instances[fixture.subject];
        nl_host other_host;
        nl_plugin_id original_id = instance->id;
        CHECK(nl_module_register(&fixture.host, subject, instance) == NL_ERR_BUSY,
              "active instance was registered twice");
        CHECK(nl_host_init_plugins(&other_host, 2u, 1000000u) == NL_OK &&
              nl_module_register(&other_host, subject, instance) == NL_ERR_BUSY &&
              empty_host(&other_host) && instance->owner == &fixture.host &&
              instance->id == original_id,
              "cross-host active-instance rejection changed original ownership");
        unused_name(&fixture, probe_name);
        if (subject->hooks.context != NULL && !subject->shared_context) {
            proxy_module = *subject;
            proxy_module.name = probe_name;
            CHECK(nl_module_register(&fixture.host, &proxy_module,
                                      &probe_instance) == NL_ERR_CONFLICT &&
                  !probe_instance.active && probe_instance.owner == NULL,
                  "mutable callback context alias was accepted or rebound");
            ++result->alias_checks;
        } else ++result->alias_skipped;
        INSPECT(NL_CONFORMANCE_ACTIVE, "rejected registration mutated actual context");
        CHECK(nl_host_poll(&fixture.host, 100u) == NL_OK, "active poll failed");
    } else if (test_case == NL_CONFORMANCE_DEPENDENCY_STOP) {
        nl_module_instance *instance = &fixture.instances[fixture.subject];
        unused_name(&fixture, probe_name);
        dependency[0] = subject->name;
        probe_module = (nl_module){.name = probe_name, .version = "1",
            .kind = NL_MODULE_SERVICE, .requires = dependency, .require_count = 1};
        CHECK(nl_module_register(&fixture.host, &probe_module, &probe_instance) == NL_OK,
              "dependent probe startup failed");
        CHECK(nl_module_unregister(instance) == NL_ERR_BUSY &&
              nl_host_unregister(&fixture.host, instance->id) == NL_ERR_BUSY &&
              instance->active && instance->owner == &fixture.host,
              "provider removal ignored live dependency");
        CHECK(nl_modules_stop(fixture.instances, fixture.count) == NL_ERR_BUSY,
              "manifest shutdown ignored external dependent");
        for (i = 0; i < fixture.count; ++i)
            CHECK(fixture.instances[i].active, "external dependent partially stopped manifest");
        INSPECT(NL_CONFORMANCE_ACTIVE, "BUSY dependency stop mutated actual state");
        CHECK(nl_module_unregister(&probe_instance) == NL_OK,
              "dependent probe shutdown failed");
    } else if (test_case == NL_CONFORMANCE_PENDING_STOP) {
        nl_module_instance *instance = &fixture.instances[fixture.subject];
        CHECK(adapter->control(adapter->context, &fixture, NL_CONFORMANCE_PENDING_ON) == NL_OK,
              "adapter did not acquire pending actual ownership");
        CHECK(nl_module_unregister(instance) == NL_ERR_BUSY &&
              instance->active && instance->owner == &fixture.host,
              "pending subject ownership failed to veto stop");
        INSPECT(NL_CONFORMANCE_BLOCKED, "BUSY stop lost pending actual ownership");
        CHECK(adapter->control(adapter->context, &fixture, NL_CONFORMANCE_PENDING_OFF) == NL_OK,
              "adapter did not drain pending ownership");
    } else if (test_case == NL_CONFORMANCE_BACKPRESSURE) {
        CHECK(fixture.max_attempts_per_poll != 0u,
              "backpressure requires a nonzero attempt budget");
        CHECK(adapter->control(adapter->context, &fixture, NL_CONFORMANCE_PRESSURE_ON) == NL_OK &&
              adapter->control(adapter->context, &fixture, NL_CONFORMANCE_SEED_WORK) == NL_OK,
              "adapter could not arm actual rejected workload");
        CHECK(adapter->measure(adapter->context, &fixture, &baseline) == NL_OK &&
              baseline.accepted <= baseline.attempts, "initial actual work metrics invalid");
        previous = baseline;
        for (i = 0; i < 3u; ++i) {
            CHECK(nl_host_poll(&fixture.host, (uint64_t)(i + 1u) * 100u) == NL_OK &&
                  adapter->measure(adapter->context, &fixture, &current) == NL_OK,
                  "blocked workload poll/measurement failed");
            CHECK(metrics_forward(previous, current, fixture.max_attempts_per_poll) &&
                  current.accepted == baseline.accepted,
                  "rejection accepted work, reversed metrics or exceeded poll budget");
            INSPECT(NL_CONFORMANCE_BLOCKED, "rejection changed retained bytes/cursor/ownership");
            previous = current;
        }
        CHECK(current.attempts > baseline.attempts, "backpressure exercised no actual attempts");
        CHECK(adapter->control(adapter->context, &fixture, NL_CONFORMANCE_PRESSURE_OFF) == NL_OK,
              "adapter could not release backpressure");
        polls = fixture.recovery_polls == 0u ? 4u : fixture.recovery_polls;
        for (i = 0; i < polls; ++i) {
            CHECK(nl_host_poll(&fixture.host, 400u + (uint64_t)i * 100u) == NL_OK &&
                  adapter->measure(adapter->context, &fixture, &current) == NL_OK,
                  "recovery workload poll/measurement failed");
            CHECK(metrics_forward(previous, current, fixture.max_attempts_per_poll),
                  "recovery reversed metrics or exceeded poll budget");
            previous = current;
        }
        expected = fixture.expected_accepts == 0u ? 1u : fixture.expected_accepts;
        CHECK(current.accepted - baseline.accepted == expected,
              "recovery accepted wrong number of workload fragments");
        INSPECT(NL_CONFORMANCE_RECOVERED, "recovery changed or duplicated retained work");
    } else if (test_case == NL_CONFORMANCE_RESTART) {
        if (adapter->seed_restart_work != NULL)
            CHECK(adapter->seed_restart_work(adapter->context, &fixture) == NL_OK,
                  "initial live restart workload submission failed");
        polls = fixture.restart_polls == 0u ? 1u : fixture.restart_polls;
        for (i = 0; i < polls; ++i)
            CHECK(nl_host_poll(&fixture.host, (uint64_t)(i + 1u) * 100u) == NL_OK,
                  "pre-restart poll failed");
        restart_start = (uint64_t)(polls + 1u) * 100u;
        CHECK(nl_modules_stop(fixture.instances, fixture.count) == NL_OK && unbound(&fixture),
              "pre-restart stop left live ownership");
        INSPECT(NL_CONFORMANCE_STOPPED, "pre-restart cleanup leaked actual resources");
        memset(fixture.instances, 0, sizeof(fixture.instances));
        CHECK(nl_host_init_plugins(&fixture.host, 1u, 1000000u) == NL_OK &&
              adapter->reinitialize(adapter->context, &fixture) == NL_OK &&
              fixture_valid(&fixture), "explicit context/host reinitialization failed");
        CHECK(nl_modules_start(&fixture.host, fixture.modules,
                               fixture.instances, fixture.count) == NL_OK,
              "reinitialized actual manifest did not restart");
        if (adapter->seed_restart_work != NULL)
            CHECK(adapter->seed_restart_work(adapter->context, &fixture) == NL_OK,
                  "restarted live workload submission failed");
        polls = fixture.restart_polls == 0u ? 1u : fixture.restart_polls;
        for (i = 0; i < polls; ++i)
            CHECK(nl_host_poll(&fixture.host, restart_start + (uint64_t)i * 100u) == NL_OK,
                  "restarted poll failed");
        INSPECT(NL_CONFORMANCE_RESTARTED, "restart retained stale ownership/session/state or failed fresh work");
    }

    CHECK(nl_modules_stop(fixture.instances, fixture.count) == NL_OK && unbound(&fixture),
          "ordinary manifest stop left registry/owner bindings");
    INSPECT(NL_CONFORMANCE_STOPPED, "ordinary actual cleanup leaked resources");
done:
    /* Probe metadata is still alive while adapters clean up failed checks. */
    if (probe_instance.active) (void)nl_module_unregister(&probe_instance);
    if (prepared) adapter->finish(adapter->context, &fixture);
    if (failure == NULL && !unbound(&fixture))
        failure = "adapter finish left active registrations/ownership";
#undef INSPECT
#undef CHECK
    return failure;
}

const char *nl_conformance_case_name(nl_conformance_case test_case)
{
    static const char *const names[] = {"lifecycle-owner-alias", "startup-rollback",
        "manifest-rollback", "dependency-stop", "pending-stop", "backpressure", "restart"};
    return test_case >= NL_CONFORMANCE_LIFECYCLE && test_case < NL_CONFORMANCE_CASE_COUNT ?
        names[test_case] : "invalid";
}

nl_status nl_plugin_conformance_run(const nl_conformance_adapter *adapter,
                                    nl_conformance_result *result,
                                    nl_conformance_report_fn report,
                                    void *report_context)
{
    nl_conformance_case test_case;
    const char *failure;
    unsigned capability;
    if (result == NULL) return NL_ERR_ARGUMENT;
    memset(result, 0, sizeof(*result));
    result->first_failed_case = NL_CONFORMANCE_CASE_COUNT;
    if (adapter == NULL || adapter->name == NULL || adapter->name[0] == '\0' ||
        adapter->prepare == NULL || adapter->inspect == NULL || adapter->finish == NULL ||
        (adapter->capabilities & ~(unsigned)(NL_CONFORMANCE_CAN_PENDING |
         NL_CONFORMANCE_CAN_BACKPRESSURE | NL_CONFORMANCE_CAN_RESTART)) != 0u ||
        ((adapter->capabilities & (NL_CONFORMANCE_CAN_PENDING | NL_CONFORMANCE_CAN_BACKPRESSURE)) != 0u &&
         adapter->control == NULL) ||
        ((adapter->capabilities & NL_CONFORMANCE_CAN_BACKPRESSURE) != 0u && adapter->measure == NULL) ||
        ((adapter->capabilities & NL_CONFORMANCE_CAN_RESTART) != 0u && adapter->reinitialize == NULL))
        return NL_ERR_ARGUMENT;
    for (test_case = NL_CONFORMANCE_LIFECYCLE;
         test_case < NL_CONFORMANCE_CASE_COUNT; ++test_case) {
        capability = test_case == NL_CONFORMANCE_PENDING_STOP ? NL_CONFORMANCE_CAN_PENDING :
            test_case == NL_CONFORMANCE_BACKPRESSURE ? NL_CONFORMANCE_CAN_BACKPRESSURE :
            test_case == NL_CONFORMANCE_RESTART ? NL_CONFORMANCE_CAN_RESTART : 0u;
        if (capability != 0u && (adapter->capabilities & capability) == 0u) {
            ++result->skipped;
            if (report != NULL) report(report_context, adapter->name, test_case,
                NL_ERR_UNSUPPORTED, "adapter does not advertise this capability");
            continue;
        }
        failure = run_case(adapter, test_case, result);
        if (failure == NULL) ++result->passed;
        else {
            if (result->failed == 0u) {
                result->first_failed_case = test_case;
                result->first_failure = failure;
            }
            ++result->failed;
        }
        if (report != NULL) report(report_context, adapter->name, test_case,
            failure == NULL ? NL_OK : NL_ERR_CONFLICT,
            failure == NULL ? "contract passed" : failure);
    }
    return result->failed == 0u ? NL_OK : NL_ERR_CONFLICT;
}
