# NOVA compact hardware revision B — RFQ / DFM package

Canonical requirements, correction history, sources and release gates:
[design](../../docs/hardware/DMX_Dongle_and_Power_Barrel.md).
This is an **unreleased prototype-development package**, not production instructions.

Latest owner requirement: normal operation needs a5V USB-C source advertising
at least1.5A, including the NOVA-LINK barrel. Existing Rev C and the completed
`eda/power-service/separated-candidate/` capture use the superseded500mA basis.
They are retained comparison designs, not implementations of the new source
qualification. The [qualified-source candidate](eda/power-service/qualified15-candidate/DESIGN.md)
captures hardware CC qualification and separate charger/backup circuitry.
Parent checks confirm zero ERC violations and nominal two-sided placement of
all137 candidate footprints alongside the original37 parts, within the proposed
flush-port board outline. DRC reports0 geometric violations and452 unrouted
connections. Its749.96mm² core courtyard sum exceeds the old150mm² reservation;
the existing case is unchanged. The explicit aged-ESR example provides9.73s,
below the10s requirement. Startup, cell-fault protection, thermal behavior and
routing remain open. The review's startup-blocking U40 mux-mode connection is
corrected to TI's MODE=VIN1 priority configuration. Parent verified the one-pad
net change, fresh KiCad exports and source-table regressions reproducing both
original failures. Physical startup and source-transition acceptance remain
open. This separate candidate is not included in baseline package acceptance.

The [25F buffer proposal](eda/buffer-fit-candidate/README.md) is the selected
development basis for addressing the15F runtime shortfall. A local PCB aperture
and lower cradle retain the98×34×24mm case; independent checks reproduce16.34s
under the stated aged-capacitance/ESR and efficiency assumptions. Nominal25mA
recharge takes43.3min before tail. The [editable assembly prototype](eda/buffer-fit-candidate/integrated25/README.md)
has a real rounded PCB aperture, proposed formed leads/lands, liners and positive
lid retention. Parent saved-board/CAD checks pass; allocated cell/PCB clearance
is0.178mm. Lead forming, vent path, solder/process and retention strength remain
unqualified. [Independent cell protection](eda/cell-protection-candidate/DESIGN.md)
is captured separately. The bounded GLM review found no new electrical defects;
its sole citation correction is recorded in the canonical hardware checkpoint.
The conditional hot-fuse screen is13.26s,
with interruption/clearing bounds still open. The [protected25 integration](eda/buffer-fit-candidate/protected25-placement/README.md)
places the14 added parts and merges the actual power/protection schematic.
Parent fresh CLI checks give ERC0/DRC0 with485 unconnected items;40 saved closed
solids/780 pairs pass nominal geometry. Fit requires a proposed0.40mm local base
relief, leaving1.60mm floor within the unchanged external envelope. Strength,
unfused routing and process capability are unqualified. Focused independent
review hit the provider rate limit and remains pending. Routing, cold/runtime
measurements and manufacturing qualification remain open.


