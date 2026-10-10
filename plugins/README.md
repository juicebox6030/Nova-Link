# Compiled plugins

Application protocols, transports, and local services use the same installed
`nl_module` descriptor and `nl_plugin` hooks. The base manages names, dependencies,
zone claims, lifecycle, and dispatch; the plugin owns its behavior and backend.
All state is caller-owned, with no allocation or OS dependency in the portable
implementations.

| Implementation | Installed API | Role |
|---|---|---|
| `counter.c` | `nova_link/counter_plugin.h` | Four-byte counter application |
| `multiverse.c` | `nova_link/multiverse_plugin.h` | DMX levels over native NLM1 chunks |
| `radio_link.c` | `nova_link/radio_plugin.h` | Bounded native PUSH/PULL transport |
| `logger.c` | `nova_link/logger_plugin.h` | Lifecycle-managed host observer service |
| `config.c` | `nova_link/config_plugin.h` | Schema-validated INI parsing and typed value service |
| `capture.c` | `nova_link/capture_plugin.h` | Bounded raw-observation JSONL staging and output service |

Use `nl_counter_module()`, `nl_multiverse_module()`, `nl_radio_link_module()`, and
`nl_logger_module()` to create descriptors. The application factories depend
on the default transport name `radio-link`; adjust descriptor names/dependencies
before startup when composing multiple instances. Start an unordered manifest
with `nl_modules_start()`, call `nl_host_poll()` for input polling and ticks, and stop
with `nl_modules_stop()`. Modules start after their dependencies and stop before
them. Failed startup rolls back its manifest, and active dependents prevent early
provider removal.

`counter.c` sends a four-byte big-endian counter. Configure its context as a
transmitter with an exclusive zone claim or a receiver with a read-only claim.
The transmitter advances its value only when the transport accepts it. The
receiver ignores other zones and payload sizes. `counter.h` is a compatibility
include for the installed header.

`multiverse.c` bridges the portable DMX/Multiverse model to native host payloads.
It chunks full/delta updates, retains a rejected TX chunk for retry, and commits
complete RX levels atomically. Configure universe, zone, session, and peer origin
explicitly. Use FIFO queues and native sequence order; a complete 512-slot update
needs several native fragments. NLM1 is a local application protocol, and NVS1 is
a separate test-only codec. Neither implements proprietary Multiverse RF.

`radio_link.c` attaches a transport during startup and polls bounded PULL work
outside callback dispatch. Its backend exchanges validated `nl_frame` values;
physical encoding and device I/O belong to that backend. An optional commit
callback supports two-phase PULL ownership. Commit failures retain the response
without redelivering it, and pending ownership can block shutdown. Backend
start/stop/can-stop callbacks provide the same lifecycle for in-memory and future
board adapters.

An invalidated PULL receipt (`NL_ERR_STALE`/`NL_ERR_EMPTY` from commit) is abandoned
before polling the replacement. Use latest-value coalescing only for independent
state messages; Multiverse-model chunk groups require FIFO.

`logger.c` attaches an application-supplied observer during startup and detaches
it on shutdown. It is a local service, with no zone claim or transport dependency.
Observer callbacks run synchronously and must not re-enter host APIs.

`config.c` accepts caller-supplied INI text and a field schema, then exposes
validated values through typed getters. It registers as a local provider through
the normal lifecycle. The example application selects factories and composes
its manifest from those values. The offline `nova-config-manifest examples/plugins.ini` example
reads a file and applies included plugin settings. See the
[configuration guide](../docs/Plugin_Configuration.md) for limits and ownership.

`capture.c` stages caller-supplied raw observations using the existing capture
JSONL schema. Its output callback owns file/device I/O; rejected output retains
the exact record and pending work vetoes ordinary stop. The
[hardware preparation guide](../docs/Hardware_Preparation.md) maps this service
to the documented ESP32-S3/CC1352R targets and 5911 reference without assuming
proprietary PHY settings or RF decoding.

Generate a new standalone plugin project with
`python3 tools/new_plugin.py my-plugin --kind application --output build/my_plugin`.
Use `--kind service` or `--kind transport` for those roles. The generated CMake
project uses the installed SDK and includes lifecycle and reusable conformance tests; see the
[development guide](../docs/Development.md).

Use the explicit `NovaLink::nova_plugin_conformance` target to run one lifecycle
contract against any compiled plugin. Adapters provide fresh contexts and a
manifest for each case, and declare the optional behavior they can exercise.
The [conformance guide](../docs/Plugin_Conformance.md) explains passed, failed and
skipped cases. The independent `NovaLink::nova_fault_backend` target supplies
deterministic transport scenarios described in the
[fault guide](../docs/Transport_Fault_Simulation.md). Neither developer target
is part of `NovaLink::nova_plugins` or the ESP-IDF component.

For a new plugin, allocate persistent context, define the hooks it needs, and
declare an `nl_module` with a unique name/version, kind, claims, and dependencies.
Use `nl_host_send()` for application payloads and `nl_module_find()` for local
provider services. Keep context and borrowed metadata alive until stop succeeds.
Give each mutable instance its own context. Reusing non-null `hooks.context` is
rejected unless both modules set `shared_context = true`; only opt in for
immutable/stateless context or callbacks that safely support independent
registrations. Sharing with a legacy plugin asserts its context is safe too.
Hooks return promptly; registry mutation and recursive poll/dispatch are guarded.
Zone access is cooperative checking among trusted C plugins, with no sandbox.

Run `./build/nova-sim` for a complete counter-to-counter manifest simulation.
Run `./build/nova-plugin-sim` for the
[combined simulation](../examples/plugin_simulation.c) of radio-link, logger,
counter, and Multiverse-model modules on two hosts.
Run `./build/nova-plugin-fault-sim` for deterministic adapter transfer delay,
disconnect/reconnect, congestion and restart scenarios; the
[fault guide](../docs/Transport_Fault_Simulation.md) describes their guarantees.
The [development guide](../docs/Development.md) includes a combined counter,
Multiverse-model, and transport manifest, backend ownership rules, and the direct
registration API for custom integration.
