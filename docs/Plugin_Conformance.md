# Plugin conformance tests

The installed `NovaLink::nova_plugin_conformance` target runs the same lifecycle
and ownership contracts against an actual plugin and its providers. Its public
API is [`plugin_conformance.h`](../include/nova_link/plugin_conformance.h).
Generated projects include an adapter and a conformance CTest alongside their
plugin-specific smoke tests. Custom projects can use the same adapter contract.

This is optional developer support. It is separate from `nova_link`,
`nova_plugins`, and the ESP-IDF board component, so production applications do
not inherit test code. The runner itself uses caller-owned storage and does not
allocate memory, perform I/O, or read a clock. A hosted test executable may
print reports and use a simulated backend. Checks remain active in Release
builds; no contract depends on C `assert`.

## Contracts and coverage

| Case | What the runner and adapter verify |
|---|---|
| Lifecycle, owner, alias | Exact host/instance binding, duplicate active-instance rejection, cross-host active-instance rejection, mutable-context alias rejection, successful poll and cleanup |
| Startup rollback | Real subject startup runs and acquires its normal resources, then a wrapper returns an injected failure; the real stop hook runs exactly once and releases resources |
| Manifest rollback | Every real supplied module starts before a dependent fails; the complete manifest rolls back and releases ownership |
| Dependency stop | Both module and raw-host unregistration refuse a live dependent; an external dependent prevents partial manifest shutdown |
| Pending stop | Real subject/backend ownership vetoes stop; draining it permits shutdown |
| Backpressure | Real attempts stay within the declared budget across three rejected polls, acceptance stays unchanged, rejected bytes/cursor remain intact, and recovery accepts the expected fragments exactly once |
| Restart | Successful stop and resource drain precede fresh host, native sequence tracking, actual context and descriptor initialization; a new poll proves fresh behavior, including a new session where required |

The four common cases run for every adapter. Pending-stop, backpressure and
restart require explicit capability flags and corresponding callbacks. A service
with no TX work skips backpressure; a plugin whose stop cancels pending work
rather than vetoing it skips pending-stop and verifies cancellation through its
cleanup inspection and plugin-specific tests. These are different contracts.

The result records passed, failed and skipped cases. The report callback receives
one event per case, with `NL_ERR_UNSUPPORTED` for an unadvertised capability.
Mutable-context alias checks are counted separately: a NULL context or an
explicit `shared_context` opt-in makes that check inapplicable, and increments
`alias_skipped`. Skips never count as exercised coverage. A missing callback
for an advertised capability is an invalid adapter, not a passing or skipped
test.

The startup wrapper injects failure **after the real start succeeds**. This
exercises cleanup of normally acquired resources. It does not discover every
failure point inside a backend's initialization. Keep plugin-specific tests for
partial initialization, malformed inputs, and protocol semantics. The harness
checks trusted compiled C; it cannot sandbox callbacks, prevent crashes in
plugin code, or establish physical radio compatibility.

## Writing an adapter

Link a test executable to the support target and the actual plugin:

```cmake
find_package(NovaLink CONFIG REQUIRED)
add_executable(test_my_plugin test_conformance.c)
target_link_libraries(test_my_plugin PRIVATE
    NovaLink::nova_plugin_conformance my_plugin)
add_test(NAME my_plugin_conformance COMMAND test_my_plugin)
```

Give the adapter stable, caller-owned context and descriptors. `prepare` runs
once for each case and fills `fixture.modules`, `count`, and `subject` using the
real factories. The runner has already initialized a plugin-only host; do not
register modules in `prepare`. Include actual providers in the manifest, leave
one host slot free for the failure/dependency probe, and keep all borrowed
strings, arrays and contexts alive until `finish` returns. The runner accepts
unordered manifests, so normal dependency resolution remains part of the test.
Very large generated manifests can consume every host slot. The starter then
disables the conformance executable by default with a CMake explanation, while
keeping its runtime manifest and smoke tests valid. Test a smaller provider
composition that leaves room for probes before enabling it.

`inspect` is mandatory. Read the real context and backend rather than asserting
that a callback was reached. For active modules, verify owner IDs and service
attachments. For stopped or rolled-back modules, verify outstanding receipts,
queues and device operations were drained or canceled. The base automatically
releases its own claims and slots; checking only those fields can miss a leaked
backend resource.