The [repaired rotary collar](rotary-compact-candidate/mechanism-repaired/README.md)
passes its geometric prototype checks atØ66×67.8mm locked/72.0mm released.
Parent reopened43 connected solids and recomputed741 neutral component pairs
without unintended intersections. The [routed axial USB source](rotary-compact-candidate/source-axial-routing/DESIGN.md)
is27×20×1mm with no unconnected items and four retained connector hole-clearance
errors. The [actual-board collar integration](rotary-compact-candidate/collar-source-integrated/README.md)
isØ66mm,73.17mm locked/77.37mm released, with captured board retention and
static flex fanout. Its added resistance fails the previous stress-current
screen:3.022A versus2.995A breaker floor before the stationary wire allocation.
The [stationary carrier prototype](rotary-compact-candidate/stationary-irm20-integration/DESIGN.md)
closes the static lead/trunk clash, but pin-to-land solder process, in-core wire
assembly remain unresolved. The [installation-source gate](rotary-compact-candidate/stationary-irm20-integration/installation-gate/receipt.json)
blocks IRM20 in theØ43mm bore for production: the published lateral allowance
alone needs47.7mm, with no explicit alternative construction found in the three
reviewed official PDFs. R1 jig/assembly development stops. The bounded
[alternative-supply comparison](rotary-compact-candidate/power-architecture-screen/README.md)
found no supported tight construction for either alternative. A stationary
source-pod allocation honoring the published spacing is checked at330×89×72mm,
which fails the compactness objective. Its43 native solids and three STEP
exports reopen, but carrier retention and terminal/FPC transitions are incomplete.
See the [allocation comparison](rotary-compact-candidate/stationary-source-pod/README.md).
The [combined compact comparison](rotary-compact-candidate/combined-compact-allocation/README.md)
shortens the old-source layout to270×89×72mm but fails integration: eight
physical interferences and a0.581mm tail gap remain. The new S12 clamp exceeds
Ø66 under the screened transform. The subsequent
[CIR-R1 interface repair](rotary-compact-candidate/compact-interface-repair/README.md)
incorporates both unchanged S12 boards at a trialØ70 collar with explicit
retention, fanout and tool access. Its bounded nominal geometry checks pass;
275×91×74mm remains a comparison with incomplete source-carrier/connector ends,
not an accepted compact product envelope. The
[S12-R1 circuit](rotary-compact-candidate/source12-candidate/DESIGN.md) is captured
on32×26mm rotating/24×16mm stationary unrouted boards. Parent fresh ERC is0;
DRC retains four connector findings and120/22 unrouted connections. Conditional
port voltage is4.783–5.304V with179mA modeled input-breaker margin; maximum USB
fault voltage/energy remains unproved. The [bounded protection pass](rotary-compact-candidate/source12-protection-energy/README.md)
screened two remedies without establishing an acceptable network; no new circuit
was captured. Its named source, response and energy requirements remain prerequisites
to source routing. This does not establish impossibility of all protection designs.
CIR-R1 provides nominal mechanical integration of these boards, but no accepted
complete pod/mains construction. Do not apply12V to the retained5V board;
electrical and manufacturing acceptance remain open.
The [CYL-R1 cylindrical screen](rotary-compact-candidate/cylindrical-source-repack/README.md)
stops at phase0 HOLD without new assembly CAD. Parent checks reproduce the
film failure and find a larger finite3D clearance-corridor interference than
the radial-only screen. The original comparison used unequal connector/tool
allowances; a matched-allowance sensitivity still suggests potential reduction,
not an accepted envelope. The [CYL-R2 constructed partial prototype](rotary-compact-candidate/cylindrical-source-repair/README.md)
now clears the corrected finite corridor and film checks. Parent native CAD
checks reproduce356 valid closed objects,0.4876mm minimum corridor distance and
0.3742mm film clearance in the allocated bore. Its302.8×77×77mm matched classic
planning comparison is not finished product size. Neck attachments, fuse and
terminals are unbuilt; mounting/lead/film crossings of the source installation
reservation remain unapproved. The completed GLM Flash review found one
assembly defect: the installed upper shell blocks all four closure-driver
paths. [CAF-R1](rotary-compact-candidate/closure-access-fix/README.md) removes
those overlaps; parent [CAF-R2](rotary-compact-candidate/closure-access-margin-fix/README.md)
also removes an accidental zero-clearance ledge contact. Four Ø5.5 passages now
provide0.25mm nominal tool-to-upper clearance, preserving all four bearing seats,
355 other shapes and all placements. Ports, strength and sealing remain
unqualified. Original reviewed files stay unchanged. See the canonical checkpoint
for checks. The completed [two-reference source screen](rotary-compact-candidate/compact-source-reference-screen/README.md)
establishes no smaller complete replacement. TIDA-01560 remains a conditional
12V reference only:66×50mm board, complete height unknown,1.125A rating below
the retained overload screen. Existing source circuits and CAD remain unchanged.
No delegated work is active and no manufacturing release is claimed.
These prototypes do not establish a manufacturable barrel. Source startup,
current delivery, sealed thermal behavior, USB and endurance remain unqualified.

