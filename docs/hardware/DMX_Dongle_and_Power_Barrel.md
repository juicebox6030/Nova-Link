# Compact DMX sidecar and rotary USB power barrel — revision C architecture

2026-10-24 · **Rev C electrical direction / Rev B mechanical baseline. NOT released build-to-print.**

**Latest source requirement:** normal operation requires a5V USB-C source
advertising at least1.5A, including the NOVA-LINK barrel. The retained Rev C
and completed500mA separated candidate predate this approval; neither implements
the new CC qualification. A compact qualified-source revision is in development.

**Latest buffer development basis:** Eaton HV1625-2R7256-R,25F, with a local
PCB aperture and lowered cradle inside the existing98×34×24mm case. Independent
geometry and energy checks support a conditional16.34s aged screen. An editable
PCB/lead/retainer prototype is checked. Protection parts now have a merged
power schematic and conditional sidecar placement; full integration is open. The separate protection prototype reduces the
conditional hot-fuse screen to13.26s; its interruption bounds and fit are open.
This is not measured runtime or a released substitution.

**Power acceptance remains open.** The static source-good defect and omitted
charge hysteresis are corrected in the prototype capture. Cold-cap startup,
transient timing and measured runtime remain unproved; the status signal alone
is not authorization to install firmware. See section6 for evidence and next work.

**Barrel architecture blocked for production:** IRM20 inside the proposedØ43mm
bore does not meet the published installation construction. The bounded source
check found no explicit reduced-clearance alternative. The documented lateral
allowance alone needs47.7mm. The saved carrier andØ66mm rotary prototype remain
geometric evidence, not an accepted complete barrel. A bounded comparison found no supported compact construction for the two
alternative families. The next engineering direction is a stationary source pod
respecting the published spacing and a12V isolated internal bus. The first pod
allocation is330×89×72mm and fails the compactness objective. A270×89×72mm
shortened comparison retains eight physical interferences and a disconnected
contact. The subsequent CIR-R1 repair incorporates both frozen S12 boards and
closes its bounded nominal interface screens at a trialØ70mm collar. Its
275×91×74mm assembly still includes generic connector blanks and an unfinished
source carrier; it is a comparison, not an accepted compact product envelope.
The subsequent CYL-R2 constructs a cylindrical source bay and corrects the
film/finite-corridor failures; matched classic planning is302.8×77×77mm, not a
finished product. CAF-R2 provides positive closure-driver clearance while
preserving the screw seats; this local assembly fix does not qualify the open
ports. Source mounting/insulation, neck joints, fuse/terminals and connector
ends remain incomplete or unapproved. S12-R1 uses32×26mm rotating and
24×16mm stationary boards; USB fault-energy protection and production
qualification remain unresolved. USB output remains
5V/1.5A, and AXIAL-R1 must not be powered at12V.
The completed two-reference source screen establishes no smaller complete
replacement. TIDA-01560 remains a conditional12V reference only: its66×50mm PCB
and12.4mm transformer height do not bound the assembled enclosure, and its
1.125A output does not cover the retained overload calculation.

This replaces revision A's long straight dongle and ESP host architecture. One
**CC1352R1F3RGZ** handles the native NOVA-LINK radio and basic DMX/RDM management.
USB-C is now **power only**. Management uses wired RDM and native NOVA-LINK wireless;
firmware delivery over the DMX connector targets ANSI E1.37-4–2026 File Transfer
Control. The onboard USB-UART bridge and USB-data recovery candidate are superseded.
No firmware work, hardware operation, purchase, certification or runtime measurement
is represented by this package.

[Revised visual](dmx-hardware-concept.html) · [BOM/AVL](dmx-hardware-bom.csv) ·
[Editable CAD and exports](../../hardware/compact-dmx/) ·
[Dimensioned drawing set](../../hardware/compact-dmx/exports/manufacturer-drawings.pdf) ·
[Partial electrical sheet](../../hardware/compact-dmx/eda/dmx-interface.kicad_sch)

## 1. Scope, corrections and acceptance boundary

Owner correction, verbatim:

> no ESP needed if it saves us space, just the TI chip for basic things, RDM management of the product is acceptable as well as via USB if recovery is needed. Ideally, the product sits more flush up against the device. Please have ASTRA LOW subagent take the rough designs and create something that could actually be produced by a manufacture. We want all of these things to be as small and compact as possible, sitting as close to the fixture as possible. We also want the center parts where the USB is to be able to rotate at least 90 degrees, up to 180 ideally so that the power is never fully obstructed. this needs to be durable and locking.

Fixture reference correction, verbatim:

> design to fit a varity of fixture across multiple manufactures. only use products that you can have a subagent go and fetch its expanded view / 3d renderings

Latest owner correction, verbatim:

> Thats fine, we can skip usb interop and just leave wireless AND wired RDM as the main path. The key is going to be how do we flash updates to the device over the DMX port

Latest RF-band decision, verbatim:

> 2.4 GHz plus US 915 MHz

Latest USB-source decision, verbatim (answer to requiring normal operation from
a5V USB-C source advertising at least1.5A, including the NOVA-LINK barrel):

> Require 1.5 A USB-C (Recommended)

This supersedes the earlier500mA engineering basis and the prior withdrawal of
an unanswered source question. Detect the source advertisement in hardware;
normal operation and firmware-install source-good must not be authorized by
VBUS voltage alone.5V remains the supply voltage; higher PD voltages are not
part of this decision. Low-power attachment detection and cap ride-through
must be distinguished from normal externally powered operation.

Both bands are hardware requirements for the compact CC1352R design. Matching,
antenna architecture and placement must support both; prior single-band space
assumptions cannot establish fit. Frequency plans, PHY, channel switching and
regulatory power limits remain later engineering, not implied by this choice.

Settled: hardware only; native NOVA-LINK; TI-only application processor;
**2.4GHz plus US915MHz RF hardware**; isolated
DMX; USB-C power; **10–30 s buffer target**; powerCON, TRUE1 and NEMA 5-15 barrel
variants; wired RDM and wireless management, firmware updates through DMX/RDM;
durable locking rotation. Factory debug/recovery pads remain; no onboard USB data.

The CAD is a **dimensioned packaging and mechanism development assembly** with real
analytic solids for custom parts and explicitly labeled supplier envelopes. It
can support quotations and mechanical prototype discussions. It is not an approved
injection mold, a fully detailed harness, a routed PCB, or a safe mains build order.
Individual STEP files are not permission to fabricate/energize a mains assembly.
The partial EDA sheets are genuinely pin-connected: one covers the DMX isolator,
its decoupling and default states. A separate historical USB recovery candidate
is superseded and remains disabled by an open qualification link. Revision C power/buffer/latch/POR/reset/staging/service capture now exports
78 components and74 nets with zero KiCad ERC violations. These are separate
partial sheets. MCU support and the dual-band frontend are now captured, while
antenna tuning/coupling, full interconnection, footprints and PCB DRC remain open. [Current circuit and limits](../../hardware/compact-dmx/eda/power-service/DESIGN.md).

Only source-backed manufacturer 3D/exploded assets qualify fixtures for the fit
matrix. The separate source-fetch task owns `hardware/fixture-fit/` and
`docs/hardware/fixture-reference-manifest.md`; this package does not assert fit to
ETC or any other fixture before that evidence is integrated and geometry checked.
No older ColorSource CAD is substituted for ColorSource V.

The completed [fixture reference manifest](fixture-reference-manifest.md) now records
**four models / three manufacturers**: ETC ColorSource Spot V19, ETC ColorSource
Fresnel V, CHAUVET Ovation E-910FC and GLP impression X5. Official3D assets were
fetched; connector pitch/recess and installed assembly collisions remain unmeasured.
Spot V has an internal CAD timestamp/identity warning. GLP includes STEP with mm
units, but no fit measurement is represented here. This meets reference-source
breadth, not geometric or physical fit acceptance.

## 2. Fixture-hugging dongle geometry

Dimensions below retain the **Rev B mechanical baseline**, with Rev C SPI flash
replacing the former bridge envelope. This is not a smaller or fully placed
working PCB: power/cutoff circuits, passives and RF still need actual placement.

