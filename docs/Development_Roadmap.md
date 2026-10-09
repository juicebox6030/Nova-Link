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
- [x] Generation handles rejecting retired IDs and guarded logger reentrancy
- [x] Self-origin receive rejection
- [x] Framed transport encoding, decoding, incremental parser, PUSH/PULL flow
- [ ] Application-specific fragmentation/reassembly for messages over 100 bytes
- [ ] Live INI configuration loader and host CLI for applying configuration
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
- [ ] Vendor SDK builds, flashing, and hardware validation

## SDK and offline development

- [x] Strict C99 CMake build, installation, and installed-package consumer check
- [x] ESP-IDF component definition (vendor SDK build remains unverified)
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
- [ ] DMX/RDM, audio, OSC, and synchronization plugins with concrete requirements

## Work that needs physical validation

Physical SPI framing and electrical timing, interrupt behavior, RF channel
switching, dual-band scheduling, airtime/collision behavior, range, interference,
and the sub-5 ms latency target cannot be verified by this simulation. They remain
separate acceptance work. No packet captures or physical-link tests are required
for the completed core work above.

## Next milestone: direct Multiverse TX/RX at 2.4 GHz

Target: receive from a Multiverse Transmitter and transmit to ETC ColorSource V fixtures using the CC1352R directly. See the [bench plan and protocol questions](Multiverse_2_4GHz.md).

- [x] Portable DMX level framing and software TX/RX loopback
- [x] RF capture log format, analyzer, and validation checks
- [ ] Confirm the CC1352R board, SDK, and transmitter variant
- [ ] Verify the existing transmitter-to-fixture reference link and record settings
- [ ] Build and flash receive capture firmware for the selected board
- [ ] Establish the actual PHY, framing/integrity fields, and hopping behavior
- [ ] Reconstruct received DMX levels and compare with known input
- [ ] Implement Multiverse RF TX and verify fixture output/reacquisition
- [ ] Integrate verified RF TX/RX with ESP32 host/plugin API
- [ ] Implement and validate RDM independently

Software checks do not establish Multiverse RF compatibility. Native NOVA-LINK fragments are a separate wire format.