The [manufacturer connector contracts](connector-interface-candidate/README.md)
provide12 original STEP references. Selected classic rear depths are30.4mm;
TRUE1 inlet/outlet31.2/32.8mm, all before terminals/wire access. The examined
NEMA flanged pair needsØ63.5mm and45.3/43.6mm rear depths, so it is not a drop-in
Ø48×24mm end. Parent checked original model identities, mounting shoulders and
source hashes; installed mated lengths and approved molded NEMA cords remain open.
Vendor invalid/open models are reference geometry, not collision-acceptance solids.
The [installed-mating study](connector-mating-envelope/README.md) ends in HOLD
for all four Neutrik pairs: mounting shoulders and isolated face probes do not
establish seating depth or locked/latch clearance. Its58 inventory/233 direct
protected-input hashes pass parent checks; no paired CAD or complete fit is claimed.

The [partial PCB placement](eda/placement-candidate/README.md) places37 MCU/RF/DMX
parts on the90×28mm outline. Parent verified the corrected signal-net merges and
candidate isolation partition. KiCad reports zero default geometric violations
and89 unconnected items; the board has no routing and omits power/SPI/USB/service
hardware. It does not establish complete-board packing or manufacturing readiness.

A separate [39-part USB/NOR copy](eda/service-footprints/gct-power-candidate/README.md)
adds proposed GCTUSB4125-GF-A and staging-flash footprints: fresh parent KiCad
DRC reports zero geometric violations and103 unrouted connections. It preserves
the original37 parts, but still needs PCB-thickness/process qualification,
removal of the obsolete midmount notch and resolution of a3mm case recess.
The active BOM, board and enclosure remain unchanged by that proposal.

The [flush-port mechanical prototype](eda/service-footprints/gct-power-candidate/mechanical/README.md)
adds a12.4×2.3mm PCB tongue and moves the USB connector3mm forward, making its
mating face nominally flush while retaining the98×34×24mm case. Independent
saved-CAD and board checks pass; component-height keepouts from the new support
must be respected in power placement. Compliant supports, strength, exact cable
fit and manufacturing process remain unqualified. This is a separate proposal,
not an adopted product outline or manufacturing release.

## Files and regeneration

From repository root, with existing tools only:

```sh
/home/juicebox/.local/bin/freecadcmd hardware/compact-dmx/cad/build_cad.py
python3 hardware/compact-dmx/cad/make_drawings.py
python3 hardware/compact-dmx/eda/generate_dmx_sheet.py
python3 hardware/compact-dmx/eda/verify_kicad.py
python3 hardware/compact-dmx/validate_package.py
```

Verified local tools: FreeCAD 1.1.3, existing user Flatpak KiCad 10.0.7
(`flatpak run --command=kicad-cli org.kicad.KiCad`), and LibreDWG 0.14 installed
with owner approval at `.tools/libredwg-0.14/bin/`. The `.tools/` directory is
ignored by Git. LibreDWG source/archive provenance is in the canonical checkpoint;
conversion warnings must be assessed before using any converted fixture geometry.

- `cad/build_cad.py`: editable dimension-driven FreeCAD construction source, analytic
  B-rep solids. Dimensions sheet in FCStd is an informational summary; edit source
  parameters and regenerate. It is not a live spreadsheet-driven constraint tree.
- `exports/compact-dmx-revb.FCStd`: editable FreeCAD document; source remains the
  authoritative parametric construction recipe.
- `exports/*assembly.step`, `barrel-exploded.step`: supplier bounding envelopes plus
  custom RFQ solids; not supplier-approved connector models. Exploded offsets are
  for visualization only, not installed locations.
- `exports/D01*`, `D02*`, `B01*`, `B04*`, `B06*`, `B09*`, `B12*`, `B19*`: individual custom-part STEP.
  No STL/mesh is represented as a production surface.
