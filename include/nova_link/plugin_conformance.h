#ifndef NOVA_LINK_PLUGIN_CONFORMANCE_H
#define NOVA_LINK_PLUGIN_CONFORMANCE_H

#include "nova_link/module.h"

/** @file plugin_conformance.h Opt-in developer test support for compiled plugins.
 * Link NovaLink::nova_plugin_conformance in test executables, not nova_plugins.
 * The runner uses caller-owned storage and performs no allocation, I/O or clock
 * reads. It is deliberately separate from the portable runtime/board component.
 * Adapters use actual plugin factories and APIs, including their real backends.
 */
typedef enum {
    NL_CONFORMANCE_LIFECYCLE,
    NL_CONFORMANCE_START_ROLLBACK,
    NL_CONFORMANCE_MANIFEST_ROLLBACK,
    NL_CONFORMANCE_DEPENDENCY_STOP,
    NL_CONFORMANCE_PENDING_STOP,
    NL_CONFORMANCE_BACKPRESSURE,
    NL_CONFORMANCE_RESTART,
    NL_CONFORMANCE_CASE_COUNT
} nl_conformance_case;

enum {
    NL_CONFORMANCE_CAN_PENDING = 1u << 0,
    NL_CONFORMANCE_CAN_BACKPRESSURE = 1u << 1,
    NL_CONFORMANCE_CAN_RESTART = 1u << 2
};

typedef enum {
    NL_CONFORMANCE_ACTIVE,
    NL_CONFORMANCE_STOPPED,
    NL_CONFORMANCE_ROLLED_BACK,
    NL_CONFORMANCE_BLOCKED,
    NL_CONFORMANCE_RECOVERED,
    NL_CONFORMANCE_RESTARTED
} nl_conformance_checkpoint;

typedef enum {
    NL_CONFORMANCE_PENDING_ON,
    NL_CONFORMANCE_PENDING_OFF,
    NL_CONFORMANCE_PRESSURE_ON,
    NL_CONFORMANCE_PRESSURE_OFF,
    NL_CONFORMANCE_SEED_WORK
} nl_conformance_action;

/** Counters for actual subject work since prepare/reinitialize. Accepted work
 * transfers ownership, whereas rejected attempts leave ownership with the
 * subject. Sample counters must be monotonic within one fixture lifetime.
 */
typedef struct {
    uint64_t attempts;
    uint64_t accepted;
} nl_conformance_metrics;

/** Runner-owned storage at a stable address during a case. prepare fills module
 * pointers, count and subject; it must not register anything. Contexts and all
 * referenced metadata remain owned by the adapter until finish. The manifest
 * must leave one free host slot for the runner's dependent/failure probe.
 */
typedef struct {
    nl_host host;
    const nl_module *modules[NL_PLUGIN_MAX];
    nl_module_instance instances[NL_PLUGIN_MAX];
    size_t count;
    size_t subject;
    unsigned max_attempts_per_poll; /**< Required for BACKPRESSURE, nonzero. */
    unsigned recovery_polls; /**< 1..1024; zero selects four. */
    uint64_t expected_accepts; /**< Work fragments on recovery; zero selects one. */
} nl_conformance_fixture;

typedef struct {
    const char *name;
    unsigned capabilities;
    void *context;
    /** Build fresh actual contexts/descriptors for every case. Host is already
     * plugin-only initialized. No plugin may start here. Leave contexts in a
     * stoppable state except when a scenario explicitly asks for pending work.
     */
    nl_status (*prepare)(void *context, nl_conformance_fixture *fixture,
                         nl_conformance_case test_case);
    /** Required: inspect actual private state, ownership and data invariants.
     * STOPPED/ROLLED_BACK must verify backend resources were drained/released.
     * BLOCKED must verify rejected work is retained byte-for-byte and its
     * cursor/sequence has not advanced. RECOVERED must verify the exact retained
     * work was accepted once. RESTARTED verifies fresh behavior/session tracking.
     * Return NL_OK only when the indicated contract holds.
     */
    nl_status (*inspect)(void *context, const nl_conformance_fixture *fixture,
                         nl_conformance_checkpoint checkpoint);
    /** Required for PENDING/BACKPRESSURE capabilities. PENDING_ON must acquire
     * real subject/backend work that vetoes stop; OFF drains/cancels it.
     * PRESSURE_ON causes rejection without acceptance; OFF releases pressure.
     * SEED_WORK submits one known workload through the real subject API (or
     * readies an automatically generated one). It must not poll the host.
     */
    nl_status (*control)(void *context, nl_conformance_fixture *fixture,
                         nl_conformance_action action);
    /** Required for BACKPRESSURE. Measure actual backend/subject attempts and
     * accepted work, not the number of times the runner called poll.
     */
    nl_status (*measure)(void *context, const nl_conformance_fixture *fixture,
                         nl_conformance_metrics *metrics);
    /** Required for RESTART. Called after successful stop and fresh host/instance
     * initialization. Drain old queues, reinitialize actual contexts, regenerate
     * borrowed descriptors and select a new session where required. The runner
     * then starts the new manifest. This is not a same-context start/stop promise.
     */
    nl_status (*reinitialize)(void *context, nl_conformance_fixture *fixture);
    /** Optional RESTART workload submission after actual registration, before
     * the poll in each lifetime. Use for APIs requiring a live registration;
     * reinitialize must never register modules early to submit such work.
     */
    nl_status (*seed_restart_work)(void *context, nl_conformance_fixture *fixture);
    /** Always called after prepare, including failed checks. Must cancel/drain
     * test ownership and unregister any remaining instances before releasing
     * context/metadata. Never reinitialize live contexts to hide failed cleanup.
     */
    void (*finish)(void *context, nl_conformance_fixture *fixture);
} nl_conformance_adapter;

typedef struct {
    unsigned passed;
    unsigned failed;
    unsigned skipped;
    /** Alias check is inapplicable for a NULL or explicitly shared context. */
    unsigned alias_checks;
    unsigned alias_skipped;
    nl_conformance_case first_failed_case;
    const char *first_failure; /**< Static runner message, or NULL on success. */
} nl_conformance_result;

typedef void (*nl_conformance_report_fn)(void *context, const char *adapter,
                                         nl_conformance_case test_case,
                                         nl_status status, const char *detail);

/** Run each supported case against a fresh fixture. Missing mandatory adapter
 * callbacks are invalid arguments, not skipped coverage. Unsupported optional
 * contracts report NL_ERR_UNSUPPORTED and increment skipped. A failed case
 * reports its first check and does not prevent subsequent independent cases.
 * Return NL_OK only if every exercised case passed; failures return CONFLICT.
 * Checks remain active in Release builds (the runner never uses assert).
 */
nl_status nl_plugin_conformance_run(const nl_conformance_adapter *adapter,
                                    nl_conformance_result *result,
                                    nl_conformance_report_fn report,
                                    void *report_context);
const char *nl_conformance_case_name(nl_conformance_case test_case);

#endif
