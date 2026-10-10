# Offline validation record

## Reusable plugin contracts and documented hardware preparation (2026-10-10)

The SDK exports `NovaLink::nova_plugin_conformance` and
`NovaLink::nova_fault_backend` as explicit developer dependencies, separately
from the production plugin aggregate and ESP-IDF component. Generated application,
service and transport projects include adapters for the same conformance runner;
generated transports also expose six individually selectable deterministic fault
scenarios. Their production targets retain only the runtime SDK dependency.

The actual counter, radio-link, logger, Multiverse-model, configuration and capture
factories passed **35 exercised contract cases**, with **7 optional cases explicitly
skipped**. The negative fixture suite detects eleven deliberately broken plugin
behaviors, including resource leaks, ignored pending ownership, altered rejected
work, unbounded attempts, duplicate acceptance and stale restart behavior. The
Multiverse fixture drains old work, resets native history, selects a fresh model
session and submits fresh TX work after reinitialization.

Independent full runs passed **45/45 CTest entries** each in GCC Debug, Release
and ASan/UBSan, and **29/29** with Clang and the extended prototype disabled.
The final generated restart-work change also passed the affected scaffold entry
again in all four configurations.
The installed consumer exercises the six-plugin aggregate, both developer targets,
and capture output backpressure, retry and shutdown. Freestanding compilation,
SDK export isolation, warnings-as-errors Doxygen, 84 relative Markdown links and
`git diff --check` passed. Actual capture-service JSONL output, including timestamp
zero and UINT64_MAX, passes the existing analyzer with exact payload preservation.

The reusable fault backend preserves FIFO ownership, invalidated receipt safety,
bounded queues and drain-before-restart behavior. The migrated combined simulator
retains its previous deterministic results: 100 FIFO congestion retries, 800
receipt retries, 50 disconnected PUSH rejections and 88 native completions before
exact-frame recovery and restart. These are logical software scenarios rather
than measured device timings.

The hardware preparation follows the documented ESP32-S3/CC1352R targets and
City Theatrical 5911 reference. The platform test compiles the production
ESP-IDF component sources with a desktop shim and runs the example lifecycle
twice. Separately, the actual `esp32s3` vendor build succeeded with ESP-IDF
**v5.5.1** (revision `fcae32885b0296b32044cb99ecbdc50d98dddb83`) and Xtensa
GCC **14.2.0** (`esp-14.2.0_20241119`). It compiled all 18 production component
sources without warnings and generated ELF/BIN artifacts. This selected SDK
baseline is recorded in the [hardware preparation guide](Hardware_Preparation.md);
it is a new implementation choice rather than a previously documented board
specification. Hardware execution, the CC1352R vendor build, packet captures and
real RF interoperability remain unverified. The capture plugin formats supplied observations;
it does not select a PHY or decode proprietary Multiverse packets. The synthetic
codec remains excluded from SDK installation and the board component.

```sh
ctest --test-dir build --output-on-failure \
  -R 'plugin_conformance|fault_backend|capture_plugin|platform_prep|plugin_scaffold'
```

See the [conformance contract](Plugin_Conformance.md),
[fault scenarios](Transport_Fault_Simulation.md) and
[development guide](Development.md). No UniFi or gateway settings were changed.

## Plugin development tooling and transport faults (2026-10-10)

The SDK now includes an allocation-free configuration service, a standalone
plugin starter generator, an offline startup configuration CLI and a deterministic
transport fault simulation. These address the Host CLI configuration and
auto-generated plugin boilerplate goals in [the design](requirements.adoc).
Configuration remains outside the base: the service validates caller-supplied
text against a schema, while the example chooses compiled factories and composes
the manifest. Live reload and dynamic code loading remain future work.

Initial complete runs passed **39 CTest entries** each in GCC Debug, Release
and ASan/UBSan, and **23 entries** in Clang with the extended prototype disabled.
After adding the CLI regression entry, that new entry passed in all four
configurations. Affected configuration and plugin integration entries were also
rebuilt and rerun. The final configured suites therefore passed cumulatively
**40/40 entries** in each GCC configuration and **24/24** in Clang.

