# Integrated25 — editable development assembly only

This folder alone is new. It clones the final U40-corrected board SHA256 `fc0785cdaaf874002b2362835070f29f00b187e4054dd3ab093c43e177ea035f`. The original proposal, qualified15 candidate and baseline remain immutable. The parent's live177-courtyard reconciliation is accepted and the input hash is independently checked. No unfinished cell-protection output is imported or allocated.

**Produced:** actual `integrated25.kicad_pcb` / project, `Buffer25.pretty` editable land, `integrated25.FCStd`, analytic `integrated25.step`, dimensioned `assembly-sections.pdf`, actual `board-top.svg`, generators and independent checks. This is an unrouted mechanical/electrical placement prototype, not a fabrication or manufacturing release.

## PCB and electrical contract

Main90×28×1mm rectangle, four original holes, outer edge segments and USB tongue stay unchanged. New **29.4×10.3 internal aperture**, x26.5..55.9/y25.5..35.8, uses four actual **R0.5 arcs** and four straight edges. R0.5 is a proposed1mm routing-tool radius, not fabricator approval. It stays right of isolationx26 and beforeRFx59. The narrow0.5mm separation from the *allocation boundary* is not a certified electrical isolation clearance; the actual isolated circuit remains unchanged and requires routed review.

Rounded corners reduce the prior square-aperture allocated BRep gap from0.231 to **0.178271mm**. The calculation uses maximumØ16.5×28.4 cell,0.15 positional inflation, aperture edges inset0.10 and PCBtop11.10. This positive result is not silently reported as the old clearance. Cutter radius tolerance, inner-edge finish, board flex and assembled datum capability require DFM agreement. Every actual pad's AABB clears the conservative full rectangular aperture: minimum **1.15mm** at C23. The true rounded hole removes less material.

C23 alone changes. MPN/value is `HV1625-2R7256-R 25F 2.7V`; pin1 remainsCAP_POS and pin2GND_USB. Its engineered PTH lands are **not Eaton recommended lands**:

- Pad centres `(57.9,26.9)` positive and `(57.9,34.4)` negative;7.5mm nominal pitch.
- Oval copper1.7X×2.7Y; plated slot1.1X×2.1Y; no paste layers. Mask opening follows pads with default zero explicit expansion, subject to fab process review.
- Minimum nominal copper annulus0.30. Slot centres are aligned with the new formed vertical leads. Maximum0.82 wire leaves0.14 lateral nominal clearance; with finished-slot−0.05 and combined forming/registration0.10, only0.015 remains in X. These tight allocations need jig/fabricator approval, not tolerance optimism.
- Supplier pitch±0.5 gives per-lead±0.25 if centered. SlotY nominal end allowance(2.1−.82)/2=.64; subtract0.25 pitch and0.15 assembly leaves0.24. Independent-centering capability must be established.
- Copper endsx58.75, courtyardx58.90:0.10 toRFallocationx59. No other footprint is moved.671 original pad signatures and177 noncell footprints/values/IDs/orientations match the source.

KiCad10.0.7 actual DRC: **0 violations,452 unconnected items,0 tracks**. Five inherited ignored categories are preserved and listed verbatim in `board-check.json`; no blanket DRC suppression was added. Source libraryQ15 is referenced read-only; the new footprint is local. This is a PCB-only derivative: **ERC cannot validate it**, and no new full schematic/ERC claim is made. Parent must update the schematic/BOM association when integrating C23.

## Source evidence and lead forming

Eaton HV TechnicalData4376 January2020 p3 gives maximum body16.5×28.4, leadØ0.80±0.02, pitch7.5±0.5, lead lengths20/25 minimum and longer-positive polarity. Its PDF remains in the immutable parent candidate. One bounded guide pass fetched the actual primary **Eaton PS-5006, December2017** application PDF into `sources/`; URL/hash in `sources.json`. It supplies handling/soldering cautions, **no numeric bend radius, first-bend distance, seal position or approved preformed variant**. No third-party guide is substituted as Eaton authority.

Actual editable lead solids use maximumØ0.82, straight1.3mm from **x55.4 maximum-body-face datum**, then a true circular90° bend of **R1.2 centreline**, then a vertical leg atx57.9 toz9. Nominal seal-side heightz18.1 and Ypositions26.9/34.4. Length from that face to tip is1.3+π×1.2/2+7.9=**11.085mm**, below the supplied20mm short-lead minimum. Trim is1mm below PCBbottom10. Body-face is **not a sourced internal-seal datum**; internal terminal exit eccentricity/standoff must be confirmed. Actual formed geometry, pitch extremes, coating cracks, solder fillets and creep must be qualified.

This compact R1.2 form is an **engineering proposal requiring supplier approval**, not a supported Eaton forming limit. Approximate outer-fibre strain d/(2R)=34% illustrates the plastic deformation/plating concern. Use a supported forming jig that clamps the straight seal-side segment without loading the seal; do not repeatedly bend. Hand assembly can use externally preformed parts, but approval is still open. A hypothetical gentler2d straight +2d radius with d=.82 needs3.28mm reach versus2.5 available, **0.78mm extra**. Its land/courtyard would enterRF by about0.68mm. Shifting the cell left0.78 would force the aperture across isolationx26. Thus this larger-form alternative is not silently fitted: it would require an explicitly new local arrangement or supplier-supported tighter form. No such redesign is performed here.