For backpressure, `control(PRESSURE_ON)` fills or blocks the real backend, and
`control(SEED_WORK)` submits a known workload through the real plugin API.
Neither callback polls the host. `measure` returns cumulative actual attempts
and accepted fragments. Set a nonzero `max_attempts_per_poll`; the runner checks
this bound after every rejected and recovering poll. Set `recovery_polls` for
the workload, and `expected_accepts` for its fragment count. Their defaults are
four polls and one accepted fragment. An application that automatically emits
one value each poll can select one recovery poll.

Each blocked poll calls `inspect(BLOCKED)` immediately. Compare retained data
byte-for-byte, including sequence and cursor state. After pressure releases,
`inspect(RECOVERED)` must confirm the accepted workload matches the rejected
one and was accepted once. Counters alone cannot detect a dropped or changed
payload. Ownership acceptance is local; it does not imply transmission or a
peer acknowledgement.

For pending-stop, acquire a real receipt or backend operation in
`control(PENDING_ON)`. After the runner checks `NL_ERR_BUSY`,
`inspect(BLOCKED)` verifies it still belongs to the plugin. Drain or cancel it
in `control(PENDING_OFF)` so ordinary shutdown can complete.

For restart, `reinitialize` runs only after successful stop and cleanup, with a
fresh native host and cleared module-instance storage. Rebuild actual plugin
contexts and borrowed descriptors, select a new Multiverse-model TX session,
and drain old backend queues before reusing them. Seed known fresh work where
the plugin needs a submission. APIs which require a live registration can use
the optional `seed_restart_work` callback, invoked after startup and before the
polls in both restart lifetimes. Set `restart_polls` to the required bounded
number of polls in each lifetime; zero selects one and values above 1024 are
invalid. This allows asynchronous adapters to finish real transfers before stop
and inspection. `inspect(RESTARTED)` runs after the restarted host polls, so
check fresh work and session/sequence behavior as well as owner
binding. A restart flag does not promise that a stopped context can be
registered again without reinitialization.

`finish` always runs after `prepare`, even after a failed contract. Cancel/drain
test ownership, stop any remaining modules, then release fixture storage. Never
clear or reinitialize a live context to disguise a cleanup failure. The failure
report remains the original contract failure even if fixture cleanup succeeds.

An adapter reports a failed inspection by returning an error. The runner keeps
executing independent cases with fresh fixtures, records the first failing case
and a static explanation, and returns `NL_ERR_CONFLICT` if any exercised case
failed. Test executables should return failure when the runner does:

```c
nl_conformance_result result;
nl_status status = nl_plugin_conformance_run(&adapter, &result, report, NULL);
return status == NL_OK ? 0 : 1;
```

## Repository fixtures

[`test_plugin_conformance.c`](../tests/test_plugin_conformance.c) adapts the
included counter, radio-link, logger, Multiverse-model, configuration and capture
plugins. Its data tests use actual native framing and radio queues, rather than
a second implementation of the plugins. The Multiverse fixture restarts with
a fresh session after draining ownership and resetting native host history.
Configuration checks preserve typed values and enforce the active reparsing
lock.
The capture adapter uses actual bounded JSONL staging and an atomic output sink
to verify pending-stop veto, immutable retries, exact acceptance and fresh
timestamp state after restart.

[`test_spi_conformance.c`](../tests/test_spi_conformance.c) adapts the actual
SPI backend service and SPI radio-link provider through the virtual driver and
native slave. Both run all seven cases, checking byte-preserving full-queue retry,
pending TX ownership, provider cleanup and fresh lower-sequence restart work.

[`test_plugin_conformance_negative.c`](../tests/test_plugin_conformance_negative.c)
feeds deliberately broken compiled plugins to the runner. These tests ensure
it catches resource leaks, ignored pending ownership, changed rejected work,
unbounded attempts, invalid pressure acceptance, duplicate recovery and stale
restart behavior. Malformed fixture metadata and invalid adapter callbacks
also fail predictably. This protects the harness itself from becoming a test
that reports success without checking the advertised behavior.

Run the focused cases with:

```sh
ctest --test-dir build --output-on-failure -R 'plugin_conformance|spi_conformance'
```

These contracts complement the
[configuration guide](Plugin_Configuration.md) and
[transport fault simulations](Transport_Fault_Simulation.md). Synthetic native
and NLM1 tests do not implement or validate proprietary Multiverse RF.