Use an **intact Neutrik NC5FRX** right-angle 5-pin female connector. Retain its latch,
insert, chuck and boot; do not cut the boot off to make an attractive envelope.
A short shielded DMX harness enters a screw-closed sidecar beside the connector,
parallel to the fixture back plane. A fixture-specific insulating saddle/tether
supports sidecar mass; the XLR latch is not the sole load-bearing mount.
The NC5FRX drawing gives **41 mm axial height, 72.9 mm overall outlet extent,
20.3 mm body diameter**, with a 15.8 mm mating nose and 19 mm nose shoulder.
These are unmated drawing dimensions, not protrusion from every fixture panel.
[Neutrik drawing](https://www.neutrik.us/media/8251/download/nc5frx.pdf?v=1).

**Datum F:** reference fixture mating plane `z=0`, connector axis `x=y=0`.
Positive z points away from the fixture. Sidecar long direction is x.
For conservative comparison the mating tip is at F; actual insertion reduces the
stand-off but recess and latch geometry can increase it. Do not subtract an
invented insertion depth.

| Feature | Proposed dimensions / location, mm |
|---|---|
| Sidecar shell | 98 × 34 × 24; x=0…98, y=20…54, z=5…29 |
| Internal cavity | x=2…96, y=22…52, z=7…27; 2 mm nominal walls |
| PCB | 90 × 28 × 1.0; x=4…94, y=23…51, z=10…11 |
| Intact XLR reference envelope | x=−10.15…62.75, y=−10.15…10.15, z=0…41 |
| Assembly union, excluding finger/cable access | 108.15 × 64.15 × 41; reference, NOT universal installed fit |
| Finger approach reserve | x=−25…−7, y=−17…17, z=0…34; 18 mm approach, verify actual latch travel |
| USB plug approach | outward +y at x=37…48.4; reserve 25 mm straight plug and 15 mm bend zone beyond shell |
| DMX harness | selected cable OD 4–5 mm within NC5FRX's 3.5–8 mm range; 50–80 mm free routing target, supplier bend radius governs |
| Antenna end | x=78…96, y=22…52, full cavity height; no metal/cap/ground/screws |

A 41 mm reference protrusion is substantially shorter than revision A's ~110 mm
straight length; it occupies more area along the fixture face. Do not hide that
tradeoff. Nearby power plugs, vents, handles and yoke motion must clear the complete
assembly **and finger/USB approaches**, not just the housing. Five selectable NC5FRX
outlet positions support assembly orientation; these are not a user-adjustable
live swivel. [NC5FRX product](https://www.neutrik.us/en-us/product/nc5frx?c=audio).

The shell's antenna end must project beyond the relevant fixture metal edge or
meet a measured detuning criterion. Reserve **15 mm minimum external metal gap as
a provisional test condition**, not a validated antenna specification. If geometry
cannot meet it, rotate the assembly, use a fitted insulating saddle, or reject that
fixture fit. Antenna type/layout and tune are not yet selected. No claim of
universal flushness or reliable RF against arbitrary metal is made.

### Component packing and tolerances

The generator checks pairwise intersections of the major allocated packages/zones;
actual PCB routing and complete passives placement are outstanding. Supplier models
are simplified maximum envelopes, never vendor-accurate mechanical surfaces.

| Item | Checked envelope | Placement / reserve |
|---|---|---|
| CC1352R RGZ | 7 × 7 mm nominal | x62…69/y27…34; additional RF network zone x61…76/y35…43 |
| ISOW1412 DFM | 12.93 × 10.63 × 3.55 max | x8…20.93/y29…39.63, z11…14.55; lands/decoupling region x5…24/y25…44 |
| AT25SF161B-MHB-T SPI NOR | 5.10 × 6.10 × 0.60 max | x52…57.1/y40…46.1/z11…11.6; actual lands/passives and routing still open |
| Eaton HV1325 | Ø13.5 × 28.4 max | x26…54.4; center y30.25/z18.75; lead/forming reserve x54.4…61, not a completed lead/cradle design |
| Hirose CX70M-24P1 | 11.4 × 8.35 × 3.66 envelope | x37…48.4/y45.65…54; 12.3 mm footprint width minimum reserve |
| Power parts | 25 × 6 × 4 allocation | x25…50/y38…44; provisional allocation, not proof all footprints fit |

Package sources: [TI CC1352R §7/package](https://www.ti.com/lit/ds/symlink/cc1352r.pdf),
[TI ISOW1412 DFM0020A](https://www.ti.com/lit/ds/symlink/isow1412.pdf),
[Renesas AT25SF161B package/ordering](https://www.renesas.com/document/dst/at25sf161b-datasheet),
[Eaton HV table](https://www.eaton.com/content/dam/eaton/products/electronic-components/resources/data-sheet/eaton-hv-supercapacitors-cylindrical-cells-data-sheet.pdf),
[Hirose CX70M drawing](https://www.hirose.com/en/product/document?documentid=D52488_en&documenttype=Catalog&lang=en&series=CX).

**Proposed tolerance stack, worst-case arithmetic rather than RSS:** shell outside
±0.20; wall/floor ±0.15; PCB outline ±0.10; board thickness ±0.10; board support
height ±0.10; cap cradle position ±0.20. Cavity width minimum
33.8−2(2.15)=29.5 vs PCB maximum28.1 gives 1.4 mm total lateral float. Cavity height
minimum23.8−2(2.15)=19.5. Corrected boss tops and PCB underside both lie at
z10: intended face contact, zero volumetric overlap. PCB top is z11; package seating
planes rise to z11 and the USB mid-mount envelope starts at z10. A provisional
12.4 ×5.9 mm edge slot removes the PCB volume occupied by that connector; it must
be reconciled with the manufacturer's exact footprint before routing.
The maximum-size15 F cap spans z12…25.5. Nominal PCB clearance is **1.0 mm**;
subtract support/floor .15, support height .10, board thickness .10 and cap
position .20 = **0.45 mm worst-case residual**. Nominal lid clearance is **1.5 mm**;
subtract shell/floor/placement stack .55 = **0.95 mm residual**. These are proposed
manufacturing tolerance allocations, not measured assemblies. Support the capacitor
from its sides/end with an independently retained cradle and lead strain relief;
do not fill the small underside gap with an assumed foam pad. Cradle geometry,
lead bends and restraint remain a detailed-design gate. USB aperture14 ×6 vs connector11.4 ×3.66 leaves at least0.7 mm lateral and0.67 mm
vertical after ±0.3 board-to-shell registration and ±0.3 aperture/part allocation;
confirm actual manufacturer's limits before tooling. Maintain radiused edges R0.5
minimum at cable contacts. Four M2 fasteners/heat-set insert locations are proposed;
insert bore, screw engagement and tightening torque require supplier selection.
PCB holes and support interfaces must follow the CAD revision, not these allocations
alone. Mold draft1–2°, ribs≤0.6 wall, knit lines, inserts and shrink are DFM inputs,
not already present on the analytic RFQ solids.

## 3. Electrical implementation brief

### TI, power-only USB and service connections

One CC1352R remains the application/radio processor. Remove CP2102N, USB D+/D−
routing and the separate USB-enumeration recovery domains from the product.
The superseded recovery candidate remains development history, not active
hardware or evidence of RDM updating. Retain factory cJTAG pads, RESET_N, ground
and VTref; provide a physical service request readable before the application.

| Function | TI DIO / package pin | Requirement |
|---|---|---|
| DMX TX / RX | DIO13 /19; DIO12 /18 | Current partial-capture UART allocation, shared normal/resident RDM use |
| DMX DE request / RE_N | DIO5 /10; DIO7 /12 | Controlled driver turnaround; reset/UVLO gating and receiver default off |
| Isolated supply request | DIO6 /11 | Through captured SYS_READY gate, default off |
| Reset | RESET_N /35 | Supervisor RESET_OK; physical/factory reset asserts supervisor MR |
| Factory debug | TMSC /24; TCKC /25 | cJTAG pads, MR request, ground and VTref |
| Factory ROM UART | DIO12 /18 RX; DIO13 /19 TX | Same UART allocation as DMX; no bridge; factory access must keep isolator disabled |
| ROM backdoor | DIO3 /8 | Factory strap only, distinct from RDM service; CCFG policy pending |
| RDM service request | DIO4 /9 | Hold at reset/power-up for future resident loader |
| External SPI NOR | DIO8 /14 MISO; DIO9 /15 MOSI; DIO10 /16 SCK; DIO11 /17 CS | Partial-capture pin/net allocation; safe defaults captured in power-service |
| Source-good / buck PG | DIO14 /20; DIO15 /21 | Static qualifier corrected; transient/power stability still requires validation |
| Input fault reserve | DIO18 /28, currently NC | Needs power-off-safe interface before connection |

This table reflects the checked MCU-support/dual-feed prototype capture; antenna
tuning, coupling and physical placement remain unqualified. [Pin ledger](../../hardware/compact-dmx/eda/mcu-radio/pin-allocation.csv)
and [capture limits](../../hardware/compact-dmx/eda/mcu-radio/DESIGN.md) supersede
the earlier proposed pin map. Separate sheets use explicit verified aliases;
they are not yet a merged full-product schematic/ERC.

Pin references: [TI CC1352R §7](https://www.ti.com/lit/ds/symlink/cc1352r.pdf) and
[TI ROM serial loader table2-11](https://www.ti.com/lit/an/swra466e/swra466e.pdf).
The ROM loader speaks UART/SPI, **not RDM**. A custom resident flash loader is
future software, programmed at manufacture. An asserted CCFG ROM-backdoor input
would bypass it, so that input must remain distinct from the RDM-service request.
GPIO assignments above are a proposed hardware allocation checked against the
physical package; no finished firmware or CCFG configuration is supplied.

### Dual-band support and antenna limit

The support circuit follows recovered **TI SWRC354 CC1352EM-IPC Rev1.1.0**
with the exact CC1352R1, source-backed supply/DC-DC/decoupling and48MHz/32.768kHz
clocks. Johanson0900PC15A0036001E supplies the2.4GHz/915MHz frontend. The current
prototype connects separate band feeds to **Johanson0900AD47A2450001E**, removing
the preliminary Murata RF switch, its control resistor and common-feed capacitor.
There is one shared radio; switching/scheduling policy is future firmware.
[Sources, pin connections and limits](../../hardware/compact-dmx/eda/mcu-radio/DESIGN.md).

The antenna's five matching components use manufacturer evaluation-board starting
values, not a tuned product match. Its non-feed lands must remain individually
isolated and soldered as the manufacturer specifies. A source-based typical
coupling screen is not a guaranteed inactive-port stress bound; validate powered/
unpowered port loading, mismatch and enclosure effects before RF operation.

The proposed18×28mm PCB end region is **not verified placement**. The antenna's
50×30mm evaluation board differs from this90×28mm board. Preserve the manufacturer
clearance outline, ground transition, two feeds and matching courtyards; a small
chip body alone does not establish fit. The earlier TI38×25mm radiator was too
large for the original18×30 reserve and is not selected. Crystal sourcing/tuning,
antenna efficiency and fixture-metal clearance remain qualification gates.

### Firmware updates through the DMX connector

Target **ANSI E1.37-4–2026 File Transfer Control (FTC)** over ANSI E1.20 RDM.
[ESTA's published-document entry](https://tsp.esta.org/tsp/documents/published_docs.php)
records approval on20 May2026 and describes firmware/file delivery using scalable
RDM buffers. It supersedes older draft-status assumptions. Full standard text,
PID/layout/timing conformance and controller interoperability must be checked
before implementation; no command numbers are invented here.

Proposed future update sequence:

1. Power the dongle through USB-C. For wired service, disconnect it from the
   fixture and use a straight-through five-pin male-to-male service adapter
   between its female XLR and a bidirectional RDM controller's female output.
   This adapter changes connector gender only; pins1/2/3 remain straight through.
   Do not assume a fixture's DMX THRU is a bidirectional/passive update path.
2. Enter service with the physical button at reset, or a controlled application
   handoff. The dongle stops generating DMX and becomes an RDM responder with
   its own persistent UID. There must be exactly one controller on this segment.
   Discover it and query FTC support. Normal console level output alone cannot
   upload firmware; the updater/controller must implement FTC.
3. Transfer the image to external SPI NOR in addressed, acknowledged blocks,
   with retry/progress state and a complete image manifest. Reserve a small
   **AT25SF161B-MHB-T,16-Mbit /2-MiB** NOR for a new image,
   a known-good image and metadata. Its SPI connections/defaults and maximum
   package envelope are captured; PCB placement and partition sizes remain open. Keep the active internal image intact
   while downloading; do not stream directly over the executing application.
4. Verify target hardware/version, image length, integrity and authorized-image
   signature before marking it installable. A resident boot manager installs
   from staging only with adequate stable power, verifies internal flash, and
   launches the application. Journal copy/progress metadata so power loss during
   internal programming can be recovered when power returns.
5. Confirm successful boot; retain a known-good rollback image until confirmation.
   If the application is invalid, the resident recovery loader must still expose
   wired RDM service without requiring the radio/application to run. If the loader
   or configuration is itself damaged, factory cJTAG is the final rescue path.

The same image/staging/verification plan can serve native NOVA-LINK wireless
updates later. Wireless RDM management is an application/gateway function to be
implemented; it is not automatic compatibility with other wireless DMX systems.
No FTC controller software, bootloader, radio update stack or firmware evaluation
is requested or supplied by this hardware task.

### Hardware required for reliable recovery

The existing isolated, bidirectional RS-485 interface can carry RDM data and its
responses. It must receive power and permit controlled DE/RE turnaround in the
resident loader. A recovery state that disables the isolator entirely would
prevent wired rescue. Keep the driver disabled by hardware defaults until the
loader deliberately transmits; suspend ordinary DMX transmission during service.

Reserve a protected/reserved resident boot area, persistent UID/settings storage,
external flash and its SPI interface, physical service/reset input and visible
power-good information. Exact flash-protection/CCFG policy and loader size need
later engineering; do not claim an immutable RDM loader exists in TI ROM.
CC1352R has352KB total internal flash, so two full internal application copies
must not be assumed. [TI's off-chip BIM architecture](https://software-dl.ti.com/simplelink/esd/simplelink_cc13xx_cc26xx_sdk/latest/exports/docs/ti154stack/html/oad-secure/bim-off-chip.html)
is a reference for staged validation/install/factory-image fallback, not an
existing RDM implementation. Its default terminal low-power behavior is not
sufficient for the proposed always-available wired recovery; that needs design.

The10–30 s capacitor is interruption buffering, **not the energy source for a
whole firmware update**. At250 kbit/s and11 serial bits/byte,352KiB alone takes
15.86 s before any RDM overhead, retries, programming or validation. Stable USB-C
power must be present for update/install; interrupted transfers/copies must be
recoverable rather than depending on the capacitor finishing them.

### Retained Rev C power-only USB path — predates the1.5A requirement

The retained capture has separate5.1k Rd resistors, joined VBUS/ground contacts and no data/SBU
connections. TPS2553 plus the selected-input TPS2116 reverse barrier supplies the buffered
normal domain. Its60.4k current-limit resistor gives a calculated389.80–488.21mA
limit range; including switch current, the static input bound is488.35mA.
This uses USB Type-C's power-sinking-device default-current design basis and does
not increase draw at1.5A/3A advertisements. Inrush, source compatibility, reverse
leakage and USB qualification remain untested; this is not certification.

AON supervision, cap/VBUS comparators, POR, independent cutoff latch, buck reset
and DMX power/DE gates are actual captured components. Loaded-cap trip removes
the main domain; cell rebound cannot rearm it without valid VBUS. The16-state
Boolean check does not establish asynchronous timing or rail-ramp behavior.
The service request is a distinct signal from the factory ROM strap. See the
[current circuit rationale, sources and release gates](../../hardware/compact-dmx/eda/power-service/DESIGN.md).

TPS3700 now senses actual converter VIN after the barrier. Its static threshold
envelope and converter-mode checks close the earlier false-good case. At the
assumed4.4V source,1.1W load and stated efficiencies, demand is325.72mA,64.08mA
below the minimum limiter; at the qualified source floor the margin is31.62mA.
These use explicit resistance, sag and load allocations. The startup gate remains
open: the converter precharge current is not guaranteed below the input limit.
Actual load, cold-start, RF/flash peaks and thermal behavior are unmeasured. The
25×6mm power allocation is not proof that this78-component sheet fits the PCB.

### Buffer and DMX

TPS61094 provides3.6V backup followed by TPS62132 fixed3.3V buck. Normal bypass
can put about5V on the intermediate rail; the MCU is supplied after the buck.
The15F/2.7V Eaton HV1325-2R7156-R is charged to2.6V. OSEL17.4k selects3.6V;
ICHG9.53k now selects**25mA**, and VCHG9.53k selects2.6V. MODE is held from the
independent source-derived AON rail when RUN disables EN; MODE low/EN low is
forced bypass, not true shutdown. Startup/decay and reverse paths need tests.
[TI TPS61094](https://www.ti.com/lit/ds/symlink/tps61094.pdf).

**Recharge is slow:** ideal empty-to-full time is1560s (**26min**) nominal. At
+30% capacitance,+2% voltage and−20% charge current, it is2585.7s (**43.1min**),
before soft-start/termination tail. This is a deliberate current-budget tradeoff,
not a measured recharge specification. The quoted current accuracy is specified
at VIN=5V; accuracy at the reduced converter input also needs qualification. Initial
attach or a short recharge interval does not imply the full buffer duration.

Use `t = 0.5 C (Vstart²−Vend²) η / P`. Nominal15F,2.6→1.5V and80% efficiency
yield27.06J, or33.8s at0.8W. The aged estimate uses15×.9×.7=9.45F, low-charge
2.548V and a**1.7V energy floor**, reserving sag/transient margin above the
calculated1.424–1.555V loaded cutoff envelope. The previous calculation yielded13.6167J /1.11W =12.27s,
including10mW supervision, but omitted recharge hysteresis. Subtracting the100mV
maximum hysteresis from2.548V gives2.448V and**11.7282J /1.11W =10.57s**. All load/efficiency/ESR assumptions remain unmeasured;
this is not a guaranteed10s runtime. Both the earlier13.51s estimate and the pre-review12.27s estimate are
superseded. With only0.57s calculated margin, the buffer target remains open. The10–30s brief is a buffering target, not a mandatory30s cutoff.

Measure loaded DMX/RF/flash consumption, cold/aged ESR, converter peak current,
cutoff timing and heat before acceptance. Keep the cell≤65°C at2.6V; hotter
operation requires voltage derating and new calculations. The capacitor powers
the dongle, not the fixture or an entire firmware update.
[Reproducible power budget](../../hardware/compact-dmx/eda/power-budget.json).

Use ISOW1412DFMR in half duplex: Y+A→DMX+, Z+B→DMX−; MODE→isolated ground for3.3 V.
XLR1→isolated common,2→DMX−,3→DMX+;4/5 unconnected. The minimal prototype relies on
the ISOW1412's manufacturer-specified bus ESD capability; no external TVS is
populated. This is not an assembled-product ESD, bus-surge or fault-immunity
claim. SM712 alone is not accepted as a coordinated surge clamp. No additional
bus-surge target was specified by the owner; isolation-barrier surge ratings do
not establish bus-pin surge immunity.

Manual120Ω termination is captured: C&K PCM12SMTR connects two parallel240Ω
Vishay CRCW1206240RFKEA resistors across the bus. Assembly/shipping position1 is
OFF; this latching switch retains its setting without power. At the assumed6V
differential/85°C corner, calculated dissipation is0.153W per resistor against
a0.206W derated allowance. This does not establish enclosure temperature or
fault headroom. The switch land pattern is provisional, with isolated mounting
lands and polymer tool access still to be placed. Enable termination only at a
physical line end after checking other terminators. The DMX EN/FLT input has a
captured1kΩ series resistor; this limits possible contention current but does
not prove brownout behavior. [Circuit, source and footprint limits](../../hardware/compact-dmx/eda/footprints/DESIGN.md).
Default DE low, receiver disabled and isolated supply disabled during reset/fault;
the resident RDM loader must deliberately enable receive/power and controlled DE.
All-layer isolation corridor and creepage must match the final rating; USB ground,
XLR common and connector shell must not accidentally bridge isolation.
RDM turnaround/proxying and native radio transport remain later firmware work.

## 4. Fixed mains core, rotating isolated USB collar

The mechanism rotates **only the USB port assembly** about the barrel's longitudinal
x axis. Connector endcaps, AC/DC module, L/N wiring and **PE stay stationary**.
No slip ring, rotating mains contact or flexing protective-earth conductor is used.
This interpretation lets the user turn a side-facing USB cable out of an obstruction
without turning either mains connector. It cannot guarantee clearance from every
fixture or a cable already pinned against a wall.

| Dimension | Proposed value |
|---|---|
| Fixed body | Ø48 ×142 mm, excluding mating plugs/pigtails |
| Collar | Ø84 ×26 mm at x58…84; end shoulders/lock details can extend to x90 |
| PSU | IRM-10-5,45.7 ×25.4 ×21.5 nominal, x45…90.7; fixed |
| Rotation | ±90° from keyed neutral; nominal stop travel180.57°, acceptance180°±1° |
| Positive index | 13 positions at15° over180°; steel pin at radius29 mm |
| Source | 5 V,1.5 A advertised by TPS25810; complete path/thermal performance unverified |

The larger collar is driven by the cable's bending loop, not unnecessary ESP power.
A smaller **IRM-03-5,37 ×24 ×15 mm,3 W** was considered. It cannot supply a1.5 A
advertisement. Supporting a smaller default-current source would require a changed
USB current/charging contract. Retain the10 W module for this prototype rather than
falsely advertise1.5 A from a0.6 A supply.
[IRM-03 drawing/spec](https://www.meanwell.com/Upload/PDF/IRM-03/IRM-03-SPEC.PDF),
[IRM-10](https://www.meanwell.com/Upload/PDF/IRM-10/IRM-10-SPEC.PDF),
[TPS25810](https://www.ti.com/lit/ds/symlink/tps25810.pdf).

The142 mm body is not a flush plug adapter: use a tether/saddle and short mains
jumper; for NEMA use approved molded pigtails to avoid wall-outlet leverage. Direct
fixture mounting of a mains barrel is not claimed. CAD endcaps are intentionally
**uncut blanks**, pending actual connector flange/terminal/creepage integration.
This is a material build-release gate, not a universal connector mount.

### Compactness assessment — development baseline, not an optimized flush barrel

The Ø84 collar and142 mm core are a development baseline. They have not met the
owner's smallest/flush objective. A bounded clock-spring FPC around the fixedØ48
core is a future investigation: **approximatelyØ60 cassette is only a target, not
a verified complete collar**. A single-layer RA-copper spiral can avoid a tight
reversing U bend, but needs supplier-qualified dynamic construction, tangential
strain relief and retained guides. [Minco design guidance](https://www.minco.com/wp-content/uploads/Minco-Flex-Circuits-Design-Guide-2019.pdf)
and [All Flex guidance](https://www.allflexinc.com/wp-content/uploads/2024/03/Minimum-Bend-Radius-Considerations-in-Flexible-Circuits.pdf)
do not certify this proposed mechanism or its cycle life.

Screening model: ±90° changes wrap count by±.25 turn. Effective radius25…28 mm
requires at least4.42 neutral turns and733 mm active length in the idealized model;
investigate roughly0.8–1.1 m after finite thickness and guide allowances, not a
short ribbon. Two8 mm-wide traces (5 V and return),0.8–1.0 m long, give150–188 mV
loop drop at1.5 A with35 µm copper at20°C, or75–94 mV with70 µm. Dissipation is
0.225–0.281 W or0.113–0.141 W respectively, before termination/controller losses
and temperature rise. The18–20 mm ribbon width also consumes axial space. Thick
copper reduces loss but increases stiffness and winding thickness. No qualified
wire-torsion alternative has been established.

Existing Ø64 index ring and approximatelyØ80 USB radial allocation independently
prevent shrinking the current complete assembly toØ60. Both require repackaging;
the142 mm body length does not shrink automatically. No speculative smaller STEP
is supplied. Rev B's RF endx76 +2 mm separation +18 mm antenna keepout +2 mm wall
totals98 mm; this is an allocation in the old layout, not a minimum Rev C length.
Removing the bridge and repacking power/staging flash requires actual placement.
Minimization and
source-backed fixture clearance remain explicit open acceptance gates.

### Lock, retention and stop design

- Proposed materials: flame-rated PC/PBT fixed core/collar (exact grade to select),
  POM replaceable bushes,304 stainless index ring, hardened17-4PH Ø3 pin.
  Prototype printed plastic is suitable for unenergized fit checks only.
- Two separate bushes ride Ø48.00±.05 journals; boreØ48.20+.05/0 yields0.15…0.30 mm
  diametral clearance. Target axial endplay0.15…0.35 mm using measured shims.
  Opposed screwed retaining shoulders hold the collar; axial load must not rely on
  the spring pin. Retainer screws must remain inaccessible in normal operation.
- Index ring2.00±.05 mm thick,13 boresØ3.20+.05/0 atR29.00±.05,15°±.15 pitch.
  PinØ3.00−.02/0; engaged depth≥1.70 mm after stack; nominal2 mm.
  Recessed captive slider pulls pin axially4.2±.15 mm against8–15 N spring target.
  Release clearance≥.5 mm, including .35 mm endplay and .15 mm guide stack.
  A modeled metal guide sleeve B19, **OD3.80+.05/0, ID3.20+.05/0 ×9 mm**, runs
  x58…67 at R29 through the left cheek and both cassette lanes. The pin's rear
  end reaches x66.35 with stroke tolerance, endplay and guide stack combined;
  the sleeve extends a further0.65 mm. Final sleeve grade/attachment, press-fit
  tolerances and divider/cover seals remain engineering work.
- The collar cannot be deliberately rotated while the pin is engaged. No friction
  clutch or cam ramp substitutes for the pin. Return spring positively re-engages
  a bore; red band remains visible unless fully engaged. Hood prevents snagging;
  slider/pin cannot be removed externally or held open by a wedged cable.
- Independent Ø4 steel stop peg atR30 travels a4.30 mm-wide semicircular track with
  R2.15 ends. Pin radial clearance gives~.286° extra each end:180.57° nominal.
  Axial stop overlap≥2 mm throughout release/endplay; pin-lock release cannot
  bypass the travel stops. Captive cheeks prevent axial lift over the stops.
  The right cheek has a **Ø4.10 mm passage** for the Ø4 peg; its shoulder and
  captive attachment still require detail. Solid peg/cheek interference is not
  an acceptable substitute for a mounting interface.
- Static targets: locked1 N·m, hard-stop abuse2 N·m, axial retention100 N,
  port cable pull40 N. At1 N·m andR29, pin shear load34.5 N; Ø3 area7.07 mm² gives
  4.9 MPa nominal single-shear stress; ring bearing pressure34.5/(3×2)=5.75 MPa.
  These are load estimates, not fatigue/impact or housing proof. At2 N·m/R30,
  stop load66.7 N. Qualify inserts, ring anchors, guides and bosses as well as steel.
- Target10,000 full rotation cycles and20,000 lock releases under cable loading,
  then repeat torque/endplay/electrical checks. No cycle life has been demonstrated.

The CAD captures rings, holes, peg, travel track and retaining-cheek concepts.
Spring, captive-slider guide, screw/insert stack, hood and detailed cable cassette
are dimensioned requirements **not complete modeled manufacturing features**.
Do not machine the whole unit from the STEP assembly without closing these items.

### Bounded wire path and pinch prevention

Two individually insulated, high-strand24 AWG secondary conductors run in **separate
axial lanes** in an enclosed annular cassette. Only5 V andreturn cross the moving
interface; TPS25810 and CC resistors sit on the rotating board so CC does not need
moving wires. Select a supplier-qualified continuous-flex wire with OD≤1.2 mm,
strand diameter≤.05 mm and dynamic bend rating≤7 mm; this wire AVL is open.
Do not substitute commodity hookup wire on the strength of an AWG match.

Inner wire centerline radius `ri=26 mm`, outer `ro=40 mm`, reversing U radius
`R=(ro−ri)/2=7 mm`. At collar angleθ, loop angleφ satisfies:

```
Lactive = ri φ + ro(φ−θ) + πR
φ = π + ro θ/(ri+ro)
θ = −π/2 … +π/2
φ = 125.45° … 234.55°
Lactive = π(26+40+7) = 229.34 mm
cut length target = 249.34 mm + termination allowances
```

Allocate10 mm strain-relieved straight tail at each end before stripping/crimping.
At the extremes, inner arc length56.93…106.43 mm and outer arc150.42…100.92 mm
sum with the21.99 mm U bend to the same229.34 mm. This is a **rolling reversing
loop**, not a wire twisted through180°. Tangential clamps keep wire orientation;
modeled ideal torsion is zero. Strand bending strain estimate `.05/(2×7)=.36%` is
only a screening calculation. A physical cassette must verify it rolls without
crossing, buckling, rubbing, or moving the effective bend below7 mm.

Two1.6 mm-wide guide lanes (axial centers x61 and64 mm) with a0.8 mm divider
(x62.1…62.9, leaving0.3 mm to each lane edge) and radiused closed covers keep
conductors separated and exclude them from lock/stop gaps. At R29 the divider and
covers must terminate/seal against the modeled B19 sleeve; do not run a continuous
divider through the pin stroke. The ideal two-lane arc sweep at181 angles gives
**0.50 mm minimum nominal wire-to-sleeve clearance** with maximum1.2 mm wire OD.
Allowing ±0.05 mm each for R29/inner path radius and +0.05 mm sleeve OD leaves
**0.375 mm**; real guide construction and wire motion must establish those bounds.
The collar USB window now occupies x65.5…78 rather than x64…78: its nearest
axial edge clears lane2's x64.8 edge by0.7 mm. The rotating board and USB envelope
are lowered1 mm (board z−3.5…−2.5, receptacle z−3…0.66) to clear the sleeve;
exact footprints, posts and plug access remain unverified.
Maintain≥0.3 mm running
clearance to insulation at worst tolerances; no sharp seam lies across a travel
path. Inner barrier separates the entire cassette from mains. Collar side cheeks
retain the loop even with release held. Stop travel is mechanically limited before
any tail reaches tensile load; ±1° overtravel consumes<0.70 mm outer-arc motion,
covered by the10 mm tail reserve **only after measured routing validation**.

At copper20°C resistivity.0175 Ω·mm²/m and24 AWG area.205 mm², two249.34 mm leads
have~.0426 Ω loop resistance, giving64 mV drop/.096 W at1.5 A. At80°C use~.0527 Ω,
79 mV/.119 W, before terminations. Full source voltage compliance at minimum PSU
output and worst TPS25810 resistance therefore remains a gate; nominal5 V alone
is not proof. Verify1.5 A at the receptacle across temperature, not only the normal
small dongle draw. No external USB cable voltage drop is included here.

### Three separate fixed-end assemblies

| Variant | Stationary input | Stationary output | Voltage scope |
|---|---|---|---|
| PC | NAC3MPXXA blue power-in chassis | NAC3MPXXB gray power-out chassis |100–240 V AC nominal, pending assembly assessment |
| T1 | NAC3MPX-TOP inlet | NAC3FPX-TOP outlet |100–240 V AC nominal, pending assembly assessment |
| US | approved molded NEMA5-15P pigtail | approved molded NEMA5-15R pigtail |120 V nominal,125 V maximum connector class; never240 V |

Use the gray-to-blue matching jumper for PC output to fixture input. Current XX/FXX
breaking-capacity conditions do not transfer to unidentified legacy mates; de-energize
legacy powerCON before mating. TRUE1 TOP uses its specified mate pair. Connector
approvals do not certify this assembly or its USB opening.
[PC input](https://www.neutrik.com/en/product/nac3mpxxa),
[PC output](https://www.neutrik.com/en/product/nac3mpxxb),
[TRUE1 inlet](https://www.neutrik.com/en/product/nac3mpx-top),
[TRUE1 outlet](https://www.neutrik.com/en/product/nac3fpx-top),
[NEMA class reference](https://leviton.com/products/515cv-lit).

Use continuous **undimmed** mains. Target15 A total through-feed for initial
assessment, not a released label; all cord, splices, terminals, PCB branch and
enclosure thermal limits govern. PSU branch shares input current capacity.
PE runs continuously through fixed, independently retained connections; never
switch/fuse PE or rely on the rotary collar for bonding. Select branch fuse/surge
coordination from the actual module and assembly fault-current assessment. No
final fuse or wire gauge is invented. Keep primary wiring and all USB-accessible
secondary parts in separate compartments. Product category, insulation class,
creepage/clearance, altitude and material group must be assessed before energized
prototype authorization. Indoor dry use only is the current intended environment.

## 5. Manufacturer handoff and build-release gates

Deliver source plus exports together. Ask for **DFM/RFQ with an exception list**;
do not request production against an incomplete BOM. Quote custom shells, lock
ring/pin/track, bushings and nonenergized fit prototype separately from electrical
engineering/NRE. No unapproved substitutions of RF, isolation, safety, flexible
wire or mains connector components. BOM status `selected` means design candidate,
not purchased/qualified. `OPEN` rows must be resolved before a purchase BOM.

Assembly sequence: inspect custom parts → populate/review PCBs → factory-load the
resident recovery loader/application and provision UID/verification material →
test direct wired RDM update, interrupted update and physical service/cJTAG rescue →
secure cap cradle and harness strain relief → assemble
intact XLR and sidecar/saddle → test DMX/isolation/RF/buffer. For barrel, qualified
manufacturer installs stationary wiring/module/barriers → electrical safety
inspection → installs bounded secondary loop at neutral using jig → captures
bushes/collar/stops/retainers → installs positive lock and checks full engagement →
qualified product-safety/thermal/EMC validation. Keep mains work behind its separate
engineering approval gate.

| Gate | Observable required evidence |
|---|---|
| Multi-manufacturer fit | fetched official3D/exploded assets, source/date/revision; dimensions of recess/pitch/latch/plug/yoke/vents; oriented assembly overlay; at least4 models/3 manufacturers proposed matrix; reject unsupported entries |
| Full electrical capture | actual all-sheet pins/values/footprints, power-only USB current-state table, independent UVLO/rearm, external staging flash and distinct RDM-service/factory controls, RF reference network; ERC and independent review |
| PCB | routed four-layer board, approved stackup/isolation/antenna keepouts, thermal/current checks, DRC, fabrication/assembly outputs and full placement collision checks |
| Mechanism | fully modeled fasteners/spring/guide/cassette/endcaps; worst-case stack and wire motion sweeps; no contact/pinch/lock bypass; cycle/torque/pull data |
| DMX/RDM update and rescue | FTC controller/responder conformance; persistent UID; external staging/verified install; interrupted download/copy and rollback; physical RDM-service input distinct from ROM backdoor; cJTAG rescue with damaged loader; no second active controller |
| Buffer | scoped rails/DE and cap current at agreed TX/RDM/loaded-DMX duty, cold/hot/aged equivalents;≥10 s worst case,30 s target point separately reported |
| DMX/RF | loaded bus/polarity/protection/turnaround/isolation and fixture-adjacent antenna tuning/radiated compliance; hardware measurements, not simulations |
| Mains | connector/endcap and harness drawings, fuse/cord/strain relief selection, PE continuity, dielectric/leakage/touch/fault/temperature review, complete product approvals as applicable |
| Source output | min/max line and ambient,1.5 A output after flex/controller losses, overcurrent/short/unplug/discharge; check module derating in sealed core |

No hardware validation, full-product ERC, PCB DRC or certification was run. The
partial DMX sheet passes actual KiCad ERC as recorded below; that does not cover
the missing circuits. CAD checks cover modeled envelopes and named clearances.
The remaining gates materially
prevent production release; they do not prevent a manufacturer RFQ/DFM review.

## 6. Canonical checkpoint and integration receipt

**Publication checkpoint, 2026-10-25:** owner explicitly requested saving these
files on `main`, committing and pushing. [Hardware folder index](../../hardware/README.md)
collects the editable designs, generated drawings/STEP, candidate BOMs and
validation/source records. Earlier “no publication” statements describe the
historical task scope; this instruction authorizes a development checkpoint,
without changing HOLD or manufacturing acceptance. Downloaded vendor originals,
reference archives, full-page vendor previews, tool caches and automatic backups
remain local/ignored; original source URLs/hashes are retained. Fresh local KiCad
ERC gives zero violations for DMX, MCU/RF, protected25 power/protection and S12.
Protected25 DRC has zero geometric violations and485 unconnected items. CAF-R2
artifact verification passes; this is not a new mechanical qualification run.
[Publication check record](../../hardware/publication-checkpoint.json).
Repository Actions permissions were read and remain `enabled:false`.


Historical development bases: hardware origin78ed438560702beb38ba36938ed613502a42a1be;
shared development HEADb42c0e6284aac734fde851c69146abf73920f337. The publication
checkpoint preserves the newer origin/main instructions commit4b88684 and adds
only this hardware/design checkpoint. Earlier receipts retain their original
base revisions; no branch switch or deployment is authorized.

**Current acceptance: NOT RELEASED.** Hardware only; TI-only native NOVA-LINK;
2.4GHz plus US915MHz; USB-C power only; wired/wireless RDM management; future
DMX-port firmware update through a resident FTC loader with external staging.
Normal operation now requires5V with at least1.5A USB-C advertisement; existing
baseline acceptance below does not establish that new qualification.
The owner corrections are preserved verbatim in section1. No firmware evaluation,
implementation, programming, RF operation, hardware measurement or certification.

Parent integration check: `python3 hardware/compact-dmx/validate_package.py` wrote
a **PASS / NOT_RELEASED** receipt; parent reran it after the BOM reconciliation
with exit0, saved `.tools/checks/revd-bom-reconciliation-package.log`.
[Package evidence](../../hardware/compact-dmx/exports/package-validation.json).
This run checks the unchanged active power baseline, not the separate power
candidate still in development. The reconciled procurement list has54 BOM rows;
current separate exports have
14 DMX-sheet components/15nets,78 power/service
components/74nets and26 MCU-support/dual-feed components/57nets. All three
separate captured projects report zero KiCad10.0.7 ERC errors/warnings/exclusions;
they are not a merged full-product ERC or routed PCB. The MCU sheet has25
physical parts and one power interface.49 MCU pins,46 retained TI connections and
12 antenna/matching connections are checked; tuning and inactive-port behavior
remain unqualified. [Current dual-feed receipt](../../hardware/compact-dmx/eda/mcu-radio/dualfeed-implementation-receipt.json).
The prior switched-topology receipt is retained as historical evidence.
Parent independently matched12/12 retrieved source hashes and verified SWRC354
is an actual ZIP. The earlier SWRC345A/SWRC361 files are login HTML.

CAD checks:38 valid modeled solids,49 clearances,78 neutral barrel pairs,15
lock-release cases and181 ideal wire positions;11 STEP exports,3 SVG sheets,
3-page PDF and2 DXFs. Sidecar98×34×24 and barrelØ84 collar are development
baselines. A partial PCB candidate now places37 MCU/RF/DMX parts including the
dual-feed antenna; full power/SPI/USB/service hardware remains unplaced. The
antenna region has courtyard screening, but no routed reference geometry or
RF measurements. No whole-assembly
dynamic collision, fixture fit or compactness acceptance follows from these checks.

**Independent review and disposition:** initial GLM5.3 reviewed54 pinned original
Rev B files. It confirmed boss/PCB and stop-peg/cheek interference, USB-window/lane
conflict and released-pin/divider conflict. Boss seating, actual cheek passage,
window relocation and B19 pin sleeve corrected the modeled conflicts. Parent
reopened FCStd and checked zero boss/PCB and peg/cheek intersection. Sleeve
attachment/cassette seals and physical durability remain open. Failed first GLM
transport used unsupported message content; the successful retry was text-only.

One broad Claude Opus5.5 high/fastMode false pass reviewed66 pinned files under
`.tools/reviews/revc-power-20261022/`, manifest SHA-256
`8e25fb8aed6dd5d96aaae85e8b1e28c419f7464d97f071be520930fbcbb10907`,
against actual HEADb42c0e6. All66 hashes matched. Task:
`node:delegated-task:command%3Amcp%3Aeaab7c50-b35d-4a00-9efc-f2e54928abd4%3Adelegate-task%3Anova-revc-opus-power-review-20261022-r1`.
It used cached datasheets/netlist arithmetic, no measurements or CAD re-review.

- **D-A high, static defect corrected:** TPS2116 replaces the lossy main diode;
  TPS3700 qualifies actual converter VIN. Netlist-derived checks reproduce the
  former false-good case and pass256 operating-mode corners with explicit
  resistance/sag/load allocations. Dynamic detection/load steps remain unproved.
- **D-B medium, still unmet:** cold-cap precharge can exceed the input limiter
  and cycle RUN. Removing the old filter and adding barrier soft start do not
  establish repeatable startup. The bounded investigation returned proposals,
  not a captured fix; a separate prototype capture is now authorized without
  introducing a1.5A-only source restriction.
- **D-C medium, arithmetic corrected:** subtract100mV maximum recharge hysteresis
  from2.548V. Aged delivered energy11.7282J /1.11W yields10.57s, only0.57s
  calculated margin. Runtime remains unmeasured and not guaranteed.

[Power fix receipt](../../hardware/compact-dmx/eda/power-service/review-fix-receipt.json).
Parent separately ran `python3 hardware/compact-dmx/eda/power-service/corner-proof.py`: Independent
netlist arithmetic passed32 detector/256 mode corners and explicitly reports
`cold_cap_startup_acceptance: UNMET`, `manufacturing_acceptance: NOT_RELEASED`.
The previous12.27s runtime omitted recharge hysteresis. Charging remains25mA,
26min ideal nominal/43.1min corner before tail. INPUT_FAULT_N remains unrouted: an
always-on2.5V signal is neither power-off safe nor a guaranteed3.3V MCU logic high.
Its translator is a proposal, not populated hardware or accepted connectivity.

**Active owned work:** Astra Low/standard owns MCU/RF/antenna, DMX and BOM changes;
Sol6.1 high/standard owns a separate power prototype candidate; parent owns canonical
docs/DECISIONS/HTML, CAD integration, acceptance and publication. No children
may commit/push, add tools/auth, operate hardware or create children/threads.

- Antenna engineering completed:
  `node:delegated-task:command%3Amcp%3Aeaab7c50-b35d-4a00-9efc-f2e54928abd4%3Athread-send%3Anova-revc-compact-antenna-engineering-20261022-1`.
  Captured production dual-feed Johanson0900AD47A2450001E and removed the
  preliminary switch/control parts. Match topology was checked against the
  manufacturer's enlarged drawing. Its50×30mm reference is not this90×28mm PCB.
  [Primary datasheet Rev3.1](https://www.johansontechnology.com/docs/4912/Antenna-0900AD47A2450001E_4RGCp0j.pdf).
- Astra Low completed termination/prototype ESD capture and initial footprints:
  `node:delegated-task:command%3Amcp%3Aeaab7c50-b35d-4a00-9efc-f2e54928abd4%3Athread-send%3Anova-revc-dmx-completion-footprints-20261022-1`.
  Initially four source-dimensioned footprints/79 numbered pads were checked.
  Parent checked the actual exported
  termination nets and thermal arithmetic: a fresh DMX-only KiCad CLI export/ERC
  passed14 components/15 nets with zero violations, saved under
  `.tools/checks/revc-termination-parent/`. The subsequent assignment pass below
  supersedes the initial footprint count; switch approval/access remain open.
  [Exact receipt](../../hardware/compact-dmx/eda/footprints/physical-implementation-receipt.json).
- Astra Low footprint-assignment follow-up completed:
  `node:delegated-task:command%3Amcp%3Aeaab7c50-b35d-4a00-9efc-f2e54928abd4%3Athread-send%3Anova-revc-complete-source-footprints-20261022-1`.
  Initial assignment pass:37 physical MCU/RF/DMX components,31 source-backed,
  six provisional. The replacement pass below supersedes those approval counts.
  Initially15 footprints parsed,14 had dimensional checks/109 numbered pads;
  actual-export component/pad maps and cross-sheet checks pass. IPC copper,
  paste and mask polygons come from exact SWRC354 Gerber vectors/PnP, with
  current-production-part applicability still a process/RF gate. The17MB ASCII
  source belongs to the separate LaunchPadR1RevB, not the IPC board. Five Johanson
  tuning parts provisionally share TI0402 lands. Parent subsequently verified
  PCM12SMTR's official Active status and inspected its recovered manufacturer
  drawing: the candidate mounting-row inner gap is1.41mm versus1.13mm specified.
  Complete switch datum/land correction remains open, without a tested assembly
  failure claim. [Switch source and dimension receipt](../../hardware/compact-dmx/eda/footprints/pcm-parent-verification.md).
  Parent matched the receipt's three schematic hashes
  and ran the integrated verifier. [Source details and gates](../../hardware/compact-dmx/eda/footprints/COMPLETION.md),
  [exact receipt](../../hardware/compact-dmx/eda/footprints/footprint-completion-receipt.json).
- Partial-board placement candidate and correction completed (Astra Low/standard):
  `node:delegated-task:command%3Amcp%3Aeaab7c50-b35d-4a00-9efc-f2e54928abd4%3Athread-send%3Anova-revd-actual-board-placement-20261022-1`.
  [Editable partial PCB and placement evidence](../../hardware/compact-dmx/eda/placement-candidate/README.md):
  37 components/156 numbered pads/67 nets on the90×28 outline, zero tracks.
  The initial generator/verifier shared a leading-slash alias error and placed
  termination parts across the proposed isolation corridor; parent found these
  despite zero default geometric violations. Initial objections remain under
  `.tools/checks/revd-placement-parent/initial-objections.json`.
  Correction task:
  `node:delegated-task:command%3Amcp%3Aeaab7c50-b35d-4a00-9efc-f2e54928abd4%3Athread-send%3Anova-revd-placement-contract-fix-20261022-1`.
  **Targeted corrections accepted:** parent inspected the corrected drawing,
  loaded the actual board and independently checked U5.2↔U1.19, U5.4↔U1.18 and
  U5.5↔U1.12. Safe DE/power gate nets and ground domains remain separate. Both
  terminators/C4 were repacked; all non-U5 courtyards clear the corridor and all
  five isolated-net parts remain on its isolated side. Fresh parent KiCad DRC:
  zero default geometric violations,89 unconnected items. Board SHA-256
  `dcfa7c469cf45f74e71fe2d50cef68aa2af697d7e97a73ff398c447cf5312ed6`;
  evidence `.tools/checks/revd-placement-parent/corrected-receipt.json` and
  `corrected-drc.json`. Complete156-pad/source-hash verification also passed.
  DMX entry(10,20) replacing(72,20) remains a proposal: wire landing, nearby
  screw and strain relief are not designed. No enclosure CAD is changed.
  Power/SPI/USB/service parts remain unplaced; no full-board, routed-RF,
  isolation-rating or compactness acceptance follows from this task.
- RF provisional-land closure pass completed (Astra Low/standard):
  `node:delegated-task:command%3Amcp%3Aeaab7c50-b35d-4a00-9efc-f2e54928abd4%3Athread-send%3Anova-revd-close-provisional-land-sources-20261022-1`.
  [Sources and selected parts](../../hardware/compact-dmx/eda/footprints/REPLACEMENT-PASS.md),
  [exact receipt](../../hardware/compact-dmx/eda/footprints/replacement-receipt.json).
  Three Coilcraft0402HP inductors and two MurataGJM155 capacitors retain the
  starting values with source-backed lands. Current37 assignments:36 source-backed,
  one provisional switch;17 footprints parse,16 patterns/113 library pads checked.
  This does not establish RF equivalence: retune and measure the new parasitics.
  Parent matched four source hashes, nine artifact hashes and all five actual
  exported MPNs, then reran package checks successfully. Fresh partial-board DRC
  still reports zero geometric violations/89 unconnected items.
- Bounded switch-source search and export-fingerprint repair completed (Astra Low/standard):
  `node:delegated-task:command%3Amcp%3Aeaab7c50-b35d-4a00-9efc-f2e54928abd4%3Athread-send%3Anova-revd-source-complete-termination-switch-20261022-1`.
  Neither checked alternative qualified: EG1218 is top-actuated THT with
  incomplete body registration; EG1315AA is SP3T and its25mA rating is below
  termination current. PCM12 remains provisional; circuit and BOM are unchanged.
  [Bounded result and repair receipt](../../hardware/compact-dmx/eda/footprints/switch-alternative-receipt.json).
  Parent also found that fresh KiCad exports change only the generated
  `design/date`, causing the placement verifier's raw input hashes to fail after
  package checks. Two independent exports were identical after removing only
  that generated field; evidence `.tools/checks/revd-placement-parent/export-date-proof.json`.
  Stable parsed-XML fingerprints now blank only top-level `design/date` text;
  regressions retain value/pin/net/footprint/pin-type/other-metadata mutation
  detection. Source schematic/library files remain raw-hash checked. Parent ran
  the whole package, then verified the unchanged board without regeneration:
  both raw netlist hashes changed, both fingerprints passed,156 pads passed,
  no source mutations. Board SHA-256
  `fe577602e2891b7c78ec8fba5d71f8648076cadccff2774c96e2673c6fb15a2b`;
  receipt `.tools/checks/revd-placement-parent/post-package-stable-receipt.json`.
  Current placement remains37 parts/67nets, zero geometric violations and89
  unrouted connections; this repair closes only the false stale-input failure.
- Exact JS102011SAQN qualification completed (Astra Low/standard), no substitution:
  `node:delegated-task:command%3Amcp%3Aeaab7c50-b35d-4a00-9efc-f2e54928abd4%3Athread-send%3Anova-revd-js102011saqn-exact-qualification-20261022-1`.
  Parent recovered the current official exact-product page and2026 JS datasheet;
  SA is right-angle SMT, correcting the historical THT description. Active,
  maintained side actuation and0.3A/6V rating are source-backed. The page4 pad
  pattern lacks terminal-row horizontal registration to the locator pair and
  complete body-origin registration. A centered footprint would assume symmetry;
  PCM12 remains provisional and the active circuit/footprints/placement are
  unchanged. [Dimension analysis](../../hardware/compact-dmx/eda/footprints/JS-EXACT-CANDIDATE.md)
  and [receipt](../../hardware/compact-dmx/eda/footprints/js-exact-candidate-receipt.json).
  Parent matched all seven source/active-artifact hashes before its separate BOM
  reconciliation below. No fresh ERC/DRC follows from this read-only candidate check.
- Parent BOM reconciliation: the current schematic already used U10 TPS3700DDCR
  and U19 TPS2116DRLR, but the list still specified two TLV3012B comparators and
  D_MAIN PMEG2010ER. Split U8/U10 entries, add U19 and retain only the two BAT54H
  AON diodes.54 rows now describe the existing capture; no circuit revision.
  Package validation now passes with those exact parts/quantities compared against
  the actual KiCad export and rejects a reintroduced D_MAIN. PCM12 lifecycle wording also
  reflects the retained Active-page receipt; its land gate remains open.
  Post-package verification passes156 pads on the unchanged board; parent receipt
  `.tools/checks/revd-bom-reconciliation-receipt.json`. This does not validate the
  separate power candidate or change the manufacturing-release boundary.
- USB-C/NOR physical footprints completed (Astra Low/standard), integration gated:
  `node:delegated-task:command%3Amcp%3Aeaab7c50-b35d-4a00-9efc-f2e54928abd4%3Athread-send%3Anova-revd-usb-nor-source-footprints-20261022-1`.
  [Candidate footprints and sources](../../hardware/compact-dmx/eda/service-footprints/README.md).
  Parent reran the KiCad-backed verifier successfully:24 USB contacts,9 NOR
  pads and6 physical shell attachments. USB shell has no active net binding;
  mask/stencil/DFM remain open. NOR lands are engineering-derived, with EP ground
  consistent with the manufacturer recommendation, not supplier-approved lands.
  Hirose recommends0.8mm PCB versus the current1.0mm; no qualified thickness
  tolerance was found. Its primary-page NRND status was reported in the source
  record. Existing board/circuits remain unchanged; no new fit or release claim.
- Exact power-only USB replacement candidate completed (Astra Low/standard), integration gated:
  `node:delegated-task:command%3Amcp%3Aeaab7c50-b35d-4a00-9efc-f2e54928abd4%3Athread-send%3Anova-reve-gct-power-usb-footprint-20261022-1`.
  [Sources, geometry and candidate](../../hardware/compact-dmx/eda/service-footprints/gct-power-candidate/README.md).
  GCTUSB4125-GF-A manufacturer A6 drawing supplies the6 contacts and4 shell
  stakes; its default1mm stake length is not a PCB-thickness qualification.
  The asserted1.00±0.10mm board recommendation was not present in the retrieved
  current primary drawing/spec and is not adopted. Parent matched3 source
  hashes and the candidate board hash, viewed the primary drawing and actual
  placement, reran the independent verifier and fresh KiCad DRC:39 electrical
  parts, zero geometric violations,103 unrouted connections. All original37
  parts retain actual pad geometry/nets/values. Parent receipt
  `.tools/checks/gct-parent-receipt.json`; candidate board SHA-256
  `dca73c2ab334e62814240cd0c01a24c17fa69820f151dbf55571e56febdca278`.
  NOR is still engineering-derived. SH→GND_USB exists only as a proposal in
  this copy; active circuitry/BOM/CAD remain unchanged. Topmount needs solid
  PCB under the obsolete midmount notch. Mating facey51 is3mm behind the case
  facey54; plug access is unresolved. Thickness/retention, mask/stencil, shell
  ESD return, full power placement and physical assembly remain gates.
- Local GCT port mechanical prototype completed (Astra Low/standard), not adopted:
  `node:delegated-task:command%3Amcp%3Aeaab7c50-b35d-4a00-9efc-f2e54928abd4%3Athread-send%3Anova-reve-gct-port-mechanical-fit-20261022-1`.
  [Editable CAD, sections and board copy](../../hardware/compact-dmx/eda/service-footprints/gct-power-candidate/mechanical/README.md).
  Connector origin shifts from(42.7,44.6) to(42.7,47.6); mating facey54 is
  nominally flush with the outer case. Main90×28×1mm PCB gains a12.4×2.3mm
  tongue, so the outline changes locally while the98×34×24mm case stays fixed.
  Old midmount notch is filled. Integral support rails/bridge and compliant
  shims/rear pad are modeled; no supplier material or print strength is qualified.
  Parent reopened saved FCStd and independently checked12 artifact hashes,
  14 valid closed solids,78 pair common volumes and65 external approach cases.
  Parent also compared43 footprints/249 pad primitives: only USB pads move3mm;
  dimensions, layers, drills, values and nets remain consistent. Actual8-segment
  tongue outline passes fresh KiCad DRC: zero geometric violations,103 unrouted.
  Evidence `.tools/checks/gct-flush-parent-cad.json` and `gct-flush-parent-board.json`.
  Board SHA-256 `9d199805cb6153b60b46d6027ff0544c402f59536bb5f8b17889015254a0aec1`.
  This screens explicit envelopes; stake thickness remains an assumed0.3mm,
  compliant-pad compression/adhesive/creep, strength, board thickness/retention,
  assembly path and exact cable fit remain physical qualification gates.
  Power-layout owner received the new keepouts: rear stopx38..47.4/y44.6..46.6
  startsz11.5 above PCBtop11, leaving only0.5mm component height there; backed
  pad extends toy47.2. Underside rails/shims also exclude bottom components.
- Section-drawing correction completed (Astra Low/standard):
  `node:delegated-task:command%3Amcp%3Aeaab7c50-b35d-4a00-9efc-f2e54928abd4%3Athread-send%3Anova-reve-gct-section-drawing-fix-20261022-1`.
  Parent's rendered PDF inspection found front-wall geometry covering the heading
  and extending above the page. `draw.py` now uses equal Y/Z scale and a separate
  annotation column; full geometry lies below the title. Parent rendered and
  visually inspected the corrected [section PDF](../../hardware/compact-dmx/eda/service-footprints/gct-power-candidate/mechanical/section.pdf),
  checked all12 current artifact hashes and parsed SVG geometry bounds y120..552.
  CAD and board hashes remain unchanged; prior geometry/DRC evidence still applies.
  This is a drawing correction only and closes no physical qualification gate.
- Startup resolution investigation completed:
  `node:delegated-task:command%3Amcp%3Aeaab7c50-b35d-4a00-9efc-f2e54928abd4%3Athread-send%3Anova-revc-startup-resolution-20261022-1`.
  [Reviewable proposal](../../hardware/compact-dmx/eda/power-service/startup-proposal.md)
  and [exact receipt](../../hardware/compact-dmx/eda/power-service/startup-receipt.json).
  Retaining TPS61094 at500mA needs unsupported prebiased-handoff bounds; no
  guaranteed repair was established. That proposal separates USB main power,
  BQ25173 charger and cap-fed TPS61023 boost, initially with CC-qualified1.5A
  sources. The1.5A coupling was subsequently corrected below. Its net11.8mm²
  added IC body area excludes support parts/courtyards;
  startup, low-input boost limits, CC timing, thermal and placement remain open.
  Existing capture and all27 baseline artifacts are unchanged. Parent reran
  `startup-analysis.py`, matched all nine receipt-pinned new artifact hashes
  and all27 baseline hashes. Abstract state/arithmetic checks do not prove a
  new circuit or close D-B. Keep the existing25mA charging setting in the active
  capture; the proposal's100mA setting is not selected hardware.
- Historical source compatibility correction: the earlier owner question proposing a1.5A
  requirement is withdrawn. Separation does not require1.5A; do not treat the
  unanswered question as authority or block circuit work on that choice. Keep
  the current500mA engineering basis while developing a candidate, without
  claiming guaranteed compatibility. The barrel still needs correct CC
  advertisement; supply wattage alone is insufficient.500mA was an engineering
  choice, not an owner requirement. This was the prior task basis; the owner's
  subsequent explicit1.5A approval below supersedes it.
- Bounded compatibility clarification completed (Sol6.1 high/standard):
  `node:delegated-task:command%3Amcp%3Aeaab7c50-b35d-4a00-9efc-f2e54928abd4%3Athread-send%3Anova-revc-separated500-clarification-20261022-1`.
  [Clarification and limits](../../hardware/compact-dmx/eda/power-service/startup-compatibility-note.md).
  Omitting CC detection/LDO saves7.2mm² IC body area plus support circuitry.
  Healthy25mA-charge arithmetic fits the stated500mA allocations; the checked
  switches do not establish fault/startup bounds. Parent matched37 preserved
  artifact hashes, five source hashes, note hash and key arithmetic. This is
  not a completed circuit or PCB-area proof.
- Separated-power500mA prototype capture completed (Sol6.1 high/standard):
  `node:delegated-task:command%3Amcp%3Aeaab7c50-b35d-4a00-9efc-f2e54928abd4%3Athread-send%3Anova-revd-separated-power-prototype-20261022-1`.
  [Captured circuit and limits](../../hardware/compact-dmx/eda/power-service/separated-candidate/DESIGN.md),
  [receipt](../../hardware/compact-dmx/eda/power-service/separated-candidate/capture-receipt.json).
  Separate25mA charger/cap-only boost/raw AON and latched fault shutdown are
  captured:176 exported components,170 fitted parts,44 ICs,135nets. ERC reports
  zero errors/warnings/exclusions;316 IC pins,128 two-terminal parts,36864 logic
  cases and256 detector corners checked. Parent matched29 artifact hashes and
  reran `verify.py` and `corner-proof.py` successfully. The approximate344mm²
  fitted body area excluding cell exceeds the150mm² reservation before lands or
  routing. DC envelope494.83mA; minimum healthy allocated margin16.57mA;
  conditional runtime10.50s. No guaranteed startup/runtime, footprint packing or
  manufacturing acceptance. Fault translator remains unimplemented.39 protected
  inputs were tracked:35 matched the start snapshot and4 generated baseline
  exports changed concurrently; no restoration of another worker's outputs.
  This candidate has no1.5A qualification and is now a comparison design.
  Parent integration evidence for this candidate and the USB/NOR source checks:
  `.tools/checks/reve-source-decision-parent-receipt.json`; product board SHA-256
  remains `fe577602e2891b7c78ec8fba5d71f8648076cadccff2774c96e2673c6fb15a2b`.
- Owner source decision, current: “Require 1.5 A USB-C (Recommended)”. Normal
  operation requires a5V source advertising at least1.5A, including the barrel.
  This is affirmative authority, not the older unanswered question. Hardware
  must qualify both cable orientations/default/1.5A/3A/detach and prevent a
  false externally-powered install gate; cap ride-through remains distinct.
- Qualified-source compact power revision (Sol6.1 high/standard), captured and
  parent-checked, not integrated or released:
  `node:delegated-task:command%3Amcp%3Aeaab7c50-b35d-4a00-9efc-f2e54928abd4%3Athread-send%3Anova-reve-qualified15-power-compact-20261022-1`.
  [Candidate circuit, sources and limits](../../hardware/compact-dmx/eda/power-service/qualified15-candidate/DESIGN.md).
  Separate BQ25173 charging/TPS61023 backup, TPS259474L input protection and
  hardware CC qualification reduce the comparison design from44 to30 ICs and
  from170 to133 purchased parts excluding USB. All137 candidate footprints are
  nominally placed alongside the preserved37 MCU/RF/DMX parts, on both sides of
  the proposed90×28mm board with flush-port tongue. Core courtyards total
  749.96mm², so the old150mm² reservation fails; that sum alone does not prove
  the enclosure must grow. Actual nominal packing passes, routing feasibility
  remains unproved. Parent verified95 artifact,33 source and69 protected-file
  hashes; fresh KiCad circuit export matches the checked components, symbols
  and nets; fresh ERC has0 violations. Actual board DRC has0 geometric
  violations and452 unconnected items, with zero routing. Independent pin,
  passive, logic, numerical-corner and saved-board checks pass. Local evidence:
  `.tools/checks/qualified15-parent/parent-receipt.json` and `commands.log`.
  The1.209A DC screen depends on applying a12V test table at5V. Healthy startup,
  source transitions, thermal behavior and independent cell-fault protection
  remain open. Conditional runtime is10.50s; the explicit aged60mΩ ESR example
  gives9.73s, so the10s minimum is not accepted. Baseline circuitry/BOM/CAD
  remain comparison artifacts; this candidate does not authorize fabrication.
- Targeted independent power review (GLM5.3, text-only, read-only), completed:
  `node:delegated-task:command%3Amcp%3Aeaab7c50-b35d-4a00-9efc-f2e54928abd4%3Adelegate-task%3Anova-qualified15-targeted-glm-review-20261023-r1`.
  Pinned state: HEAD `b42c0e6284aac734fde851c69146abf73920f337` plus197 files
  in `.tools/reviews/qualified15-20261023/`; snapshot-manifest SHA-256
  `ffa0d335367e6153d67c67c0c2c1162d818f89f9185bc562fd7bf2fdb5827938`.
  Review focuses on CC qualification, source/backup/cutoff transitions, the
  loader's external-power gate and concrete circuit/placement mismatches.
  Previous Rev C review findings and the candidate's stated failed requirements
  are included; no repeat broad review or firmware work is authorized.
  **Critical D-1, corrected in capture:** the reviewed U40 TPS2116 MODE was
  grounded while its raw-input PR1 divider was high. Datasheet §7.3.1 selects
  Hi-Z in this state, shutting down
  AON on valid USB power, both at cold boot and during hot attach. The existing
  checks validated the same wrong pin map and assumed AON was powered. Parent
  independently checked the frozen netlist, primary PDF and40 divider/reference
  corners; all valid-input cases select shutdown. Evidence:
  `.tools/checks/qualified15-review-parent.json`. No other demonstrated defects
  were reported; the previously listed electrical/runtime/physical gates stay
  open. The earlier passing ERC and nominal placement establish no startup
  acceptance. Corrected capture and behavioral regression are complete:
  `node:delegated-task:command%3Amcp%3Aeaab7c50-b35d-4a00-9efc-f2e54928abd4%3Athread-send%3Anova-qualified15-u40-fix-20261023-1`.
  U40.5 MODE now connects directly to U40.3 VIN1 (`AON_USB_LIMITED`), implementing
  TI's priority mode without AON-powered bias. Parent verified105 current file
  hashes and all197 original review files, independently reran the behavioral,
  electrical and corner checks, and made fresh actual KiCad netlist/ERC/DRC
  exports. The actual saved board differs only in U40.5's net token; all other
  board bytes and geometry are preserved. Seven source-table rows and48
  qualified-source corners pass; negative tests reproduce both old cold-boot
  and hot-attach failures. Fresh ERC has0 violations; DRC remains0 geometric
  violations/452 unconnected items. Evidence:
  `.tools/checks/qualified15-u40-parent/parent-receipt.json` and `commands.log`.
  Current candidate receipt SHA-256:
  `69b5d108cb5b40924c75389221586ca3d236bd46212cfc6184b3160a13466362`.
  The2mA AON-feed load is an engineering allocation, not a measured maximum;
  supply ramps, main-mux precharge, source transitions and startup remain
  physical qualification gates. This correction closes the wrong-mode wiring
  defect, not whole-device startup acceptance or manufacturing release.
- Buffer improvement investigation (owner-requested Astra LOW/standard), complete:
  `node:delegated-task:command%3Amcp%3Aeaab7c50-b35d-4a00-9efc-f2e54928abd4%3Athread-send%3Anova-buffer-runtime-fit-20261023-1`.
  [Three-family screen, primary sources and packaging proposal](../../hardware/compact-dmx/eda/buffer-fit-candidate/README.md).
  Parent selects Eaton HV1625-2R7256-R25F as the development basis: max body
  Ø16.5×28.4mm, lowered cell centre y30.65/z18.1, local29.4×10.3mm PCB aperture,
  same98×34×24mm case. Initial tolerance and test-aging factors give15.75F;
  54mΩ ESR and80% electronics efficiency at1.11W give16.343s from2.448V to
  1.705917V loaded cutoff. Parent reproduced this using an independent analytic
  integral, verified26 artifact hashes, reopened16 valid closed CAD shapes and
  checked173 component envelopes with zero intersections. All177 live-board
  courtyard records exactly match the proposal's extraction after reconciling
  the final U40 correction; board hash is
  `fc0785cdaaf874002b2362835070f29f00b187e4054dd3ab093c43e177ea035f`.
  Nominal recharge at25mA is43.3min before tail. Independent evidence:
  `.tools/checks/buffer25-parent/parent-receipt.json` and `live-placement.json`.
  This closes the conditional energy-screen shortfall with a packaging proposal,
  not the measured10s runtime requirement. Cold/aged combined limits are absent;
  keep the cell≤65°C at2.6V. Formed leads, retention, vent path, cell protection,
  PCB cutout strength and routing remain open. The15F baseline remains unchanged.
- Actual25F prototype assembly (Astra LOW/standard), captured and parent-checked:
  `node:delegated-task:command%3Amcp%3Aeaab7c50-b35d-4a00-9efc-f2e54928abd4%3Athread-send%3Anova-buffer25-assembly-integration-20261023-1`.
  [Editable assembly, drawings, source evidence and limits](../../hardware/compact-dmx/eda/buffer-fit-candidate/integrated25/README.md).
  Actual rounded R0.5 aperture, proposed formed C23 leads/PTH slots, integral
  saddles, silicone liners, axial stops and screw-retained lid are captured.
  Parent independently verified23 current and26 prior artifact hashes,177
  unchanged noncell footprints/671 pads, fresh actual DRC0 violations/452
  unconnected,26 valid closed shape objects,321 zero-volume pair checks,4
  bounded intended screw/pilot engagements and3268 component-solid checks.
  An independent rounded-wire aperture construction reproduces the allocated
  0.178271mm cell/PCB gap. Evidence:
  `.tools/checks/integrated25-parent/parent-receipt.json`; actual board SHA-256
  `a607ea54646ee852cc41a1894928887a5fa5276dce76ea12690f43ff46b24dd8`.
  C23 remains a PCB-only derivative, with no new schematic/ERC acceptance.
  Eaton's fetched handling guide supplies no numeric forming radius or seal
  datum: proposed1.3mm straight/R1.2 bend requires supplier/process approval.
  The slot/forming X tolerance leaves only0.015mm allocated margin. Vent path,
  liner compression, screw/thread/retention strength, soldering, copper-free
  routing and full physical qualification remain open; no production release.
- Independent cell protection prototype (Sol6.1 high/standard), captured and
  parent-checked, protection acceptance UNMET:
  `node:delegated-task:command%3Amcp%3Aeaab7c50-b35d-4a00-9efc-f2e54928abd4%3Athread-send%3Anova-buffer25-cell-protection-20261023-1`.
  [Circuit, sources, faults and exact limitations](../../hardware/compact-dmx/eda/cell-protection-candidate/DESIGN.md).
  Independent TPS3700 OVP opens a TPS22963C charger-input switch; TPS3808
  inhibits startup. Cell-local045101.5MRL precedes the charger/boost split.
  Hysteretic cutoff/retry is explicit, not latched OVP. Proposed charger tuning
  is2.576V/25mA, OVP trip2.623–2.697V; conditional runtime is14.564s with nominal
  fuse resistance or13.256s with the126mΩ hot-fuse test allocation. No measured
  runtime or source/temperature/lifetime guarantee. Maximum interruption time
  is not published, and constant-current fuse timing does not prove clearing
  of a decaying cell short. Protection acceptance remains UNMET.
  Added14 parts occupy85.765mm² of courtyards, max fuse height2.94mm; the21-part
  coupon is not a sidecar placement. Parent verified63 file hashes,175 protected
  inputs,10 cached PDF hashes, fresh actual circuit export/ERC0, saved61 pads
  and fresh coupon DRC0 violations/45 unconnected. Evidence:
  `.tools/checks/cell-protection-parent/parent-receipt.json`. Main board/BOM/CAD
  remain unchanged by this separate prototype.
- Targeted cell-protection review (GLM5.3, text-only, read-only), completed:
  `node:delegated-task:command%3Amcp%3Aeaab7c50-b35d-4a00-9efc-f2e54928abd4%3Adelegate-task%3Anova-cell-protection-glm-review-20261023-r1`.
  State: HEAD `b42c0e6284aac734fde851c69146abf73920f337` plus239 pinned files in
  `.tools/reviews/cell-protection-20261023/`, snapshot-manifest SHA-256
  `88213168bc3450c06ed3d5f9abbf3d1a362c3f68c2ff2210cb4ce6a4024fa847`.
  No new demonstrated electrical defects; the reviewer reproduced every
  reported threshold/runtime/fault calculation and checked61 saved pad nets.
  One citation defect was verified and corrected: cached BQ25173 primary
  literature is SLUSDY6 (November2021), not SLUSD97A. Circuit, numeric, source
  and mechanical artifacts are unchanged. Parent refreshed only the affected
  documentation receipt/inventory hashes and the downstream source preservation
  baseline; original239-file cell and90-file source review snapshots are intact.
  Evidence: `.tools/checks/cell-protection-citation-fix/receipt.json`. Both current
  inventories and all257 downstream protected inputs pass. The review does not
  close typical-only interruption time, decaying-current fuse clearing, hot
  resistance/leakage allocations, open-fuse sensing, sidecar fit or physical
  runtime/temperature qualification. No additional review round is required for
  this citation correction.
- Compact rotary collar Phase0 (Astra LOW/standard), completed with failures:
  `node:delegated-task:command%3Amcp%3Aeaab7c50-b35d-4a00-9efc-f2e54928abd4%3Athread-send%3Anova-compact-rotary-cassette-prototype-20261023-1`.
  [Primary sources, calculations and limitations](../../hardware/compact-dmx/rotary-compact-candidate/README.md).
  Parent verified17 artifact hashes. The unchanged IRM10/FPC/TPS25810 path
  misses4.75V in all12 screened corners, even4.72575V in the optimistic stated
  case. The simple fixed-radius Archimedean model changes length±43.589mm;
  this rejects that model, not every clockspring. No speculative shrink CAD
  was generated. A source receptacle also needs D+/D− charger shorting; the
  six-contact sink connector cannot provide it. Phase0 suggests local regulation
  and a USB2-contact source connector, with no compliance/thermal acceptance.
- Constant-length compact mechanism (Astra LOW/standard), completed with
  concrete assembly failures:
  `node:delegated-task:command%3Amcp%3Aeaab7c50-b35d-4a00-9efc-f2e54928abd4%3Athread-send%3Anova-rotary-constant-length-mechanism-20261023-1`.
  [Failed prototype, CAD and receipt](../../hardware/compact-dmx/rotary-compact-candidate/constant-length-mechanism/README.md).
  Parent verified all29 artifact hashes. The path retains1046.167656mm length
  across181 positions, minimum bend R25 and sampled surface gap0.1398mm for
  allocated0.16mm thickness. This is geometry, not elastic equilibrium or cycle
  qualification. Trial envelope is Ø66mm, locked span64.3mm and released
  operating span68.5mm. The saved rotor has a detached backing; fixed clamp
  lacks0.2443mm for its proposed stiffener/gap stack. Six unintended screw/head
  intersections and three unfinished stationary joints remain. Parent reopened
  the saved FCStd, confirmed40 objects/41 closed solids, the disconnected
  backing, all six screw collisions and the clamp shortfall; evidence is
  `.tools/checks/rotary-mechanism-parent/parent-receipt.json`. Captive index
  retention and return spring are incomplete. Assembly acceptance is withheld;
  the25×18mm electronics bay remains a placeholder.
- Concrete collar repair (Astra LOW/standard), completed geometric prototype:
  `node:delegated-task:command%3Amcp%3Aeaab7c50-b35d-4a00-9efc-f2e54928abd4%3Athread-send%3Anova-rotary-mechanism-concrete-repair-20261023-1`.
  [Repaired geometry, assembly sequence and limits](../../hardware/compact-dmx/rotary-compact-candidate/mechanism-repaired/README.md).
  The candidate verifier passes55 artifact hashes,29 preserved original hashes,
  43 connected closed native parts, seven reopened STEP exports,4,446 full pair
  checks with ten bounded thread interfaces,342 tool checks,181 released motion
  positions and13 detents. Captive pin, removable retention cap, spring envelope,
  stiffeners and connected spool/backing are modeled. EnvelopeØ66mm,67.8mm
  locked span/72.0mm released. Physical spring/strength/adhesive/FPC equilibrium
  and endurance are unqualified; the source remains a25×18mm placeholder here.
  Parent reopened all43 single connected closed solids, verified55 artifact
  hashes and recomputed741 neutral component pairs with only the ten bounded
  thread contacts. Four prior frame heads now clear, with radial clearance
  checked separately from their intentional bearing-seat contact. Nominal
  static stiffener gap screens exceed0.055mm. Parent evidence:
  `.tools/checks/repaired-collar-parent/parent-receipt.json`. This closes the
  enumerated geometric repair defects; no actual-board fit or physical acceptance.
- Actual collar/source integration (same Astra LOW/standard child), completed
  geometric prototype; electrical/manufacturing acceptance UNMET:
  `node:delegated-task:command%3Amcp%3Aeaab7c50-b35d-4a00-9efc-f2e54928abd4%3Athread-send%3Anova-collar-actual-source-integration-20261023-1`.
  [Integrated source, retention and finite fanout](../../hardware/compact-dmx/rotary-compact-candidate/collar-source-integrated/README.md).
  Actual27×20×1mm AXIAL-R1 board bytes are unchanged. Proposed complete collar
  envelope isØ66mm, locked span73.17mm/released77.37mm, around the unchanged
  Ø48×142mm core. The source transform is proper-handed: rotationX−90°,
  translation(75,26.1,10). Its supplier-bounding connector body endsX104.17;
  this is not an exact mating datum. Child evidence reports86 connected closed
  solids,18,018 pair checks,181 motion positions,13 detents,1,078 tool checks,
  eight reopened STEP exports,63 artifact hashes and129 preserved inputs.
  Board retention, static developed fanout and external solder/clamp access are
  captured; flex equilibrium/endurance, joints, strength and thermal/USB behavior
  remain unqualified. Parent independently verified63 artifact/129 frozen hashes,
  all86 saved connected closed solids and3,003 fresh neutral physical pairs;
  no unexpected intersections. Parent evidence for both integrations and the
  independent constant-power calculation:
  `.tools/checks/stationary-and-collar-parent/parent-receipt.json`.
  **Integrated source current screen FAILS:** the added14.199mΩ hot tail raises
  the existing80%-efficiency/410mA-VCONN stress model from2.987141A to3.022256A,
  exceeding the2.994611A breaker floor by27.645mA. The proposed16.250mΩ tail
  allocation plus4.964mΩ stationary wires gives3.040273A/−45.662mA margin.
  [Reproducible calculation and input hashes](../../hardware/compact-dmx/rotary-compact-candidate/integration-power-screen/result.json)
  are generated by its adjacent `check.py`; exit0 means the arithmetic and
  expected failure reproduced, not electrical acceptance. These retain the
  conditional source assumptions, not measurements or a coherent measured
  thermal corner. The earlier4.786V port screen cannot establish delivery through this assembly;
  source/current/protection budget correction is required before acceptance.
- Regulated rotary USB source (Sol6.1 high/standard), captured, parent-checked,
  acceptance UNMET:
  `node:delegated-task:command%3Amcp%3Aeaab7c50-b35d-4a00-9efc-f2e54928abd4%3Athread-send%3Anova-rotary-source-regulator-capture-20261023-1`.
  [Circuit, source documents and limits](../../hardware/compact-dmx/rotary-compact-candidate/regulated-source/DESIGN.md).
  Prototype path is stationary IRM20-5 → LV flex → TPS259474 reverse-blocking
  breaker → TPS63070 forced-PWM5.136V → TPS25810 advertising1.5A → full-contact
  USB4105 with passive D+/D− short.30 purchased parts/32 footprints are placed
  top-only on25×18×1mm. Parent verified88 artifact hashes,257 protected inputs
  and14 primary-PDF hashes; fresh actual netlist semantics match, ERC0, DRC4
  connector hole-clearance errors/85 unconnected, and all123 saved numbered
  pad primitives match the real export. Conditional port window4.786–5.336V
  and healthy-case flex current2.453A depend on allocated efficiency/transients;
  stress breaker margin is only7.47mA and converter limits at actual VIN are
  unproved. USB maximum height3.46mm exceeds the old3.2mm target; module lead
  intrudes0.75mm into the mains keepout. The placed port exits negative board Y,
  whereas the current collar assumes axial positive X. No whole-collar fit,
  startup/thermal/reverse/fault/USB acceptance. Parent evidence:
  `.tools/checks/rotary-source-parent/parent-receipt.json`, `board-receipt.json`
  and `mechanical-receipt.json`. Parent reopened32 connected envelope solids,
  checked496 zero-volume pairs and reproduced the0.589mm³ lead/harness clash;
  these are simple package allocations, not vendor-detailed CAD or fit release.
- First targeted source-circuit review (GLM5.3, text-only/read-only), completed:
  `node:delegated-task:command%3Amcp%3Aeaab7c50-b35d-4a00-9efc-f2e54928abd4%3Adelegate-task%3Anova-regulated-source-glm-review-20261023-r1`.
  Frozen90-file snapshot `.tools/reviews/rotary-source-20261023/`, manifest SHA256
  `f31d7795aedeafbda180582c806e5c4f33f6bf4eea988e42dc4ca1a1654a8afd`.
  No new demonstrated electrical defects; actual pin maps,123 pad nets,18 CC
  states and reported voltage/current calculations match the cached sources.
  Parent inspected TPS25810 primary p6:0.65V is the MINIMUM falling threshold,
  not typical as the review nit stated;0.875V is typical. The acceptance check
  now uses stricter recommended logic levels, low<0.63V/high>1.17V, and passes
  at0.4V/~2.491V. Circuit/numeric/PCB artifacts are unchanged; documentation,
  check and receipt inventories were refreshed, with90 frozen review files
  retained. Parent evidence: `.tools/checks/rotary-source-review-disposition/receipt.json`.
  C12 is nominal10nF±10%, so its upper value crosses TI's>10nF recommendation
  for100Ω series damping. Add that resistor in the routed successor rather than
  dismissing the boundary on nominal value alone. This review does not close
  converter limits, thermal/startup, output OVP, upstream flex protection,
  reverse transients, connector process or assembled USB behavior.
- Axial source-board routing (Sol6.1 high/standard), completed AXIAL-R1:
  `node:delegated-task:command%3Amcp%3Aeaab7c50-b35d-4a00-9efc-f2e54928abd4%3Athread-send%3Anova-rotary-source-axial-routing-20261023-1`.
  [Actual routed source and engineering limits](../../hardware/compact-dmx/rotary-compact-candidate/source-axial-routing/DESIGN.md).
  PCB27×20×1mm, four copper layers, top-only34 footprints/32 purchased parts,
  USB+X at PCB-edge datum(27,10,0), component maximum height3.46mm. The25×18mm
  target is unmet. Added R12 is10kΩ in TPS63070's VIN→EN path per§11.1;
  R13 is100Ω in the DVDT capacitor branch. Parent verified69 inventory entries,
  14 primary-PDF hashes and349 protected inputs; fresh actual netlist matches,
  all127 saved numbered pads match, ERC0/DRC4 inherited GCT hole clearances,
  zero unconnected items,582 tracks/92 vias and no rule exclusions. Only the two
  documented signal splits differ from the reviewed source. Parent evidence:
  `.tools/checks/axial-source-parent/parent-receipt.json`. Supplied endpoints,
  land/copper checks and reopened package CAD support routing capture, not
  source current delivery, startup, thermal, USB, fabrication or collar fit.
  Board SHA256 `53b83aa71d1bcd986906509348bc061eb9e334296ddc980340c954eb8305cbcc`.
- Stationary IRM20 carrier/lead integration (same Sol6.1 high/standard child),
  STATIONARY-R1 captured; assembly/installation acceptance UNMET:
  `node:delegated-task:command%3Amcp%3Aeaab7c50-b35d-4a00-9efc-f2e54928abd4%3Athread-send%3Anova-stationary-irm20-carrier-fit-20261023-1`.
  [Saved assembly, sources and process objections](../../hardware/compact-dmx/rotary-compact-candidate/stationary-irm20-integration/DESIGN.md).
  The raised carrier closes the original0.75mm maximum-lead/trunk overlap under
  the enumerated engineering allocations. Child evidence reports54 closed
  solids,1,431 pairs,zero unintended intersections and422 unchanged inputs.
  Minimum lead projection is0.28mm; lead/deck gap0.15mm, film/trunk gap0.075mm,
  body/nominal-bore gap0.465mm. Parent independently verified43 inventory/422
  protected hashes,54 saved closed solids and all1,431 fresh component pairs,
  including eight bounded same-net joints. These are geometric gaps, not
  insulation ratings.
  Broad source pin tolerances leave nominal pins disconnected from carrier lands;
  a validated PTH/solder process is absent. The preformed wire loop collides with
  the intact core during axial insertion. Proposed in-core forming has no proven
  jig, tool access, extraction or process. Do not treat it as a buildable assembly.
  MEAN WELL's cached PCB installation guide explicitly includes IRM and calls
  for5mm below with film and10mm surrounding distance; this tight core does not
  meet that guidance. Its applicability cannot be silently waived based on
  component approvals or short PCB pins.
- Installation feasibility follow-up (same Sol6.1 high/standard child), completed:
  `node:delegated-task:command%3Amcp%3Aeaab7c50-b35d-4a00-9efc-f2e54928abd4%3Athread-send%3Anova-stationary-installation-gate-20261023-1`.
  [Source evidence and dimensional bounds](../../hardware/compact-dmx/rotary-compact-candidate/stationary-irm20-integration/installation-gate/receipt.json).
  Three official technical PDFs provide no explicit alternative construction
  permitting the proposed tight enclosure. The manual includes IRM;27.7mm
  maximum width plus two10mm lateral allowances requires47.7mm, exceeding the
  Ø43mm bore independently of bottom/pin-mating interpretation. Component
  listing is not a construction report or reduced-clearance permission.
  **IRM20/Ø43mm-bore architecture BLOCKED for production.** Stop R1 assembly/jig
  development. Conservative72.9×47.7×44mm reservation has a64.89mm rectangular
  cross-section diagonal; that is a comparison, not an approved minimum or
  adopted resize. Parent independently verified five inventory hashes,466
  preserved inputs,three primary-PDF hashes and the lateral/diagonal arithmetic.
  Evidence: `.tools/checks/stationary-and-collar-parent/installation-gate-parent.json`.
  A permitted alternative elsewhere or in unavailable approval conditions remains
  unknown; no vendor contact or safety waiver is inferred.
- Alternative power-architecture screen (same Sol6.1 high/standard child), completed:
  `node:delegated-task:command%3Amcp%3Aeaab7c50-b35d-4a00-9efc-f2e54928abd4%3Athread-send%3Anova-compact-power-architecture-screen-20261023-1`.
  [Two-family comparison, primary sources and obligations](../../hardware/compact-dmx/rotary-compact-candidate/power-architecture-screen/README.md).
  RECOM RAC20-12SK/277 and TRACO TMLM20112 have dimensioned primary drawings
  but no retrieved applicable construction conditions establishing a permitted
  compact system enclosure. Neither is selected; permission remains unknown.
  Parent verified13 inventory/473 protected hashes,seven primary PDFs and all
  nine12V constant-power cases independently. Evidence:
  `.tools/checks/power-architecture-parent/receipt.json`. Under the same80%
  efficiency assumption, IRM20-12 parameter stack11.41V gives1.110526A versus
  3.040273A for the full-resistance5V stress case. This is a conditional comparison,
  not efficiency/startup/current/thermal qualification or a transferable breaker
  selection. The whole-carrier81×52×44mm reservation excludes remaining harness,
  film, mounting and thermal allowances; no new enclosure fit is asserted.
- Protected12V-input rotary source capture (Sol6.1 high/standard), completed as
  S12-R1, a partial unrouted prototype; protection acceptance UNMET:
  `node:delegated-task:command%3Amcp%3Aeaab7c50-b35d-4a00-9efc-f2e54928abd4%3Athread-send%3Anova-rotary-12v-protected-source-capture-20261023-1`.
  [Exact circuit, source evidence and gates](../../hardware/compact-dmx/rotary-compact-candidate/source12-candidate/DESIGN.md).
  Stationary TPS259474 protects the FPC input; rotating TPS62135 forced-PWM buck
  feeds TPS25940 output disconnection, monitored independently by TPS3700, then
  TPS25810/USB4105 advertising1.5A. The static barrier interrupts sustained12V;
  maximum transient voltage/energy and USB-pin survival remain unproved. Its
  latest precision trip5.476745V leaves only2.7905µC to5.5V on120µF at reference
  tolerance. Typical propagation and delayed current limits cannot establish a
  guaranteed bound. The higher internal OVP is not a5.5V clamp.
  Parent verified73 inventory hashes,22 source hashes, receipt SHA
  `51393c2a663f8cc206af64d4d0aa09d541832f1a5ac542f7a93bc06f95e2e519`,
  and1122/1123 protected inputs; the one difference is the recorded parent-owned
  package README update. Fresh actual CLI export matches except design/date;
  ERC0, rotating four retained GCT hole-clearance findings/120 unconnected,
  stationary zero geometric findings/22 unconnected, no tracks/vias. All189
  saved numbered pads match185 unique exported nodes. Parent independently
  recomputed conditional4.783–5.304V port window and1.318556A worst modeled
  FPC current against1.497305A breaker floor, a178.749mA margin. These depend on
  unmeasured efficiency/resistance/ripple allocations. Evidence:
  `.tools/checks/source12-parent/receipt.json` and `arithmetic.json`.
  Rotating32×26×1mm/45 footprints and stationary24×16×1mm/12 footprints are
  allocations, not collar/pod fit. Maximum top3.46mm, plus external clamp/access
  reservations. The inherited100nF MPN is provisional. Startup, thermal,
  effective capacitance, reverse/unload and FPC fault coordination remain open.
- S12 output-fault-energy engineering pass (Sol6.1 high/standard), completed as
  PE-R1; protection remains UNMET and no new circuit was captured:
  `node:delegated-task:command%3Amcp%3Aeaab7c50-b35d-4a00-9efc-f2e54928abd4%3Athread-send%3Anova-source12-protection-energy-20261023-1`.
  [Failure-state table, two remedies and qualification requirements](../../hardware/compact-dmx/rotary-compact-candidate/source12-protection-energy/README.md).
  LT4363 series protection and TL431BI/TS820 crowbar implementations both miss
  the unchanged S12 non-nuisance/ceiling window using the stated reference
  envelopes; retuning or another temperature grade could alter that static
  result but would not supply missing dynamic bounds. This is not proof that
  no protection architecture can work. Parent verified16 inventory hashes,
  13 source-record hashes, all73 unchanged S12 inventory entries and receipt SHA
  `3661df8358ec6681410eea14f584beb670e29a88a395e468fe47a684a3590428`.
  Parent independently reproduced the two ideal-gain interval failures and
  2.7905µC/15.3155µJ reference headroom, or0.731µs at the assumed3.8176A.
  Evidence: `.tools/checks/source12-energy-parent/receipt.json`. Neither the
  capacitor minimum nor that current is a qualified fault bound. Primary-web
  excerpts are identified as excerpts, not complete downloaded PDFs.
  Missing inputs include maximum local/source injection and parasitics,
  startup/near-threshold full-chain response, effective capacitance and
  pass-device/shunt interruption/SOA coordination. The numbered plan names
  required data and a proposed later bench matrix; no hardware activity or
  qualification is authorized or represented by this receipt. No third remedy,
  new area/height, source-board change or routing followed this bounded pass.
- Stationary source-pod allocation (Astra LOW/standard), completed as an oversized
  comparison; compactness and construction acceptance UNMET:
  `node:delegated-task:command%3Amcp%3Aeaab7c50-b35d-4a00-9efc-f2e54928abd4%3Athread-send%3Anova-stationary-source-pod-allocation-20261023-1`.
  [Editable allocation and limits](../../hardware/compact-dmx/rotary-compact-candidate/stationary-source-pod/README.md).
  Overall330×89×72mm includes a128×82×62mm source pod, the retained142mm
  tube and two24mm connector placeholders. Parent verified27 artifact hashes,
  166 protected inputs and four source hashes; independently reopened43 closed
  connected native solids and all three STEP exports, checked36 physical pairs
  without intersections, source planning distances and the whole envelope.
  Evidence: `.tools/checks/stationary-pod-parent/receipt.json`. Child reports239
  spacing checks and4344 USB comparisons across181 angles; parent inspected the
  top drawing but did not independently repeat that sweep. Carrier retention,
  primary/secondary terminal transitions and final radial FPC-clamp connection
  remain unresolved. No actual connector variant, new12V board fit, thermal or
  mains construction acceptance follows from this allocation.
- Combined compact allocation (Astra LOW/standard), completed as a failed
  integration comparison; no accepted compact product envelope:
  `node:delegated-task:command%3Amcp%3Aeaab7c50-b35d-4a00-9efc-f2e54928abd4%3Athread-send%3Anova-combined-compact-allocation-20261023-1`.
  [Editable comparison, exact collisions and limits](../../hardware/compact-dmx/rotary-compact-candidate/combined-compact-allocation/README.md).
  Inline270×89×72mm removes60mm/18.18% bounding volume from the330mm baseline;
  offset152×150×72mm has much greater transverse bulk and an unfinished neck.
  Both retain unqualified connector volumes. The inline CAD uses the old source
  as comparison geometry; S12 is a dimensional screen only. Its transformed
  clamp reachesR33.370796 before a wall, exceedingØ66. A1mm wall/0.25mm allowance
  suggestsØ69.241591 and275mm length; these are arithmetic, not completed CAD.
  Parent verified32 artifact/202 protected-input/four source hashes, inspected
  the top drawing, independently reopened140 closed connected native solids
  and108/27 STEP solids, and reproduced all eight named intersection volumes.
  Parent also reproduced18.18% shortening and the clamp-radius arithmetic;
  evidence: `.tools/checks/combined-compact-parent/receipt.json`. Child reports
  2937 pair records and zero USB intersections across181 angles. Eight
  unintended intersections remain: L/N branches, N/carrier and six LV/clamp
  hardware pairs. The plus lead remains0.581013mm from its tail. Four pin passages
  are missing; seven endpoint contacts and four source-reservation crossings
  remain unqualified interfaces. Valid solids do not close these failures.
- Compact interface repair and actual S12 fit (Astra LOW/standard), completed
  as CIR-R1 bounded mechanical prototype; compactness/manufacturing acceptance UNMET:
  `node:delegated-task:command%3Amcp%3Aeaab7c50-b35d-4a00-9efc-f2e54928abd4%3Athread-send%3Anova-compact-interface-repair-20261023-1`.
  [Editable assembly, exact changes and limits](../../hardware/compact-dmx/rotary-compact-candidate/compact-interface-repair/README.md).
  Both frozen S12 boards are included byte for byte:57 footprints and189 numbered
  pad features. Trial collarØ70, coreØ48×87mm; the275×91×74mm whole comparison
  retains the source-pod allocation and two24mm connector blanks. It is not an
  accepted compact product envelope. Board edge retention, removable axial gate,
  static fanout shoes, source-wire paths and independent stop return bridge are
  now explicit geometry. Nominal repairs do not qualify their materials/process.
  Parent verified86 artifact,241 protected-input and seven source hashes, plus
  receipt SHA `a02ab89bdc101d2cbb9db31e49d2724ac45c86ffe5dbebb604c8a5fd5cdfba6c`.
  Parent inspected the dimensioned section and independently checked both
  actual saved-board contracts:57 footprints/189 numbered pads, positions,
  sizes, drills, layers, values and netlist nodes; both boards remain unrouted.
  Parent independently reopened360 valid closed single-solid native objects,
  checked189 transformed pad centroids/net labels, recomputed2007 selected
  support/wire pairs with12 bounded intended contacts and no unexpected overlap,
  and confirmed the four repaired wire shapes stay insideR24. Evidence:
  `.tools/checks/compact-interface-parent/receipt.json`. The six STEP reopens and
  full181-position sweep remain child evidence; the redundant parent STEP import
  was stopped after180s and does not count as a parent reopen. The current static fanout/wire paths increase the
  retained conditional input-path model from178.298 to184.389mΩ; independently
  solving the constant-power corner gives1.319524A and177.781mA margin to the
  modeled breaker floor. This reuses unqualified efficiency/contact/wire
  assumptions; it is no transient, fault or ampacity acceptance. Arithmetic:
  `.tools/checks/compact-interface-parent/path-budget.json`.
  The child reports360 closed single-solid objects, six reopened STEP exports,
  181 motion/USB positions,13 locking positions and16 tool screens with no
  unintended overlaps in the defined checks. Object counts include reserves,
  alternate poses and lands, not manufactured-part counts. Named electrical
  contacts and source-reservation crossings remain unqualified construction
  interfaces. S12 is unchanged and unrouted; source protection, carrier retention,
  mains construction, real connector mating, wire/flex life, strength, thermal
  performance and compactness acceptance remain open. No build release follows.
- Cylindrical stationary-source repack (Astra LOW/standard), CYL-R1 completed
  as phase0 HOLD, no new assembly CAD/STEP:
  `node:delegated-task:command%3Amcp%3Aeaab7c50-b35d-4a00-9efc-f2e54928abd4%3Athread-send%3Anova-cylindrical-source-repack-20261023-1`.
  [Screen, sources and limits](../../hardware/compact-dmx/rotary-compact-candidate/cylindrical-source-repack/README.md).
  Parent verified19 artifact/403 protected/three source hashes and receipt SHA
  `51fba486eb780295c9ddf87e8d69ce0874910ce091548121cb3a9e0f33972975`.
  Those403 inputs matched before this parent checkpoint edit; afterward402/403
  match, with only this canonical document intentionally changed. The original
  frozen hashes remain untouched; the exact delta is recorded in parent
  `post-doc-integrity.json`. All19 task artifacts remain unchanged.
  The single arrangement allocates a76.2mm cylindrical body,88mm source bay,
  21.330729mm neck and unchanged87mm core. Its297.130729mm classic panel planning
  length includes60.8mm rear connectors and40mm terminal/tool space; the original
  CIR275 includes only48mm end blanks. Thus the reported22.13mm length increase
  and6.84% volume reduction compare unlike boundaries and do not establish that
  a cylinder is unhelpful. Applying the same60.8/40mm end allocations to CIR gives
  327.8mm versus297.13mm: a conditional30.67mm/21.84% box-volume reduction, not
  finished product dimensions. Actual access sufficiency and overlap remain
  unresolved; this normalization is a sensitivity model, not an accepted fit.
  Parent reproduced the film tolerance gap−0.025814mm. The reported neck gap
  −0.039478mm is only a radial centerline screen; it omits the axial extent of
  a round section normal to the wire tangent through the sloped bore. Parent
  independently constructed a point on theØ5.5 clearance-corridor surface with
  radial penetration0.550867mm. This proves corridor interference, not physical
  Ø4.5 wire contact: the sampled physical-wire surface retains0.042113mm, which
  is not a complete fit proof. Do not prescribe a0.04mm relief as sufficient.
  Evidence: `.tools/checks/cylindrical-source-parent/check.py` and `receipt.json`.
  Child reports181 source-bay-only axial separation screens against frozen
  CIR geometry, not whole-assembly motion acceptance. Carrier retention,
  recentered pin connections, insulation/film support, complete terminals,
  access and source electrical/manufacturing qualification remain open.
- Cylindrical source correction/construction (Astra LOW/standard), CYL-R2
  completed as a constructed partial prototype, HOLD:
  `node:delegated-task:command%3Amcp%3Aeaab7c50-b35d-4a00-9efc-f2e54928abd4%3Athread-send%3Anova-cylindrical-source-correct-geometry-20261023-1`.
  [Editable assembly, corrected comparison and construction limits](../../hardware/compact-dmx/rotary-compact-candidate/cylindrical-source-repair/README.md).
  Source bayOD77/ID71×88mm and27mm neck retain the87mm CIR core and frozen S12
  boards. Actual carrier posts/ears/screws, upper capture ribs, film supports,
  primary trunk/branches and rerouted secondary-to-J0 contacts are now drawn.
  The primary fuse remains an explicit unbuilt4mm centreline/1mm conductor gap.
  Parent verified46 artifact/222 protected/three source hashes before this
  checkpoint update, plus receipt SHA
  `0cc43cc3a2596b44cfa81834fe26f41583948954af58fdb4d292100895d1d61f`.
  Direct222 inputs and all46 artifacts still match after this update. The
  inherited CYL-R1 canonical-document delta changes again with this parent
  record, so the live strict historical verifier detects it; the frozen source
  manifests/receipts and60-file review snapshot remain untouched. Exact current
  hashes are in parent `post-doc-integrity.json`, not refreshed source manifests.
  Parent independently reopened356 valid closed single-solid native objects,
  recomputed all three fullØ5.5 corridor BRep containments in the tolerance-
  reduced bore (zero outside volume; minimum distance0.487627mm), checked film
  containment/corner clearance0.374186mm and matched classic planning arithmetic:
  302.8×77×77 versus327.8×91×74mm,25mm/18.669% conditional box-volume reduction.
  Equal access allowances remain unqualified; these are not finished envelopes
  or achieved compactness. Evidence: `.tools/checks/cylindrical-repair-parent/`.
  Child reports317 CIR objects unchanged,150 reopened STEP solids,9086 selected
  pairs/14 bounded positive contacts,181 stops/13 locks/84 released-pin/spring
  pairs and tool/insertion screens. Parent did not repeat those full checks.
  The earlier film/corridor failures are corrected in the defined CAD scope.
  Mains construction remains unaccepted: supports/ribs/screws/leads cross the
  installation reservation, including ribs0.25mm above the module versus the
  inherited10mm surrounding allowance. Neither material choice nor a large
  enclosure grants a mounting exception. The neck/source/core joints are
  unbuilt; local relief leaves0.970mm nominal/0.670mm allocated wall with no
  strength acceptance. Wire bends, film handling, fuse/insulated terminations,
  connector/cord ends and physical electrical/thermal/endurance qualification
  remain open. No production or full electrical continuity is claimed.
- Focused CYL-R2 source-construction review (**GLM Flash**, owner-requested
  replacement), completed2026-10-24, one bounded read-only/text-only pass:
  `node:delegated-task:command%3Amcp%3Aeaab7c50-b35d-4a00-9efc-f2e54928abd4%3Adelegate-task%3Anova-cyl-r2-construction-glm-flash-review-20261023-r1`.
  Owner correction, verbatim: “use GLM Flash, that subagent is broken”. The
  previous GLM5.3 task `nova-cyl-r2-construction-glm-review-20261023-r1` has no
  usable review receipt; status retrieval returned “The requested terminal task
  result is unavailable.” Its cancellation was acknowledged as
  `cancel_requested`; no verdict is inferred. The replacement was accepted
  running on `claudeAgent` / `zai/glm-5.3-flash`, options empty, with the same
  original brief, findings/responses, known gates and unchanged snapshot.
  Snapshot `.tools/reviews/cyl-r2-20261023/`,60 pinned files, manifest SHA
  `c22ce5ad063deac7c9ba919724ad94d4c782e4f329dabcc3aaa6d14ae455757f`.
  Reviewer verified60/60 hashes, source text, comparison/corner arithmetic,
  count identities, motion-certificate structure and drawing/proof consistency.
  It found one confirmed minor assembly defect: four closure-driver envelopes
  collide with the installed upper shell. `build.py` placesØ5 tools at
  X−110/−32,Y±32,Z4.5..40.5, but provides no shell access passage; `access.py`
  checks only module/carrier/film with the upper half absent. At the tool
  centreline, parent independent arithmetic places the shell wall at
  Z15.370426..21.406775, confirming the blocked path. The stated closure step
  cannot be accepted using an upper-half-removed check.
  No other new defects were confirmed. CAD/BRep/pair/STEP execution was outside
  the review's text-only scope; disclosed mounting/insulation, neck/fuse/terminal,
  connector and qualification gates remain open. Parent disposition evidence:
  `.tools/checks/cylindrical-repair-parent/review-disposition.json`.
- Closure-driver access correction (Astra LOW/standard), CAF-R1 completed:
  `node:delegated-task:command%3Amcp%3Aa336df30-781c-4f7d-8ab1-a5a85051a526%3Athread-send%3Anova-cyl-r2-closure-driver-fix-20261024-1`.
  [Original correction and preserved checks](../../hardware/compact-dmx/rotary-compact-candidate/closure-access-fix/README.md).
  Four Ø5.5 passages remove the original127.758..127.838mm³ driver overlaps;
  355 other shapes, seats and placements remain unchanged. Parent verified27
  artifact/49 frozen input hashes. CAF-R1's author-run1,356 installed-driver,
  334 lid-insertion and1,352 screw-insertion checks pass;150 STEP solids reopen.
  Parent then found accidental zero-distance contact at the passage's Z4.5
  start plane, at an end-ring ledge. Zero volume alone did not establish a
  positive tolerance margin. CAF-R1 remains preserved as intermediate evidence.
- Parent narrow margin correction, CAF-R2:
  [Editable native/STEP, drawing and receipt](../../hardware/compact-dmx/rotary-compact-candidate/closure-access-margin-fix/README.md).
  Lower the four passage starts from Z4.5 to Z4.0, retaining Ø5.5 and Z41.5 exit.
  Existing Ø5 tools remain at Z4.5..40.5. Actual whole-tool-to-upper gap is now
  0.25mm nominal, with zero intersection; four8.042477mm² bearing seats and all
  material below Z4.0 remain intact. Only the fixed upper loses0.349388mm³;
  355 other saved BReps and all356 placements are preserved. Proposed radial
  tolerance residual0.05mm and axial residual0.30mm are unqualified allocations.
  The ports are open holes: sealing/caps, access protection and wall strength
  remain open. This closes the review finding geometrically, not product
  acceptance. Earlier full insertion/pair checks are retained by the strictly
  subtractive delta, not claimed as rerun. No further review round is active.
  Final local verification:18 artifacts plus receipt inventory and77 frozen
  inputs pass; saved-BRep check preserves355 other shapes/all356 placements;
  STEP reopens150 valid closed solids. PDF rendered and visually inspected;
  Python compilation, concept JavaScript syntax and `git diff --check` pass.
  Receipt SHA `fbe403173b1d392c35c0289382674bd006cfa0ecce7eeab3c3e15619934543fc`;
  native SHA `066417cd8d07541535b009c4af07e440b843ecec828b333f04a5c6d5c6b4b79b`.
  Parent evidence: `.tools/checks/closure-access-parent/caf-r2-verification.json`.
- Bounded compact-source reference screen (Astra LOW/standard), CSR-R1 completed:
  `node:delegated-task:command%3Amcp%3Aa336df30-781c-4f7d-8ab1-a5a85051a526%3Athread-send%3Anova-compact-reference-source-screen-20261024-1`.
  [Two-reference matrix, original assets and limits](../../hardware/compact-dmx/rotary-compact-candidate/compact-source-reference-screen/README.md).
  Exactly PMP11295 RevD and TIDA-01560 E1 were inspected. Neither establishes a
  smaller complete source/enclosure or an accepted replacement. TIDA is retained
  only as a conditional custom12V reference direction, not a selected circuit.
  Its native board outline is66×50mm; exact Würth750343769 drawing gives a
  maximum29×21.5×12.4mm transformer body. The2.03mm lead projection is a minimum,
  not maximum. Only17/50 native footprints have embedded models; complete maximum
  assembly height, installed safety spacing and thermal construction are unknown.
  TIDA board area3300mm² exceeds the retained IRM body1465.33mm²; the old4212mm²
  planning carrier footprint is not a universal minimum. A lower transformer
  alone does not establish a smaller complete barrel or permitted construction.
  Parent independently recomputed the pinned native coordinates and hot-path
  resistance0.1843885063Ω; visually checked transformer and E1 assembly drawings
  and read guideTIDUDS3 table1. At retained load/current/efficiency allocations,
  the direct5V path needs source-low5.387164V for4.75V at the port. No5.4V source
  is selected. TIDA's12V/1.125A rating is below the conditional1.241344A overload
  calculation by116.344mA. Conditional normal margin is not startup/fault proof;
  the spare3.3V winding cannot simply be reassigned. Source upper/lower regulation,
  overload collapse, S12 output-energy interruption and installed construction
  remain unresolved. PMP measured results do not qualify this rotary power path;
  its complete outline/height evidence was not retrieved.
  Verified17 artifact and38 source-file hashes;23/24 frozen inputs match exactly.
  The sole difference is the explicitly recorded concurrent parent canonical-doc
  change, not a source or candidate mutation. Receipt SHA
  `13128c2e091c60624e595738864cb5ce9ec110674dabff438699bb03428a4840`.
  Parent evidence `.tools/checks/compact-reference-source-parent/receipt.json`.
  Existing boards/CAD/source buses remain unchanged; no new fit model or circuit
  was captured. Resource-use restrictions and transformer revision remain open
  obligations. This bounded screen is complete; no follow-on source-family
  search, vendor contact, procurement or implementation task is active.
- Actual mains-connector source contracts (Sol6.1 high/standard), completed as
  CI-R1 reference data; no complete end assembly is qualified:
  `node:delegated-task:command%3Amcp%3Aeaab7c50-b35d-4a00-9efc-f2e54928abd4%3Athread-send%3Anova-mains-connector-interface-sources-20261023-1`.
  [Exact parts, mating map, original CAD and limits](../../hardware/compact-dmx/connector-interface-candidate/README.md).
  Six chassis candidates and six specified external mates have official STEP
  files. Parent verified138 inventory/42 source/96 protected-input hashes and
  receipt SHA `58dd649c753c43b13ae55ac53ae8598ee6b020e4b91a6c35f7d42672c3014f5a`.
  Parent independently reopened all12 model identities, checked six planar
  mounting shoulders and tessellated bare rear-depth comparisons; inspected
  representative classic, TRUE1 outlet and NEMA outlet primary drawings.
  Evidence: `.tools/checks/connector-contract-parent/integrity.json` and `cad.json`.
  Nominal drawing rear depths: NAC3MPXXA/B30.4mm each; NAC3MPX-TOP31.2 and
  NAC3FPX-TOP32.8mm; Leviton5278-C45.3 and5279-C43.6mm, both withØ63.5 flanges.
  All exceed the24mm end blank before terminations. Pair rear-depth differences
  versus two24mm blanks are12.8/16.0/40.9mm respectively, not total housing growth
  or fitted dimensions. The flanged NEMA set is a comparison, not a replacement
  for the intended approved molded-cord architecture; exact cords remain open.
  Classic A/blue inlet and B/gray outlet require the correct keyed cable mates
  and a B-to-A fixture jumper, not direct B-to-A mating. Legacy combinations
  do not gain load-breaking capability from a newer cord mate. NEMA locking
  rotation does not imply a locking mains connection.
  The two TRUE1 chassis imports are invalid as whole shapes;5278-C and several
  mates are open/surface geometry. They remain unchanged reference data, not
  Boolean-fit acceptance. Classic CAD rear extents differ from drawings by
  about0.35/0.45mm. Installed mated datums, terminal/sleeve/wire/tool envelopes,
  model revision/validity and complete construction remain unresolved. Astra
  received these constraints; any retained24mm blank must stay a comparison.
- Neutrik installed mating-envelope pass (Sol6.1 high/standard), completed as
  CME-R1 HOLD for all four pairs; no installed CAD pose accepted:
  `node:delegated-task:command%3Amcp%3Aeaab7c50-b35d-4a00-9efc-f2e54928abd4%3Athread-send%3Anova-neutrik-mated-envelope-20261023-1`.
  [Source probes, exact gaps and contracts](../../hardware/compact-dmx/connector-mating-envelope/README.md).
  Parent verified58 inventory hashes,233 directly protected files,28 reused
  sources/four added exact mate drawings, and receipt SHA
  `57dc8d71e3b762b104bacafbdaa6bf25a45712400394b0695dbb291fc4b6b4f6`.
  The inherited CI-R1 check remains95/96 with the parent-owned canonical-document
  delta preserved. Evidence: `.tools/checks/connector-mating-parent/integrity.json`.
  Child checked eight unplaced references and eight isolated plane probes;
  panel shoulders/body axes do not establish axial seating, locked clocking,
  contact overlap, latch travel or installed envelopes. Parent did not promote
  those probes to mating acceptance. Added drawing references give variable
  standalone lengths79–82.5mm classic/77–80mm TRUE1, not installed projections.
  Drawing/model identity discrepancies are retained. No paired STEP, new parts,
  terminal envelope or NEMA substitution was produced.
  A full standalone-body reserve can be a provisional packaging allowance, but
  cannot qualify locked/unlocked, latch or hand access. Astra received this
  limit; independent internal-interface repair continues. Required data are a
  labeled installed datum/section with stop, locked key/latch state, play and
  contact engagement, plus exact insulated terminal/sleeve/tool/wire envelopes.
  This bounded lookup ends here; no repeated catalogue search or outreach is
  implied. Manufacturer contact and physical characterization remain unperformed.
- Protected25 sidecar placement integration (Astra LOW/standard), completed
  conditional geometric candidate; electrical/physical acceptance UNMET:
  `node:delegated-task:command%3Amcp%3Aeaab7c50-b35d-4a00-9efc-f2e54928abd4%3Athread-send%3Anova-sidecar-protected25-placement-20261023-1`.
  [Merged capture, board, relief and limits](../../hardware/compact-dmx/eda/buffer-fit-candidate/protected25-placement/README.md).
  Adds the14 captured protection parts without duplicating the existing charger.
  The saved pre-fuse net contains only C23.1,F101.1,R101.1; charger IN and its C7
  bypass move behind U103. Existing charge-disable and downstream CAP_POS
  branches remain; feedback R20/R21 use captured22.2k/10k0.1%10ppm values.
  Parent verified80 artifact/194 frozen hashes and fresh actual CLI export,
  ERC0/DRC0 with485 unconnected items and zero tracks. All178 original
  placements/673 pad geometries and all459 connected exported power/protection
  pins match. Five inherited ignored DRC categories remain unchanged; zero
  violations is not unrestricted fabrication acceptance.
  Parent reopened40 connected closed solids and STEP solids, recomputed780
  pairs with four bounded screw engagements only, and verified25 source solids
  unchanged. The base alone loses10.944mm³ inside the specified3.8×7.2×0.4mm
  relief; outer98×34×24mm envelope remains. Nominal fuse/base gap is0.434mm;
  the XY±0.25/down0.20mm engineering envelope remains clear by0.18mm.
  Remaining1.6mm floor strength, creep/warp and process capability are unqualified.
  Parent evidence: `.tools/checks/protected25-parent/boardcheck.json`,
  `cadcheck.json` and `integrity.json`. Board SHA256
  `8956ca784d8f61f8a350c47510adce9011edc46a3dca845c69121b468f0af81f`.
  Cell-land/fuse distance11.7338mm is a straight-line lower bound, not a routed
  unfused length. Distributed bypass/control parts still need actual routing.
  [Equal-scale fuse fit section](protected25-fit.html) shows the local relief and
  limits. The visual handoff's obsolete15F/500mA claims are corrected to the
  current25F/qualified1.5A direction, with historical barrel geometry labeled.
  Light728px/dark360px fit previews and the full handoff preview had no console
  errors; rotation and three variant controls were exercised. Evidence:
  `.tools/checks/protected25-parent/visual-check.json`.
  Turnoff/overshoot, fuse clearing, healthy10s, cell forming/vent, RF/termination/
  USB and production qualification remain open. Baseline files are unchanged.
- Focused protected25 integration review (GLM5.3), **failed before findings**:
  `node:delegated-task:command%3Amcp%3Aeaab7c50-b35d-4a00-9efc-f2e54928abd4%3Adelegate-task%3Anova-protected25-integration-glm-review-20261023-r1`.
  Provider result: “Claude API rate limit reached. Try again later.” No review
  approval or no-defect verdict is claimed. Pinned snapshot:
  `.tools/reviews/protected25-20261023/`,281 files, manifest SHA256
  `baf2dc6e59345f73503dc6f243db12e680b99fc10f4cb3350c04154d2aea58a5`.
  Review scope is the actual electrical merge and local relief, with previously
  disclosed protection limits retained. Independent review remains pending;
  avoid repeated calls to the saturated provider. Parent checks above remain
  valid as the bounded evidence, not an independent review substitute.

Fixture research is complete only for source breadth: four models across ETC,
CHAUVET and GLP, fetched official3D assets with pinned hashes.
[Source manifest and original task receipts](fixture-reference-manifest.md).
ETC DWG conversion had unsupported/missing-body warnings; the bounded CHAUVET
conversion produced 82 empty solid bodies. GLP's original-coordinate rendering
is coherent: loose B-spline bounds caused the earlier apparent discrepancy and
do not establish an exploded model. Its two nominal Ø22.20 mm mounting features
are 86.00 mm apart, with local lands at source Z=58.00 mm. Socket identity,
mating planes and recess/protrusion remain unknown, so these dimensions cannot
support a product clearance overlay. No universal fit or adjacent-connector
clearance claim. Original source-fetch task and third-maker follow-up are
recorded in that manifest.

Required before production: cold-start resolution; system DMX ESD qualification
and placed termination/access; final dual-band antenna/RF layout and tuning;
full electrical integration, actual footprints/PCB routing/DRC and fabrication
outputs; cap restraint and tolerance/thermal/runtime measurements; detailed lock/
cassette/endcap/harness/strain-relief design; multi-fixture CAD overlays and
physical fit; mains safety/thermal/EMC and dynamic-wire qualification. A roughly
Ø60 flex cassette remains an investigation target, not a complete barrel design.

The bounded compact-source reference screen is complete. No screened reference
supports reducing the retained product envelope. Do not substitute a naked board
or transformer height for the complete source/mains/connector construction.
The next necessary engineering work is a single architecture's supported source
installation, complete assembly profile and normal/overload/startup/fault budget,
including S12 output response and energy requirements, before another housing
resize or source-board routing. TIDA is a conditional reference only; no custom
converter or revised bus/circuit has been selected or implemented. Typical data
and reference pre-compliance do not establish product guarantees.

GLM Flash's focused review is complete; CAF-R2 resolves its single demonstrated
assembly defect geometrically. Prior film/corridor and closure checks retain
saved-CAD evidence. Source/neck/core attachments, primary fuse/insulated terminals
and permissible mounting/lead/film construction remain unfinished or unapproved.
Do not detail production tooling around unapproved reservation crossings. The
302.8mm matched planning comparison is not an accepted compact product size.
CI-R1 supplies connector contracts; CME-R1 remains HOLD for installed mating,
latch and terminal geometry. Current12V/S12 remains an unrouted prototype.
Protected25 retains parent merge/geometry evidence, but independent review and
a healthy10s minimum remain unqualified. These are separate candidates, not a
released integrated assembly. RDM loader implementation is later software scope.
No delegated work or review is active. No procurement, vendor contact, hardware
qualification is represented by this checkpoint. Publication authority is now
explicitly granted for the saved development checkpoint above.

Fixture metrology follow-up completed (Sol6.1 high/standard), task
`node:delegated-task:command%3Amcp%3Aeaab7c50-b35d-4a00-9efc-f2e54928abd4%3Adelegate-task%3Anova-fixture-panel-metrology-20261022-r1`,
changed only `hardware/fixture-fit/measurements/` and the source manifest. The
[measurement receipt and renders](../../hardware/fixture-fit/measurements/README.md)
retain source entity IDs, unchanged coordinates, units and interpretation limits.
Parent inspected the base and selected-feature renders and checked the nominal
feature arithmetic against the receipt. All eight checked source hashes remain
unchanged. No fixture overlay or product geometry change resulted. The next
useful source is an installed I/O assembly or dimensioned interface drawing
identifying socket parts and mating datums; neutral STEP/IGES would bypass the
demonstrated ETC/CHAUVET conversion barrier.