Eaton warns against sleeve damage, exposed copper under the cell and uncontrolled solder heat; the family sheet generally discourages manual soldering. The guide recommends tip<260°C,350°C maximum and<5s, and prohibits generic reflow. A qualified controlled solder/preforming process is required; these numbers alone do not approve this assembly. Copper-free cell/support region and sleeve-to-liner compatibility need routed/assembly verification.

## Positive mechanical retention and assembly

Cell staysx27..55.4,cy30.65,cz18.1; case98×34×24 unchanged. Original GCT bridge/stops/stakes/port, NOR and RF placement remain. Two lower saddles atx28..31 and50..53,y25.8..35.5,z7..12.5 are **integral with the local PA12 base**, replacing unattached conceptual blocks. Curved separate liners fill the radial8.25..8.60 space inside these saddles.

The local lid now has two matching upper bosses atx28..31/50..53,y27.65..33.65, down to the R8.60 curved surface, with separate **0.35 radial silicone liners**. Closing the lid captures the cell vertically between upper and lower saddles; it does not rely on lead strength or adhesive as the retention load path. Proposed material: electrically insulating silicone35–50ShoreA, compatible adhesive only to plastic backing, not bonded to the sleeve. Grade, temperature/flame rating, compression-set, extraction force and long-term sleeve compatibility remain unqualified.

Axial stops are lid-integral x26.3..26.6 and55.8..56.1,y29..32.3,z24.5..27. Separate0.4mm compliant pads fill nominal0.4mm rigid gaps at the upper peripheral endfaces (padz24.5..26.2). Combined0.25mm process/position allowance leaves0.15 rigid axial margin. Central endface radius6.4 remains geometrically open below the restraint; **actual vent position and pressure escape are not dimensioned by this source and require approval**. No potting or fully capped endface is proposed.

Four **engineering M2×22 countersunk screw envelopes**, on unchanged(7,26),(73,26),(7,48),(73,48), close the lid:2mm shaftz7..28,4mm diameter90°headz28..29 flush with external lid. Local lid has1.1R clearance bores and matching countersinks; existing1.7mm boss pilots retain3mm nominal engagementz7..10. These are conventional prototype dimensional choices, **not supplier-exact screw CAD or an approved thread recipe**. Source an appropriate fastener and qualify pilot/tapping or thread-forming method, torque, pull-out and boss splitting. The exact thread is not modeled; the four shaft/pilot interference volumes are explicitly recorded as intended engagement, confined toz7..10. No other intersection is waived.

Suggested assembly: qualified formed cell and land soldering first; place board over integral cradles with lead/USB slots aligned; seat cell on lower liners without loading leads; install upper/axial liners on lid; close while checking lead freedom and vent path; tighten four screws to a tested torque. With nominal16mm rather than maximum16.5mm body, liner compression changes: select/shim liner thickness from actual tolerances, do not force the maximum-envelope stack onto every cell. Screw/board-hole alignment, thermal expansion and liner compression require tolerance trials.

## Evidence and limits

`mechanics-check.json`:26 valid closed shape objects;321 zero-volume pair comparisons;4 explicitly bounded nominal thread engagements;3268 component-solid checks. USBJ1's courtyard intentionally crosses the case and is not extruded against its own port; its **actual connector/stake solids are included in all-pair checks**. Four empty mounting courtyards are represented by actual screw/boss/hole solids. Other component envelopes retain the prior source-backed DBV1.45mm and conservative top2.23/bottom1.45 screens. Rounded aperture/lead and actual solder-slot clearances are modeled, not zero-thickness paths. Worst inflated cell is checked against rigid base/lid; liner compression volumes are separately reported as intended compliance, not erased.

`verify.py` checks actual saved board input hash, all unchanged pads/nets/layers/IDs, C23 polarity/geometry, outer edge preservation,8newedges/4arcs, all pad-to-aperture gaps, RF boundary and actual DRC. No cell protection parts are assumed. Existing16.343s conditional runtime is unchanged; physical measurements, cold bounds, charger/protection integration, routing, RF, soldering, liner/fastener strength and assembled/cable fit remain release gates. Nominal geometry is checkable; force retention and manufacturing capability are not claimed verified.

Reproduce from repository root (all outputs remain here):

```sh
flatpak run --command=python3 org.kicad.KiCad hardware/compact-dmx/eda/buffer-fit-candidate/integrated25/board.py
flatpak run --command=kicad-cli org.kicad.KiCad pcb drc --format json --severity-all -o hardware/compact-dmx/eda/buffer-fit-candidate/integrated25/drc.json hardware/compact-dmx/eda/buffer-fit-candidate/integrated25/integrated25.kicad_pcb
flatpak run --command=python3 org.kicad.KiCad hardware/compact-dmx/eda/buffer-fit-candidate/integrated25/verify.py
NOVA_BUFFER25="$PWD/hardware/compact-dmx/eda/buffer-fit-candidate/integrated25" QT_QPA_PLATFORM=offscreen /home/juicebox/.local/bin/freecadcmd hardware/compact-dmx/eda/buffer-fit-candidate/integrated25/mechanics.py
python3 hardware/compact-dmx/eda/buffer-fit-candidate/integrated25/draw.py
```

FreeCAD logs a source-shape hasher warning; all explicit validity/intersection assertions pass and exports are checked independently by their recorded hashes. PDF rendered with pdftoppm and inspected; actual SVG rendered at400dpi and inspected. No hardware/firmware/installation/publication or baseline changes.
