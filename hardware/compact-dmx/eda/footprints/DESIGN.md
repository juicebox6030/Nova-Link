Current update: [five RF substitutions and remaining switch datum](REPLACEMENT-PASS.md) supersedes the earlier six-provisional counts below. Earlier sourcing history retained.

# DMX prototype protection, termination and partial footprint capture

Current follow-up: [all37 assignments and remaining approvals](COMPLETION.md).
Parent recovered the official PCM12 drawing and verified Active lifecycle status;
its mounting-row gap differs from the provisional footprint by0.28mm. See the
[switch verification receipt](pcm-parent-verification.md). Historical retrieval
failures below do not describe current source access.

2026-10-22. This pass closes the **prototype protection basis and electrical termination capture**, not product release. The follow-up now assigns all37 physical components; six source-approval gates remain. Power and CAD are unchanged. The former requirement to solve an unspecified2/4kV bus surge before capture is withdrawn. No new surge target is selected.

## Protection basis

[TI ISOW1412 SLLSF86D, August2026](https://www.ti.com/lit/ds/symlink/isow1412.pdf) §6.2 specifies±8kV IEC61000-4-2 contact discharge for bus pins relative to GND2 and across the barrier to GND1. This is component capability under the manufacturer's conditions, not a tested assembled-product ESD claim. The part also presents1/8unit-load receiver impedance (§11.2); the headline256nodes is not an assertion about this product's complete DMX network.

[TI's ISOW1432 surge explanation](https://e2e.ti.com/support/isolation-group/isolation/f/isolation-forum/1219957/isow1432-surge-voltage-test-condition) distinguishes isolation-barrier surge from surge applied to bus pins. The discussion's TIDA-00731 external network is relevant if an explicit bus-surge requirement is later adopted; it is not needed merely to acknowledge the existing ESD rating. No external TVS is fitted in this prototype. SM712 alone is not accepted as a coordinated surge clamp and is removed from the active BOM. ADM2795E plus new isolated power is not selected.

Route the pair and its local return on the isolated side with short entry paths. Keep GND_ISO and GND_USB copper, vias and test access separate; do not use a shield/chassis shortcut to bridge them. Cable/connector shell treatment, test points, enclosure discharge paths and system ESD testing remain engineering gates. No quantified system surge, EFT, continuous fault or mains-miswire immunity is claimed.

## Manual termination

S_TERM is C&K PCM12SMTR SPDT. Official [PCM datasheet revised2025-03-14](https://www.ckswitches.com/media/1424/pcm.pdf), pp1–2, specifies0.3A at6VDC,70mΩ contact resistance,10000electrical cycles,−40..85°C. Position1 joins1–2; position2 joins2–3. Here common2 is DMX_P, throw1 is isolated NC, throw3 feeds R_TERM1/2, both240Ω to DMX_N. Assembly and shipping position1 is **OFF**. This is a latching mechanical switch, not a spring-return contact or automatic POR-off function. It retains the user's position without power. No GPIO controls it; any electronic mode control would be a separate hardware revision.

R_TERM1/2 are Vishay CRCW1206240RFKEA,240Ω1%100ppm/K,0.25W each at70°C. [Vishay20035 revision2026-04-14](https://www.vishay.com/docs/20035/dcrcwe3.pdf), pp1/3/4/11, supplies ordering, rating/derating and reflow pads. Two parallel resistors give120Ω nominal and distribute heat. `termination-budget.json` computes worst-case with both resistors at−1% and an additional conservative0.65% temperature excursion to85°C:118.02Ω; at6V differential,50.84mA total and0.15252W per resistor. Linear70→155°C derating permits0.20588W each at85°C. This uses source resistor rating, not measured enclosure temperature. At5V differential each dissipates0.10591W.6V is the switch's rating boundary, **not extra fault headroom**. Do not use this branch for higher differential fault voltage or hot-switch an unknown powered bus.

Common-mode voltage shifts both floating switch terminals together; the6V contact rating is differential, not a GND_ISO common-mode limit. All switch contacts and mounting lands stay in the isolated island. Do not connect the metal case to logic ground or expose a conductive access path across the isolation barrier. The500VAC component dielectric specification is not a certified user-accessible barrier design. A polymer tool-access recess and assembled-system test are required.

Enable only at the physical end of a DMX line. Two enabled ends produce60Ω nominal total; adding this switch in the middle of an already terminated line produces40Ω and can overload the driver. Existing driver54Ω test conditions do not authorize a third terminator. RDM changes direction, not the need to maintain the same line termination. During a fixture service disconnection, inspect controller/adapter termination; never assume the absent fixture still terminates the line.

## Current footprint assignments and source limits

`assignments.json` maps all37 physical components to actual parsed KiCad lands and exact schematic values. Three interface symbols remain intentional nonphysical boundaries. Fifteen footprint files parse;14 have independent numeric checks covering109numbered pads.31component assignments are source-backed;5RFtuning assignments and the parent-owned switch remain provisional. Prior receipts are historical evidence, not current counts.

`generate.py` regenerates the original lands and invokes `extract_ti_lands.py` and `generate_support.py`. `verify.py` runs with the existing Flatpak KiCad Python and checks every exported physical component's pad-number set, footprint property and selected MPN/value. No body-only footprint substitution is used. See `COMPLETION.md` for exact extraction and source caveats. NC antenna islands and the separately documented provisional all-layer clearance region remain unchanged. No routed PCB or proven isolation/antenna placement is supplied.

## Parent placement constraints

U5 lands occupy11.8mm across rows and12.03mm along the lead row. A90° rotation may help position isolated bus pins17–20 toward the lead entry, but does not reduce the isolation barrier requirement. Existing nominal isolatorx8 versus leadentryx72 forces a long isolated corridor if retained; reassess placement/entry rather than route GND_ISO through logic/RF copper. No arbitrary creepage rating or fabricated routed solution is supplied. Keep termination resistors and S_TERM on the isolated side close to the bus entry; allow two4.1×2.3 resistor courtyards plus the switch/access lane. Actual packing and temperature remain unknown. Parent must model this before any enclosure/PCB release; no CAD moved here.

Before/after source hashes are in `validation.json`; the power sheet stayed unchanged during this pass. Changes to owned MCU/DMX hashes are intentional. Full-package acceptance is for parent to rerun after power work settles.
