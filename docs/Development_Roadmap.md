# Development Roadmap — NOVA-LINK

The portable core can be exercised entirely on a development machine. Checked
items below describe software implementation and offline validation, not board
readiness or over-the-air performance.

## NOVA API / host

- [x] DataFragment structure, validation, and explicit serialization
- [x] Payload to fragment and fragment to payload (up to 100 bytes)
- [x] Zone claim table, exclusive/read-only rules, release, and active-zone mask
- [x] Structured access, lifecycle, transport, and receive logging callbacks
- [x] Zone 0 shared access and management flag propagation
- [x] Plugin payload send with backpressure and per-zone sequence counters
- [x] Payload receive with per-stream duplicate/stale rejection and dispatch
- [x] Plugin startup, failure rollback, tick hooks, and shutdown cleanup
- [x] Uniform named modules, declarative claims, service lookup and dependencies
- [x] Unordered manifests with transactional startup and dependency-safe shutdown
- [x] Transport and logging services using the common plugin lifecycle
- [x] Generation handles rejecting retired IDs and guarded logger reentrancy
- [x] Self-origin receive rejection
- [x] Framed transport encoding, decoding, incremental parser, PUSH/PULL flow
- [ ] Generic message fragmentation/reassembly beyond the DMX application format
- [x] DMX-specific native segmentation/reassembly for complete 512-slot frames
- [x] Configuration service with schema-validated INI buffers and offline host CLI composition
- [ ] Live configuration reload with ownership-safe drain/restart policy
- [ ] Remote zone-claim discovery/coordination and origin-ID assignment
- [ ] OTA/dynamic plugin loading and any actual runtime memory isolation

## NOVA-LINK / radio core

- [x] Shared packet structure and codecs
- [x] PUSH enqueue and PULL receive responses in software
- [x] Bounded per-zone TX queues and shared RX queue
- [x] Clock-driven rotation of active zones
- [x] Metadata injection after a data-zone round, only while requested/pending
- [x] Burst extensions bounded to at most one additional base slot, including current RX holds
- [x] TX preparation applying current holds to late or subsequent BURST fragments
- [x] Two-phase PULL ownership with aborted-transfer retry and stale-commit protection
- [x] Per-(origin, zone) deduplication with wrap and explicit restart handling
- [x] Congestion, duplicate, stale, and accepted-packet statistics
- [ ] Define PING/STATUS response layout and transport acknowledgment/error semantics
- [ ] Define shared RF timing/synchronization and a frequency/priority table
- [ ] Choose PHY/CRC settings, regulatory profiles, retry policy, and band arbitration
- [x] Optional latest-value RX coalescing per stream with stale PULL protection
- [ ] Per-zone RX fairness/reservation policy
- [ ] Session epochs, remote restart/reset, and authentication/replay policy
- [ ] Vendor-specific RF TX/RX adapter and asynchronous completion handling
- [ ] ESP32 SPI master and CC1352R SPI slave/GPIO adapters
- [x] Portable asynchronous SPI backend service and complete-frame native slave adapter
- [x] Reusable virtual SPI driver joining both adapters with deterministic faults
- [x] Vendor SDK compile/link checks for the documented ESP32-S3 and CC1352R targets
- [ ] Firmware flashing, hardware execution and physical validation

## SDK and offline development