- `exports/01*.svg` through `03*.svg`, `manufacturer-drawings.pdf`: three dimensioned
  vector drawing sheets; source is `cad/make_drawings.py`.
- `exports/sidecar-pcb-outline.dxf`: outline, mounting holes and provisional USB edge slot only, no copper/footprints.
  `lock-ring.dxf`: proposed index-ring profile/holes, not released CAM.
- `eda/dmx-interface.kicad_sch`: modern self-contained schematic with embedded,
  electrically typed symbols; matching `nova-dmx.kicad_sym`, project and local
  symbol table preserve library checking. Twelve circuit components plus X1/J1
  explicit partial-sheet boundaries. X1 maps to the current `eda/power-service/` X_DMX interface.
  Power, cutoff and POR gating are captured there; MCU/RF have a separate captured sheet. Pin8 is modeled in enable-input mode;
  the alternate open-drain fault-output mode is documented on the sheet.
- `eda/verify_kicad.py`: invokes existing Flatpak KiCad10.0.7 to export the actual
  XML netlist, PDF/SVG and run ERC with all severities and failure exit enabled.
  It verifies every U5 pin/type and every resistor/capacitor node against the CLI
  export. `dmx-interface.net` is now ONLY a real KiCad-generated netlist.
- `eda/dmx-erc.json` and `kicad-validation.json`: zero errors/warnings/exclusions
  on this PARTIAL sheet;14 exported components/15 nets, including boundaries
  and intentional NC nodes.
  These results do not establish complete product capture, PCB DRC or hardware
  operation. `eda/dmx-interface.pdf` / `rendered/dmx-interface.svg` are CLI renders.
- Correction: the retired legacy `.sch`/cache loaded zero components in KiCad;
  its hand-written XML was not evidence of schematic connectivity. Prior PATH-only
  discovery missed the existing KiCad Flatpak. Both legacy files are removed.
- `exports/cad-validation.json`: major-package interference, solid validity, explicit base/PCB contact, package/PCB and shell clearance, antenna-volume checks,
  78 neutral barrel mechanical pairs, minimum/nominal/maximum lock release,
  and 181-angle ideal two-lane wire-to-lock-sleeve clearance.
  Includes allocated zones; does not prove complete component packing, whole-part
  assembly clearance, wire motion, fixture fit or mains insulation compliance.

The STEP files deliberately include uncut mains endcap blanks. Source-backed
connector cutouts, detailed primary harness, captive lock slider/spring/hood,
fasteners and closed secondary cassette still need modeled detail and engineering
review. B19 is a modeled sleeve through the cassette; divider/cover seals and
its retention remain incomplete. Schematic capture covers the isolated DMX interface
and current power/buffer/POR/cutoff/SPI/service hardware. MCU/RF support is
captured separately;37 MCU/RF/DMX parts have partial placement. Complete PCB
placement/routing, USB protection qualification and mains source boards remain
unfinished RFQ/NRE work.

No vendor firmware, proprietary implementation, binaries or secrets are included.
Manufacturer datasheets consulted are linked in the canonical design and BOM.
No manufacturing order, hardware energization, purchase, branch change, commit or
push was performed by the design child. Parent integrates and publishes.

## Current power-only and RDM service hardware

Owner correction: “Thats fine, we can skip usb interop and just leave wireless AND wired RDM as the main path. The key is going to be how do we flash updates to the device over the DMX port”.

`eda/power-service/DESIGN.md` is the source/pin/budget record for this capture.
USB-C is power only; there is no onboard UART bridge or USB recovery domain.
`eda/historical/` preserves the superseded candidate and its old ERC evidence;
it is excluded from current package acceptance.

```sh
python3 hardware/compact-dmx/eda/power-service/generate.py
python3 hardware/compact-dmx/eda/power-service/verify.py
python3 hardware/compact-dmx/eda/generate_dmx_sheet.py
python3 hardware/compact-dmx/eda/verify_kicad.py
python3 hardware/compact-dmx/eda/power_budget.py
QT_QPA_PLATFORM=offscreen /home/juicebox/.local/bin/freecadcmd hardware/compact-dmx/cad/build_cad.py
python3 hardware/compact-dmx/cad/make_drawings.py
python3 hardware/compact-dmx/validate_package.py
```

