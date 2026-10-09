# Offline validation record

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
The GitHub workflow covers GCC, Clang, ASan/UBSan, installed consumers, the
standalone prototype, Python 3.11/3.14, and both API references. Hardware,
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