The starter tests cover all three plugin kinds, invalid/reserved names,
dependency validation, safe destination handling and relocated templates. The
installed-SDK test stages the generator and templates in a temporary prefix,
then generates, builds and runs application, service and transport projects via
`find_package(NovaLink)`, including paths with spaces. Configuration tests cover
strict schemas, typed values, bounded storage, error diagnostics and provider
lifecycle. Eight CLI cases check successful TX/RX startup, optional defaults,
command/file errors and invalid field relationships rejected before startup.

`nova-plugin-fault-sim` exercises delayed queue handoff, disconnected PUSH
rejection, retained PULL receipts with exactly-once dispatch, bounded 8/16 TX/RX
queues, congestion, coalescing, drain-before-shutdown and explicit model/native
restart. The deterministic baseline completes 11 DMX updates from 401 submitted
snapshots, then recovers the exact final 512 levels and a new session. Transfer
delays are logical test inputs; this does not measure physical SPI or RF timing.

The freestanding SDK build, refreshed installation, independent aggregate-plugin
consumer and warnings-as-errors Doxygen build passed. The consumer exercises
schema parsing, typed values and the configuration provider alongside the four
existing plugins. The synthetic codec/header remain excluded from installation.
The configuration source also passed strict GCC `-fanalyzer` checks. Markdown
relative links and `git diff --check` pass. The CI template now tests the SDK
compiler matrix separately from the extended prototype's GCC/UBSan job; hosted
CI remains inactive as described below.

```sh
python3 tools/new_plugin.py scene-player --kind application --zone 7 \
  --output build/scene_player
./build/nova-config-manifest examples/plugins.ini
./build/nova-plugin-fault-sim
ctest --test-dir build --output-on-failure -R 'config|plugin_scaffold|plugin_fault'
```

See the [development guide](Development.md),
[configuration contract](Plugin_Configuration.md) and
[transport scenarios](Transport_Fault_Simulation.md). No hardware, packet
capture, device/network operations or UniFi/gateway changes were used. Vendor
SDK builds and proprietary Multiverse RF interoperability remain unverified.

## Uniform plugins and Multiverse host integration (2026-10-09)

The installed SDK now has named `nl_module` descriptors with declarative claims,
provider dependencies and service lookup. Unordered manifests validate before
startup, start providers first and roll back failure. Shutdown protects live
dependents, pending transport receipts and optional backend-owned work. The
plugin-only base registers transport, logging and application modules through
one lifecycle and polls input before application ticks.

Counter, radio-link transport, logger and Multiverse-model plugins are installed
individually or through `NovaLink::nova_plugins`. The native Multiverse plugin
segments 512-slot frames into eight bounded NLM1 payloads, retries queue pressure
without changing frozen chunks, and reconstructs complete frames atomically.
NLM1 is a native application format, not proprietary Multiverse RF.

GCC Debug, Release and ASan/UBSan each passed all **35 CTest entries**. Clang
passed all **19 entries** with the separate extended prototype disabled for its
previously documented conversion warnings. The six changed/new base and plugin
sources passed GCC `-fanalyzer` with strict C99/conversion warnings. A
freestanding build installed successfully; the independent installed consumer
linked the aggregate plugin target and ran a complete manifest startup,
TX queue acceptance and shutdown, alongside the normalized engine checks.
Doxygen generated the public reference with warnings treated as errors.

New tests cover dependency graphs, missing providers, cycles, duplicate names,
context-sharing opt-in, rollback, provider shutdown guards, callback reentry,
bounded PUSH/PULL polling, queue backpressure, aborted commits, stale/empty
receipts after latest-state replacement, lifecycle/observer ownership and legacy
adapter compatibility. Multiverse plugin tests exercise the complete framed
host/radio path for all 0..512 slot counts, independent NLM1 golden bytes and
every-byte corruption, immutable retries/coalescing, loss/recovery, filters,
explicit restart, deadlines, two independent universes and 65,540 updates.