The power/service generator produces self-contained modern KiCad source and a
matching library. Its verifier runs actual CLI export/ERC and independently
checks IC pins, every two-terminal component, USB-data NCs, latch states and
separation of resident-service and ROM straps. PDF/SVG and a component ledger
are actual KiCad exports/derived records. Four power flags identify implemented
passive-derived rails; none substitutes for a control gate.

The resident DMX/RDM update loader, rollback/authentication policy and factory
CCFG mapping are future software work, not implemented or tested here. The service
button is distinct from the ROM UART/SPI backdoor. cJTAG and ROM/reset factory pads
remain. Stable VBUS and power-good are exposed; capacitor energy is ride-through,
not a whole-transfer guarantee. No MCU GPIO pin number is invented.

`eda/power-budget.json` records the retained <=500mA PSD design basis,25mA charge setting,
current/cutoff tolerances and unmeasured runtime. Existing98x34x24mm housing is
retained; the SPI NOR max envelope replaces the bridge, but the complete power
component placement does not yet fit a verified25x6mm allocation.

### MCU support and dual-band frontend follow-up

`eda/mcu-radio/` now captures exact CC1352R1 support values from public TI
SWRC354 Rev1.1.0 plus the production Johanson0900PC15A0036001E frontend.
Owner selected **2.4GHz plus US915MHz**; one shared radio, now with two antenna feeds. Run `python3 eda/mcu-radio/generate.py` then `python3 eda/mcu-radio/verify.py` from this directory. KiCad10.0.7 actual export/ERC verifies26 components,57 nets,49MCU contacts,46 retained TI reference connections and12 antenna-match connections, plus current power/DMX endpoint snapshots. Zero ERC violations does not qualify RF performance.

Johanson0900AD47A2450001E dual-feed prototype removes the preliminary Murata switch, its control resistor and common DC block. Its five matching parts use manufacturer reference values. The50×30mm reference board differs from our90×28mm board;18×28mm end-region reservation is only a placement proposal. Inactive-port loading/stress, tuning, fixture-metal clearance, crystal qualification and PCB routing remain gates. See [sources and limits](eda/mcu-radio/DESIGN.md), [reservations](eda/mcu-radio/placement-reservations.csv) and `dualfeed-implementation-receipt.json`. Older allocation/dualband receipts and `historical-switched/` are historical, outside current acceptance.

DIO4/pin9SERVICE remains separate from DIO3/pin8ROM. DIO18/pin28 fault reserve
remainsNC until a power-off-safe interface is agreed. R4 limits EN/FLT current;
The minimal prototype uses ISOW1412 on-chip ESD capability; no external SM712. Manual120ohm termination is now captured, assembledOFF. No firmware,
complete-product/ERC/PCB qualification or proven hardware recovery is claimed.

### Termination and partial source footprints

`eda/footprints/DESIGN.md` records the minimal component-ESD basis, manual termination ratings/derating and placement constraints. DMX exports14 components/15nets with zeroERC. `eda/footprints/generate.py` writes editable local lands; run its `verify.py` using `flatpak run --command=python3 org.kicad.KiCad`. The [RF replacement pass](eda/footprints/REPLACEMENT-PASS.md) gives36 source-backed assignments and one provisional switch across37 physical MCU/RF/DMX parts.17 footprints parse;16 dimensioned patterns/113 numbered pads are checked. IPC copper/paste/mask lands are exact TI reference vectors. Five matching parts now use source-backed Coilcraft/Murata lands, with RF retuning still required. PCM12SMTR is Active, but its mounting-row datum/pattern correction remains open; this is **not full footprint-source acceptance or a PCB release**. Current evidence is in `eda/footprints/replacement-receipt.json`; prior assignment receipts are historical.