- [x] Strict C99 CMake build, installation, and installed-package consumer check
- [x] ESP-IDF component and ESP32-S3 example compiled with selected ESP-IDF v5.5.1 baseline
- [x] CC1352R native project compiled/linked with SimpleLink 7.41.00.17 and TI Arm Clang 3.2.0.LTS
- [x] Doxygen public API generation
- [x] Golden packet vectors and exhaustive header/payload-size codec tests
- [x] All 65,536 previous/current sequence pairs
- [x] Deterministic malformed/noisy byte-stream parser exercise
- [x] Lifecycle failure, access conflicts, reentrancy, queue overflow, and retry tests
- [x] Complete plugin-to-plugin simulation with duplicate bands and sequence wrap
- [x] Offline JSON/JSON Lines inspection tool and CLI tests
- [x] Local GCC Debug/Release, sanitizer, freestanding, docs, and packaging checks
- [x] Counter example plugin with application-owned payload encoding
- [x] Offline RF airtime, slot fit, backlog, sequence-horizon, and assumed dual-band budget tool
- [x] Installed counter and DMX/Multiverse-model plugins with runnable manifests
- [x] Standalone plugin starter generator and installed-SDK CMake template
- [x] Deterministic transport delay, disconnect, congestion and restart scenarios
- [x] Reusable plugin conformance harness with explicit optional-capability reporting
- [x] Installed deterministic fault backend and generated transport-test integration
- [x] Capture observation service using the existing JSONL schema and a compile-only ESP32-S3 project
- [x] Installed developer-only virtual SPI target and paired counter/DMX simulation
- [x] Simultaneous two-way 512-slot DMX through production ticks and paired virtual SPI
- [x] Actual SPI service/transport reusable conformance adapters with all seven cases
- [ ] RDM, audio, OSC, and synchronization plugins with concrete requirements

## Work that needs physical validation

Physical SPI framing and electrical timing, interrupt behavior, RF channel
switching, dual-band scheduling, airtime/collision behavior, range, interference,
and the sub-5 ms latency target cannot be verified by this simulation. They remain
separate acceptance work. No packet captures or physical-link tests are required
for the completed core work above.

## Extended protocol experiments

`experimental/extended/` contains a separately tested implementation of CRC-8
link framing, metadata/peer discovery, segmentation, INI loading, remote zone
claims, and multi-node RF simulation. These features are implemented in that
prototype; unchecked SDK features above still require an integration decision.
The APIs export overlapping symbols and the link formats differ, so applications
must select one stack. The prototype is built by default but excluded from SDK
installation. See its [guide](../experimental/extended/README.md).

## Next milestone: direct Multiverse TX/RX at 2.4 GHz

Target: receive from a Multiverse Transmitter and transmit to ETC ColorSource V fixtures using the CC1352R directly. See the [bench plan and protocol questions](Multiverse_2_4GHz.md).

- [x] Portable DMX level framing and software TX/RX loopback
- [x] RF capture log format, analyzer, and validation checks
- [x] Portable normalized TX/RX engine with full/delta chunking and atomic reconstruction
- [x] TX completion tokens, immutable retries, coalescing, and periodic full resync
- [x] RX integrity/filter/sequence checks, assembly deadlines, holdover and loss status
- [x] Explicit session binding and duplicate rejection after link expiry
- [x] Synthetic byte codec, fault-injection emulator, and offline C-engine replay
- [x] Labeled-capture byte-distribution comparisons for candidate offsets
- [x] Analyze published Multiverse transmitter/receiver firmware; record candidate PHY modes, SHoW ID/hop hypotheses, and capture controls ([findings](Multiverse_Firmware_Findings.md))
- [x] Installed host/adapter API and hardware-independent integration checks
- [x] Native host/module plugin, 72-slot payload chunks, full TX/RX path and loss recovery
- [x] Record SDK/toolchain baselines for documented ESP32-S3/CC1352R targets and 5911 transmitter reference
- [ ] Record actual development-board products, revisions and deployment pin mappings
- [x] Offline board-adapter ownership and capture handoff checklist
- [ ] Verify the existing transmitter-to-fixture reference link and record settings
- [ ] Build and flash receive capture firmware for the selected board
- [ ] Establish the actual PHY, framing/integrity fields, and hopping behavior
- [ ] Reconstruct received DMX levels and compare with known input
- [ ] Implement Multiverse RF TX and verify fixture output/reacquisition
- [ ] Integrate verified RF TX/RX with ESP32 host/plugin API
- [ ] Implement and validate RDM independently

Software checks do not establish Multiverse RF compatibility. Native NOVA-LINK fragments are a separate wire format.