`nova-plugin-sim` bootstraps four plugins per host from manifests. It delivered
301 counters and 25 exact complete DMX frames despite 141 dropped native
fragments and 73 corrupted payloads, recovered the final 512-channel frame via
a clean FULL and then reported link expiry through silence. This is a logical
software scenario with no airtime/physical timing claim. The original counter
simulation also runs through the common transport/module lifecycle.

```sh
./build/nova-plugin-sim
ctest --test-dir build --output-on-failure
cmake --build build --target docs
```

No hardware, device/network operations, or UniFi/gateway changes were used.
Vendor SDK builds and actual Multiverse RF/fixture interoperability remain
unverified. See the [plugin guide](../plugins/README.md) and
[native Multiverse integration contract](Multiverse_Emulator.md).

## Multiverse emulator checks (2026-10-09)

Added the installed `NovaLink::nova_multiverse` normalized TX/RX engine, a
separate test-only synthetic byte codec, seeded fault simulation, offline replay
through the C receiver, a versioned synthetic log, and differential capture
analysis. These implement hardware-independent host/adapter state and ownership;
they do not establish City Theatrical RF compatibility.

GCC Debug, Release and ASan/UBSan builds passed all **30 CTest entries**.
Clang 22.1.8 passed all **14 entries** with `NOVA_BUILD_EXTENDED=OFF`.
The full Clang build encountered existing enum-to-uint8 conversion errors in
`experimental/extended/src/nl_zone.c:44` and `nl_host.c:239`; those prototype
sources were not changed by this work. GCC still tests the prototype in all
three complete configurations. The new C modules passed GCC `-fanalyzer`,
strict C99/conversion warnings, and freestanding compilation. Doxygen generated
the API reference with warnings as errors. The installed consumer linked the
normalized engine and exercised a complete TX/RX update; the test codec/header
were excluded from SDK installation. ESP-IDF/vendor and physical RF builds
remain unverified.

The new C suite covers all 0..512 slot counts with chunk sizes 1, 7, 64, 127,
and 512; full, changed-span and empty refresh updates; 65,540 sequential updates
including 16-bit wrap; failed/stale TX completions and frozen snapshots under
host changes; overlapping/reordered chunks and conflicting metadata; missing
bases, recovery, assembly/loss deadlines, session/universe filtering; duplicate
rejection after expiry; backward timestamps, end-of-uint64 clocks and token
exhaustion; malformed frames, truncations and each golden packet byte corrupted.
Independent Python `struct`/`zlib` vectors validate C framing and CRC behavior.

Replay tests run 0%, 20%, 75% and 100% loss scenarios, verify every complete frame
against the exact stimulus snapshot, compare simulator/replay result counters,
and check malformed logs, unknown profiles, wrong settings, silence expiry,
CLI output and preservation of source captures. The eleven-observation versioned
example reconstructs four exact frames before reporting link loss. The capture
analyzer has seven unit tests, including distribution comparisons that keep
PHY/frequency/length/CRC groups separate and account for unequal sample counts.

Reproduce the emulator/demo using [its guide](Multiverse_Emulator.md), or run:

```sh
ctest --test-dir build --output-on-failure -R multiverse
python3 tools/replay_multiverse.py examples/multiverse.synthetic.jsonl \
  --end-us 104000 --summary-only
python3 -m unittest discover -s tests -p test_rf_capture.py
cmake -S . -B build/clang -DCMAKE_C_COMPILER=clang \
  -DCMAKE_BUILD_TYPE=Debug -DNOVA_BUILD_EXTENDED=OFF
cmake --build build/clang --parallel
ctest --test-dir build/clang --output-on-failure
```

No hardware, real packet captures, network/device I/O, RF transmission, or
UniFi/gateway changes were used. The real PHY, framing/integrity, hopping,
mDMX/FEC, SHoW Key and control exchanges still need measurements and fixture
validation. The emulator's sequence/session/chunk format and timing are local
model assumptions; the synthetic codec is not an on-air implementation.

## Consolidation checks (2026-10-09)

