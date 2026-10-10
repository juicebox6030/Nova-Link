# Startup plugin configuration

The `configuration` service validates startup INI text against a caller-owned
schema. The application chooses compiled plugin factories and performs checks
between fields before starting its manifest. Configuration never selects a
shared library, script, executable, callback pointer, or filesystem path to load.
The portable service performs no file or network I/O and supports no live reload.

The [offline example](../examples/config_manifest.c) reads one file, validates all
fields, constructs five built-in plugins, and starts an unordered manifest:
`multiverse`, `counter`, `logger`, `radio-link`, and `configuration`. The transport
and logger require `configuration`; both application plugins require all three
services. Those names and dependencies are fixed by the application. The module
host validates manifest dependencies and individual claim declarations before
startup; registration acquires claims and rolls back conflicts.

```sh
cmake -S . -B build
cmake --build build --target nova-config-manifest
./build/nova-config-manifest examples/plugins.ini
```

The [sample file](../examples/plugins.ini) configures a 512-level TX frame and a
counter on different zones. One host poll accepts nine native fragments into the
in-memory backend: eight DMX chunks and one counter. The example serializes and
decodes each accepted native fragment, discards it, drains ownership, and stops
the manifest. This proves local startup and queue acceptance. It does not prove
physical transmission, receiver delivery, RF timing, or proprietary Multiverse
compatibility. The DMX payload is the native NLM1 application format.

The CLI accepts exactly one filename and returns zero on success, one for input,
validation or runtime failure, and two for incorrect command syntax. Invalid
configuration never starts a manifest. File input is limited to 8,192 bytes;
the example provides storage for 32 entries. RX configurations also start and
poll successfully; without injected traffic they produce no RX frame.

## Example schema

All five sections are required. Section and key spelling is case-sensitive.
Unknown sections or keys and duplicates are errors. Integers are unsigned
decimal without a sign; booleans accept `true` and `false`; roles accept `tx` and
`rx`. Leading and trailing spaces/tabs are trimmed. Blank lines and full-line
`#` or `;` comments are accepted. Values are ASCII text: quotes, backslashes,
and inline `#` or `;` are literal characters, with no quote, escape, or comment
interpretation. Embedded NUL, other control bytes and non-ASCII input are rejected.

| Section | Key | Requirement and range |
| --- | --- | --- |
| `host` | `origin` | Required, 0..7 |
| `host` | `idle_timeout_us` | Optional, unsigned 64-bit; defaults to 0 (disabled) |
| `radio-link` | `slot_us` | Required, 1..4,294,967,295; logical scheduler slot |
| `radio-link` | `poll_budget` | Required, 1..65,535 receipt attempts per poll |
| `logger` | `echo` | Required boolean; print synchronous host events when true |
| `counter` | `role`, `zone` | Required role and zone 1..7 |
| `multiverse` | `role`, `zone` | Required role and zone 1..7 |
| `multiverse` | `universe` | Required, 1..63,999 |
| `multiverse` | `session` | Required, 0..4,294,967,295; explicit stream epoch |
| `multiverse`, TX | `interval_us` | Required, nonzero unsigned 64-bit |
| `multiverse`, TX | `full_interval_us` | Required, unsigned 64-bit, at least `interval_us` |
| `multiverse`, TX | `chunks_per_tick` | Required, 1..8; one poll sends up to this budget |
| `multiverse`, TX | `slots` | Optional, 0..512; defaults to 512 |
| `multiverse`, TX | `initial_level` | Optional, 0..255; defaults to 0 for every configured slot |
| `multiverse`, RX | `peer_origin` | Required, 0..7; must differ from local host origin |
| `multiverse`, RX | `loss_timeout_us` | Required, nonzero unsigned 64-bit |
| `multiverse`, RX | `assembly_timeout_us` | Required, nonzero, at most `loss_timeout_us` |

TX-only fields are rejected for RX, and RX-only fields are rejected for TX.
Counter and Multiverse zones must differ because the example routes different
payload protocols on those zones, even when both are read-only. All integers
are validated as 64-bit values before narrowing to the SDK's field widths.
Only after these checks does the example initialize other plugin contexts and
the host. The schema does not permit modifying dependencies, plugin names, or
selecting arbitrary factories.

To try RX, change `multiverse.role` to `rx`, remove its TX-only fields, and add:

```ini
peer_origin=2
loss_timeout_us=50000
assembly_timeout_us=5000
```

Keep these keys within `[multiverse]`; choose a peer different from `host.origin`.
`counter.role=rx` independently enables a counter receiver.

## Using the portable service

Include `nova_link/config_plugin.h` and link `NovaLink::nova_config_plugin`, or
the aggregate `NovaLink::nova_plugins`. Define stable `nl_config_section` and
`nl_config_field` arrays, zero-initialize an `nl_config_context`, and provide
`nl_config_entry` storage. `nl_config_parse()` checks the schema and text without
executing callbacks. On failure, `nl_config_error` reports a status, section/key
and source line; line zero denotes a schema error or missing required value.
Entries may contain partial output and the context is invalid after failure.

Use `nl_config_value()`, `nl_config_uint()` and `nl_config_bool()` after a
successful parse to validate application-specific relationships and initialize
compiled contexts. Then construct `nl_config_module()` and the other descriptors
and call `nl_modules_start()`. Consumers may require the name `configuration` and
retrieve its context through `nl_module_find(host, "configuration")->module.service`.

The service borrows entries and schema storage; both must remain alive and
immutable while the parsed context is used, including getters after shutdown,
until the next parse or the context is discarded. The input text may be released after parsing.
The service locks reparsing while active. Shutdown unlocks reparsing without
clearing validated entries; this is a lifecycle boundary, not live reload.
Writable outputs and entry storage must not overlap input or schema storage;
read-only schema strings may share storage.
Serialize configuration, module, and host operations on the same application
event loop. For a new TX lifetime, drain old transport ownership and choose a new
session before reinitializing the Multiverse context.

The [plugin development guide](../plugins/README.md) describes module lifecycle
rules; [Multiverse emulator documentation](Multiverse_Emulator.md) describes the
remaining real-capture and hardware limitations.
