# NOVA-LINK software architecture evaluation

Timestamp: **2026-10-22T12:31:18-05:00 (America/Chicago)**.

Requested by the owner after discussion of what was built, how it works, and its major design wins and weaknesses. This is an engineering assessment, not a full defect audit or an approved redesign.

## Scope and evidence

The software discussion examined revision `ebfb7c3062903b1b33b98ce41f3fba136b2b595c`, including public host/radio APIs, architecture, protocol decisions, plugin DMX encoding, roadmap, and validation records. A fresh GCC Debug configure/build and CTest run at that revision passed **53/53 tests** in `/tmp/nova-link-status-build` (13.73 seconds of CTest execution). No boards, physical links, or RF interoperability were tested. Historical Release, sanitizer, and vendor build results are recorded in [Validation.md](Validation.md); they were not rerun for this evaluation.

At writing time, the checkout had advanced to `78ed438560702beb38ba36938ed613502a42a1be`, with concurrent hardware edits. This assessment does not validate those changes. The newer compact product direction removes the ESP host in favor of one TI wireless MCU; see the [hardware design](hardware/DMX_Dongle_and_Power_Barrel.md) and [decision index](../DECISIONS.md). The two-processor path below describes the SDK reference architecture, not a requirement for every product.

## Assessment

The portable software engineering is substantially more mature than the wireless system design. The SDK has careful ownership, bounded resources, and meaningful failure simulation. The largest risk is sequencing: considerable infrastructure has been built before establishing the physical transfer, RF timing, and interoperability contracts on which a deployed system depends.

## What exists and how it works

There are three distinct bodies of work:

- The installed native C99 SDK: host lifecycle, local zone claims, message routing, codecs, sequence tracking, queues, scheduler, and transport/service plugins.
- The DMX/Multiverse behavior model: full/delta lighting updates, chunking, atomic receive reconstruction, immutable retries, session binding, and recovery. Its native plugin encoding is a model format, not verified commercial Multiverse encoding.
- The [extended prototype](../experimental/extended/README.md): a separate API and wire format exploring discovery, segmentation, and CRC-protected framing. It cannot be linked together with the native stack because symbols overlap.

A native application plugin claims a zone and submits up to 100 payload bytes. The host adds origin, zone, flags, and an eight-bit sequence. In the reference split-processor path, a transport sends a framed PUSH through an asynchronous SPI backend to a radio queue. The scheduler exposes transmission windows; a future physical RF adapter must perform transmission and completion handling.

RX reverses that path: physical adapter, radio deduplication and RX queue, PULL transfer, host deduplication, then plugin dispatch. PULL uses adapter-local revision tokens to retain queued data until ownership transfer is committed. These tokens are not wire acknowledgments. Calls are serialized by the application's event loop; core storage is fixed or caller-owned.

See [Architecture.md](Architecture.md) for component boundaries and [Protocol_Decisions.md](Protocol_Decisions.md) for authoritative format details and limitations.

## Design wins

1. **Explicit ownership and backpressure.** Immutable pending transfers, retry-safe receipts, stale-token rejection, and shutdown vetoes address common causes of intermittent embedded failures. Local acceptance, RF completion, and peer acknowledgment are correctly distinguished.
2. **Useful portability boundaries.** Host, codecs, queues, scheduling, and physical adapters can be exercised separately. Virtual SPI joins real production backend/slave logic rather than replacing the whole path with a simplified mock.
3. **Sensible lighting-state recovery.** Atomic frame publication prevents partial DMX states from reaching consumers. Periodic FULL updates repair missed DELTAs, while pending chunks remain frozen as newer source snapshots arrive.
4. **Bounded resource behavior.** No core heap allocation or hidden threads; congestion is visible through status and queues rather than unbounded memory growth. This is valuable for constrained MCUs, although target memory and timing budgets still need measurement.
5. **Failure-oriented checks and honest claims.** Tests cover disconnect, congestion, duplicate delivery, uncertain outcomes, restart, and simultaneous traffic. Documentation distinguishes model results, vendor compilation, and physical evidence.

## Major weaknesses and unresolved design risks

### Physical contracts lag the abstractions

Native byte-level PUSH acceptance, empty/error responses, transaction boundaries, GPIO behavior, and shared RF timing are unresolved. Virtual drivers can communicate local outcomes through C interfaces that do not yet have an established physical equivalent. This is an integration risk, not proof that the interfaces are unimplementable. Prove how each promised outcome is obtained on hardware before freezing the adapter contract.

### Header compression imposes operational limits

Three origin bits permit only eight identities. Eight-bit sequence comparison becomes ambiguous after large skips or wraparound; native sender reboot recovery needs external session coordination. There is no native wire session epoch. These can be acceptable constraints for a deliberately small controlled network, but are restrictive for a general event SDK. Additional header bytes should be weighed against measured airtime, capacity, and recovery requirements rather than presumed too expensive.

### A local scheduler is not a radio rendezvous protocol

Ascending zone rounds are deterministic locally. They do not establish clock synchronization, common subscriptions, channel agreement, or recovery after missed control traffic. BURST requires receivers to hear an extension announcement before their original slot closes. Bounded extensions improve local behavior but do not resolve missed-announcement recovery. Synchronization and channel access are feasibility gates for the wireless design.

### Native integrity and framing remain incomplete

The native fragment and transport envelope add no checksum. Length/command checks cannot detect arbitrary corruption, and a plausible damaged length can consume subsequent frames. The DMX model's CRC does not protect arbitrary plugin payloads. Verified PHY integrity and physical transaction boundaries may supply some protections; document and test their exact scope before deciding whether transport integrity must change.

### Two incompatible stacks create maintenance debt

The extended prototype explores features absent from the SDK, but retaining both indefinitely risks duplicated fixes and uncertainty about the authoritative API. Decide explicitly which ideas to adopt, which stack to retain, and whether to archive the experiment. Do not silently combine incompatible formats or describe prototype features as installed SDK capabilities.

### State updates and reliable messages need distinct contracts

Latest-per-stream coalescing is suitable for self-contained snapshots, not arbitrary commands or fragment groups. The shared RX FIFO also permits a busy stream to consume capacity needed by others. Bounded queues do not guarantee fairness, delivery, or deadlines. Define intended traffic classes and required service guarantees before expanding application plugins.

## Recommended next work, not newly approved decisions

Pause broad software feature expansion long enough to prove a narrow physical data path and recovery behavior. Select the actual product architecture first: use a host/SPI/radio path only where the product retains that split; for the compact single-MCU product, validate its direct DMX/radio path instead.

Acceptance should include exact complete DMX output, queue saturation behavior, explicit transfer outcomes, disconnect recovery, sender/receiver reboot recovery, measured memory use and latency, and a documented integrity boundary. For Multiverse interoperability, first establish the transmitter-to-fixture reference link and independently obtained capture evidence; preserve the repository's clean-room requirements. Hardware use on `ltpshop-board` requires its shared lease.

Use measured results to settle identity/session encoding, transport integrity, timing/rendezvous, and acknowledgment policy before treating them as stable. Do not equate a passing model, a compiled image, or a PHY candidate with an interoperable RF product.

Future agents should read current decisions and hardware records before acting: this dated evaluation preserves reasoning and evidence, while newer owner decisions may supersede its assumptions. Record any adopted design change in `DECISIONS.md` in the implementation commit. This document itself adopts no wire format or hardware change.