The root build now includes the installed SDK, the independent DMX library and
capture analyzer, and the separately linked extended protocol prototype.
GCC Debug, Release, and ASan/UBSan configurations each passed all **27 CTest
entries**. The extended prototype also passed its standalone UBSan trap build
(16 entries), and the SDK without tools or the prototype passed seven entries.
All builds treat compiler warnings as errors. Both source trees passed GCC
`-fanalyzer` with strict conversion warnings, and both Doxygen references built
with warnings as errors. Local Markdown file links were checked.

The freestanding SDK/DMX build installed successfully; a separate
`find_package(NovaLink)` program linked both `NovaLink::nova_link` and
`NovaLink::nova_dmx` and exercised their encoders. The capture analyzer passed
five Python unit tests. The prototype's 88 Python tests also passed directly
under Python 3.14; CTest used Python 3.12. No third-party Python dependencies
are needed.

Consolidation fixes include distinct CMake targets and test names, installation
of DMX headers/library, root build switches applying to the prototype,
documentation output-directory creation, and ignored nested build/bytecode
artifacts. Empty-message reassembly now avoids pointer arithmetic and zero-byte
`memcpy` on NULL storage; invalid storage returns an error. A regression covers
empty zero-capacity messages and recovery from insufficient storage.

Reproduce the default checks with the README commands. For installation:

```sh
cmake -S . -B build/core -DNOVA_BUILD_TESTS=OFF -DNOVA_BUILD_TOOLS=OFF \
  -DNOVA_BUILD_EXTENDED=OFF -DCMAKE_C_FLAGS=-ffreestanding
cmake --build build/core --parallel
cmake --install build/core --prefix "$PWD/build/sdk"
cmake -S tests/consumer -B build/consumer -DCMAKE_PREFIX_PATH="$PWD/build/sdk"
cmake --build build/consumer
./build/consumer/consumer
cmake --build build --target docs docs-extended
```

Local sanitized builds used the compatible runtimes described below, copied
into ignored `build/sanitizer-runtime`, with local linker search path/RPATH.
The versioned GitHub workflow template (`config/ci.github-actions.yml`) covers
GCC, Clang, ASan/UBSan, installed consumers, the standalone prototype, Python
3.11/3.14, and both API references. It is inactive: the saved GitHub token lacks
the `workflow` scope needed to publish `.github/workflows/ci.yml`. Hosted CI and
Clang checks have not run for this consolidation. Hardware,
vendor SDKs, and actual RF/Multiverse interoperability remain unvalidated.
No UniFi or gateway settings were changed.

The earlier SDK-only validation record follows.

Checked on 2026-10-09 with GCC 16.1.1, CMake 4.3.0, Python 3.14.6 and Doxygen.
The scope is the portable C99 SDK and local software models. No packet captures,
physical links, RF transmission, board access, or UniFi/gateway changes were used.

## Reproducible software checks

Debug, Release and ASan/UBSan builds each passed **all eight CTest entries**:
`protocol`, `stream_zones`, `host`, `radio`, `integration`, `simulation`,
`offline_tools`, and `rf_feasibility`.

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build --parallel 2
ctest --test-dir build --output-on-failure

cmake -S . -B build/release -DCMAKE_BUILD_TYPE=Release
cmake --build build/release --parallel 2
ctest --test-dir build/release --output-on-failure

cmake -S . -B build/sanitized -DCMAKE_BUILD_TYPE=Debug -DNOVA_ENABLE_SANITIZERS=ON
cmake --build build/sanitized --parallel 2
ctest --test-dir build/sanitized --output-on-failure
```

Sanitizer commands require matching compiler runtimes. This workspace used local
compatible ASan/UBSan libraries under ignored `build/sanitizer-runtime`, with the
sanitized build's linker search path and RPATH pointing there. No system library
or network configuration was changed.

The core also compiled with `-ffreestanding`, generated the public Doxygen
reference with warnings treated as errors, installed into a local SDK directory,
and passed the separate `find_package(NovaLink)` consumer:

```sh
cmake -S . -B build/core -DNOVA_BUILD_TESTS=OFF -DNOVA_BUILD_TOOLS=OFF \
  -DCMAKE_C_FLAGS=-ffreestanding
