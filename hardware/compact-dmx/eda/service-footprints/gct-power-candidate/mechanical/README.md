# Flush GCT tongue/support mechanical prototype

This directory alone changes. `build.py` is the editable geometry source; `flush-prototype.FCStd` contains named editable solids and a dimension reference sheet. Python dimensions drive regeneration; the spreadsheet is descriptive, not a claim of linked parametric constraints. STEP files preserve analytic BRep surfaces. Supplier connector/stakes and engineering plug are explicitly labeled envelopes, not invented supplier CAD. Baseline CAD/BOM/circuit and source39-board remain untouched.

## Changes and coordinates

External case remains x0..98,y20..54,z5..29: **98×34×24mm**. Existing base, screw bosses, lid and port x36..50/y51..55/z9.5..15.5 are reproduced locally without importing baseline scripts. PCB remains z10..11; main rectangle90×28 atx4..94/y23..51. Old midmount notch is filled. New tongue **12.4×2.3**, x36.5..48.9/y51..53.3, extends outline locally; do not call the outline unchanged. Four original mounting holes remain.

GCT origin moves only +3mmY, from(42.7,44.6) to(42.7,47.6); face movesy51→**54**, flush with nominal outer case. All other37original parts plus NOR retain positions/nets/values. Stakes nowx38.38/47.02,y47.6/51.4. Four plated slots .6×1.2 are cut in mechanical PCB; shell copper1.1×1.7 remains in actualKiCad copy. Front copper edge52.25 leaves1.05mm to tongue edge53.3; outer side copper47.57 leaves1.33mm to right edge48.9 (same left). Allocated.10outline+.10placement+.05land tolerance leaves.80/.1.08mm respectively. Tongue-to-external-plane gap.70 nominal; allocated.20 leaves.50. No RF/cap/isolation/screw reserve is displaced.

## Support and insertion path

Two integral base rails x36.9..37.4 and48..48.5,y49..52.7,z7..9.6 support0.4mm compliant foam shims to nominal PCBbottom10. They avoid all four stakes. Existing screw bosses contact the PCB as before. Rail/board nominal contact occurs through shims, not overlapping solids. With allocated rigid+.10,board±.10,shim±.05, the contact stack spans±.25mm: shim must tolerate up to.25mm compression and support engagement can occur after up to.25mm PCB displacement at the opposite corner. This is a **material/compression gate**, not a proven retention solution.

Integral PA12 prototype bridge x37.5..47.9,y44.6..54,z16..19 attaches to front wall above port. Rear stop x38..47.4,y44.6..46.6,z11.5..19 leaves.60mm rigid gap behind shellrear47.2. Backed compliant pad8.8×.6×2.4 atx38.3/y46.6/z11.5 fills that gap, creating intended nominal shell contact. It transfers rearward insertion load to bridge/front wall without demanding.6mm solder movement. Allocated connector/placement/base stack.35 leaves.25 rigid clearance and requires pad compression accommodation. Pad adhesive/creep/retention remain open. Withdrawal remains carried by the four soldered stakes and PCB retention; this is not a new connector lock.

Insertion target20N comes from GCT maximum stated mating force; use40N as an engineering proof-load target, not tested evidence. Elementary cantilever screening for bridge10.4wide×3thick,9.4long gives ~24.1MPa bending at40N; rear stop9.4wide×2thick, assumed4.5lever gives~28.7MPa. These simplified estimates omit stress concentrations, print anisotropy and creep. No PA12 grade or allowable is qualified; material/process and proof-load testing must precede release. Integral bridge introduces manufacturing undercuts; this is an additive prototype, not released injection tooling.

## Finite envelopes and tolerance evidence

Connector external envelope8.94×6.8×3.16 at(38.23,47.2,11), top14.16. Drawing A6 general tolerances and placement allocation give screening boxx38.005..47.395,y46.95..54.25,z11..14.51. Base shifted toward connector by.10Y and−.10Z is checked with actual BRep intersection; zero overlap. Nominal flush becomes up to.25mm projection/recess under this allocation, not the original3mm recess. Port still contains the envelope; complete cable access is not inferred.

Four stake screening solids extend toz9.75 (maximum1.25 length below top11); .8 width is drawing-based. **Stake thickness .3mm is explicitly an engineering screening assumption because the drawing does not dimension it.** These solids are finite and fit the modeled slots, but no supplier-exact stake/slot clearance qualification is claimed. Exact section/coplanarity, plating and solder fillet volume remain gates. No hidden zero-thickness wire/terminal shortcut is used.

Engineering test overmold is12wide×6high×12long, x36.7..48.7,z9.5..15.5,nearestfacey54.4. Five external approach positions are tested against all modeled solids. At nominal flush its .4mm shoulder setback clears the case; at.25mm recession only.15mm remains. This is a stated test envelope, **not universal cable fit**. GCT drawing's1.85 shoulder-related spacing is not promoted to an overmold maximum. Metal plug insertion through actual connector internals is not modeled—the source external envelope is deliberately solid. Test proves external approach screening only; exact plug drawing/physical mating remains required.

## Checks and files

- `solid-checks.json`:14 valid closed solids,78 actual common-volume pair checks,65 external plug/solid approach checks. Intended surface contacts have zero volume; no collision pair is blanket excluded. Cap and NOR maximum envelopes included. No true routed-PCB component-height model is claimed.
- `tongue.kicad_pcb`:39electrical parts+4holes, exact original pads/nets unchanged except connector translation. RealKiCad10.0.7 DRC **0geometric violations,103unconnected**,0tracks. No new full schematic/ERC claim.
- `section.svg/.pdf`: dimensioned Y/Z section and tongue coordinates; `pcb.svg/.pdf`: actual KiCad lands/outline. `flush-assembly.step`, `base-proposal.step`, `pcb-tongue.step` andFCStd are reviewable prototype exports.

Commands from repository root:

```
flatpak run --command=python3 org.kicad.KiCad hardware/compact-dmx/eda/service-footprints/gct-power-candidate/mechanical/board.py
NOVA_GCT_MECH="$PWD/hardware/compact-dmx/eda/service-footprints/gct-power-candidate/mechanical" QT_QPA_PLATFORM=offscreen /home/juicebox/.local/bin/freecadcmd hardware/compact-dmx/eda/service-footprints/gct-power-candidate/mechanical/build.py
python3 hardware/compact-dmx/eda/service-footprints/gct-power-candidate/mechanical/draw.py
flatpak run --command=kicad-cli org.kicad.KiCad pcb drc --format json --severity-all -o hardware/compact-dmx/eda/service-footprints/gct-power-candidate/mechanical/drc.json hardware/compact-dmx/eda/service-footprints/gct-power-candidate/mechanical/tongue.kicad_pcb
```

No enlargement, shrink claim, universal fixture/cable fit or manufacturing release. Remaining material gates: stake section, supplier board-thickness/retention, shim/pad specification, bridge strength/creep, solder attachment, exact plug and assembled tolerances. Complete qualified1.5A power placement, switch source gate, RF tuning and full-product routing remain independent work.