cmake --build build/core --target nova_link docs --parallel 2
cmake --install build/core --prefix "$PWD/build/sdk"
cmake -S tests/consumer -B build/consumer -DCMAKE_PREFIX_PATH="$PWD/build/sdk"
cmake --build build/consumer
./build/consumer/consumer
```

GCC `-fanalyzer` completed without diagnostics under the same strict warnings:

```sh
mkdir -p build/analyzer
(cd build/analyzer && gcc -std=c99 -Wall -Wextra -Wpedantic -Wconversion \
  -Wshadow -Werror -fanalyzer -I../../include -c ../../src/*.c)
```

Clang and vendor SDK builds were not run locally.

## Covered behavior

- All 256 header values and all payload sizes 0–100, golden transport vectors,
  maximum frame size, malformed input, and 200,000 deterministic parser bytes.
- All 65,536 previous/current sequence pairs, independent streams, idle timeout,
  explicit origin reset, queue wrap/overflow, and retry without sequence loss.
- Plugin claims, startup rollback, callback reentry, stale generation handles,
  generation exhaustion after success/failure, own-origin rejection, and logging.
- Current-window BURST holds on two separate synchronized radio schedulers,
  repeated announcements, congested RX, late/subsequent TX preparation,
  deadline/overflow checks and metadata. Pre-scheduler RX does not hold future slots.
- PULL preparation/retry/commit, stale responses, coalescing during staging,
  byte-identical revisions after sequence wrap, and uint64 token exhaustion.
- 600 full-size end-to-end payloads with duplicate copies and sequence wraps;
  overtaking/stale arrivals and metadata. The example delivers 300 counters once
  each while rejecting 300 duplicate copies. These are logical-time simulations.
- RF calculator dimensional/golden results, backlog and sequence horizons,
  infeasible/overloaded bounds as `null`, per-zone service rate, scheduler-compatible
  integer timing, dual-band assumptions, and numeric overflow errors.

Boundary tests inject near-exhausted internal counters instead of making billions
of registrations or RX calls. Applications must not mutate that bookkeeping.

## Opus collaboration

The requested collaborator is invoked through the local Claude CLI using
`--model claude-opus-5-5 --effort high`. Returned model metadata is checked.
Sources are read-only for the collaborator; temporary probes and models live
under ignored `build/opus-review`. Every prompt repeats the no-hardware,
no-capture and owner gateway boundaries.

Checkpoint 1 independently built/tested the initial implementation and created
adversarial API probes plus an analytic/Monte Carlo RF model using the real
scheduler. Its concrete findings led to current-window BURST holds, transactional
PULL revisions, generation handles, own-origin rejection and logger guards.
Optional per-stream coalescing addresses newest-state loss for represented
streams; per-zone fairness is still pending. Protocol limits were documented
separately rather than assigned an unreviewed wire encoding.

Checkpoint 2 independently passed fresh Debug and sanitizer suites (8/8 each),
ported prior probes, and added 14 targeted probes and real-scheduler models.
It confirmed the PULL, handle, logger and own-origin fixes. Two further findings
led to `nl_radio_prepare_tx()` for late/subsequent BURST sends and RF service-rate
checks. Pre-scheduler RX holds were removed; unset handles are documented as
`NL_PLUGIN_ID_NONE`. Non-monotonic adapter timestamps remain invalid by contract.
Timing inputs now match the C scheduler and bitrate/receiver assumptions are
explicit. Checkpoint 3 independently passed Debug/sanitizer suites (8/8 each)
and verified current TX/RX timing with three seeds and multiple assumed airtimes.
Its careful adapter model maintained identical zones at every sample, including
30% assumed submission rejection. It also identified the calculator's improper
use of the extension to fit the first announcement. That check now uses the base
deadline; adapter preflight ordering and prolonged-congestion limits are explicit.
Checkpoint 4 passed its Debug suite (8/8) and four relevant sanitized entries,
then checked the strict announcement deadline against the real scheduler at
998, 999 and 1000 µs. It confirmed the final calculator/docs/integration changes
and found no new Medium-or-higher issue. Its remaining receiver-processing/clock
margin concern is now explicit in `--fixed-us` and the adapter documentation.
All four checkpoints returned `claude-opus-5-5` model metadata successfully,
with no permission denials; each invocation specified `--effort high`.
Local prompts/reports are in `build/opus-review/checkpoint1.*` and
`build/opus-review/checkpoint2.*`, `build/opus-review/checkpoint3.*`, and
`build/opus-review/checkpoint4.*`; they are working artifacts, not required SDK
dependencies.

## RF assumptions and limits

No dedicated RF simulator or SDR tools were available; nothing was installed.
The collaborator used temporary C emulation. The maintained calculator is
`tools/rf_feasibility.py`, with golden checks in `tests/test_rf_feasibility.py`.

| Assumed transmission | Calculated channel time |
|---|---:|
| 102-byte fragment + 11 overhead bytes, 50 kb/s | 18,080 µs airtime |
| Same bytes, 200 kb/s | 4,520 µs airtime |
| 102-byte fragment + 9 overhead bytes, 2 Mb/s | 444 µs airtime |
| Previous row + 200 µs setup | 644 µs required window |
| Time-shared copies at 200 kb/s (+11 bytes) and 1 Mb/s (+8 bytes), 200 µs setup each, two 500 µs switches | 6,800 µs required window |

These effective bitrates, byte counts and costs are inputs, **not verified TI PHY
values**. Rates account for FEC, spreading or line coding. Dual-band fit describes
sender occupancy only; it does not establish that a receiver hears both copies.
The fixed per-copy cost must include worst-case receiver radio processing and
clock granularity as well as setup/turnaround. Host delay is applied after radio
queueing and does not relax the first-announcement deadline. The example's
200 µs total fixed cost remains an assumption requiring a real timing budget.
For example:

```sh
python3 tools/rf_feasibility.py --bitrate 2000000 --overhead-bytes 9 \
  --slot-us 644 --fixed-us 200 --zones 4 --metadata-slot --host-us 250 \
  --stream-hz 250 --require-fit
```

Under those assumptions, the round is 3,220 µs and the idealized no-loss delivery
bound is 4,114 µs with no queued predecessor. One fragment is transmitted per
zone window. The bound includes up to one round of waiting, additional rounds
for the specified backlog, transmission/setup and specified host overhead. It
assumes common timing and prompt scheduler/adapter calls. Service is approximately
310.56 fragments/second per zone; a sole 250 Hz stream uses 80.5% of that service.
At a specified rate at or above service capacity the tool withholds its no-loss
bound (`null`) and `--require-fit` exits 2. This requires positive capacity
headroom; equality is deliberately rejected even under ideal timing. A fragment
that cannot fit also has no bound. The first BURST announcement must finish
strictly before the original deadline. The calculator conservatively requires
the fragment/copies to fit that base window, even when BURST extends the round;
it does not model earlier separate announcements or in-progress PHY holds.
A single-band bound in dual-band
output applies only to the primary copy, while the separately named dual-band
bound covers both copies.

The temporary rendezvous/collision model explored unsynchronized schedules and
clock drift/jitter. It showed that slot fit alone cannot establish reliable
rendezvous or channel access. Its loss figures depend on hypothetical channel
plans and are not forecasts for NOVA-LINK hardware. The calculator does not
model collisions, retries, interference, propagation, capture effect, clock
recovery, regulatory duty-cycle limits, or actual RX/TX/band turnaround.

Shared RF timing/MAC/frequency selection, authentication/session epochs, physical
PUSH acknowledgments/credits, empty/error/STATUS/PING response layouts, remote
configuration/reset, per-zone RX reservation, PHY drivers and vendor SDK builds
remain protocol or board work. Dual-band reliability and sub-5 ms delivery remain
unverified targets; see [protocol decisions](Protocol_Decisions.md) and
[roadmap](Development_Roadmap.md).
