# CYL-R2 — cylindrical source construction, partial prototype / HOLD

CYL-R2 constructs one source bay in editable FreeCAD and STEP, with a retained carrier, shell closure, pin passages, supported film, continuous stationary trunk envelopes and rerouted secondary conductors contacting the actual unchanged S12 J0 lands. **It is not a complete or approved mains assembly.** The neck attachment, source fuse/terminal construction, connector ends and approval of mounting/lead crossings through the installation reservation remain open. No compactness threshold is attributed to the owner.

All writes are confined to this directory. CYL-R1 remains byte-unchanged. `parent-correction.json` records the parent’s two corrections and the sole intentional historical-manifest delta: the canonical document changed after the original403/403 verification. Its original manifest was not refreshed. IRM20-12 and its documented mains/derating assumptions remain unchanged; the stray125V fragment conveys no requirement. Internal12 V, external5 V/1.5 A, stationary mains/PE and isolated-LV-only rotation are retained.

## Corrected comparison and dimensions

The old mixed-allowance rejection is withdrawn for this task. CIR275 was128 sourcepod +12 neck +87 core +48 generic end blanks. The fair sensitivity removes those blanks and adds the **same** actual bare rear depths and total0/20/40 mm terminal/tool allowance to both layouts. `comparison.json` lists every term. CYL is88 sourcebay +27 neck +87 core. With40 mm total access:

| Comparison | CIR panel allocation | CYL panel allocation | Conditional box-volume reduction |
|---|---:|---:|---:|
| Classic,60.8 mm rear total |327.8|302.8|18.669%|
| TRUE1,64 mm rear total |331.0|306.0|18.604%|
| Flanged NEMA comparison,88.9 mm rear |355.9|330.9|18.139%|

CYL uses77×77 transverse planning dimensions; CIR uses91×74. These are **not completed product envelopes, minima or achieved owner acceptance**. Terminal/tool sufficiency is unproved. Some old pod space may already serve access, so the40 mm addition could overlap existing CIR space; the0/20/40 sensitivity exposes that uncertainty rather than counting it as proven saving. CYL’s two20 mm regions are disjoint: X−135..−115 and87..107. Classic rear boundaries would lie−165.4..−135 and107..137.4. Front projections, installed mates, latches and hands are not included. No guessed connector solids were added. Molded NEMA cord construction remains intended; the flange row is only a comparison, not a substitution. CI/CME HOLD and the classic B-to-A jumper requirement remain.

The bore increase from CYL-R1 is0.4 mm radius and the neck increase is5.669 mm. These engineering choices target at least0.3 mm film and0.4 mm finite-corridor clearance after the stated bore allowance, not an owner diameter or reduction threshold.

The constructed source shell is X−115..−27, OD77/ID71, with3 mm nominal wall; neck X−27..0 tapers to OD49/ID43. CIR core0..87 and all board datums stay unchanged. The module is translated(+4.5,0,−2) from CIR: max52.9×27.7×24.5 body, pin projection4.5 mm. Its body occupies X−97.45..−44.55,Y±13.85,Z−12.5..12.0. Pin datums become L/N X−93.8,Y±10.4,Z−17; LV X−48.8,Y−2.4/−10.4,Z−17. Actual supplier pin-location tolerances and termination details remain unresolved.

The81×52×44 inherited reservation occupies X−111.5..−30.5,Y±26,Z±22. An additional0.5 mm per face is retained. This is an engineering whole-carrier reservation, not a manufacturer-approved housing minimum. Film is82×53×0.25 at Z−22.75..−22.5, with modeled post and lead passages. Its maximum outer radius34.925814 mm fits the35.3 mm tolerance-reduced bore with0.374186 mm clearance. Nominal bore35.5±0.2 and outer radius38.5±0.2 are **proposed allocations**: worst outer diameter77.4; nominal source-wall3, allocated minimum2.6. The local lock-access relief in the neck leaves only0.970 mm nominal /0.670 mm after the stated0.3 mm combined allowance. That thin region and the unbuilt neck joint have no strength acceptance.

## Retention and construction, with exact limits

The lower shell and four carrier posts are one connected solid. Four M2-envelope screws retain real carrier ears: diameter2.4 clearance holes and diameter1.6 pilot holes give4.4 mm nominal pilot engagement. Four further M2-envelope screws close the two shell halves with4 mm pilot engagement. The proposed carrier is61×32×1.6 before its ears, seats and guide walls; four diameter2 pin passages clear nominal source pins. Module maximum-body side/end play is0.25 mm; two ribs on the removable upper half prevent lift with0.25 mm top play. This is positive geometric capture, not a claim of clamp force, thread strength, creep life or shock rating.

Four post collars support the film at its lower face. Post holes have0.3 mm nominal radial clearance; lead passages are actual diameter3.6 swept cuts around diameter3 branch envelopes, also0.3 mm nominal. Module seats, carrier-to-post bearing and film-to-post support are checked contacts. Example manufacturing allocations of±0.1 on each mating support face leave0.05 mm from the nominal0.25 module play; they are not supplier tolerance grants. Pin-position tolerance, full solder/lead stacks and actual film handling are not closed.

**Installation construction is not approved:** posts, carrier screws, upper retention ribs and lead paths cross the reserved volume. `cad-check.json` enumerates every crossing volume. In particular the upper ribs are only0.25 mm above the maximum source body, whereas the inherited enclosure reservation preserves10 mm above it. No assertion is made that the manufacturer permits such dielectric mounting exceptions. Machined PEEK shell/carrier and insulating fasteners are prototype material proposals only; no allowable, flammability, insulation-system or thermal approval is inferred. The exact remaining construction question is approval or redesign of this insulating support/retainer system and its source-pin/film crossings. A large empty enclosure reservation alone does not resolve it.

The source shell and neck currently meet on an axial face; neck and CIR core meet at X0. **Their mechanical attachment/retention is unbuilt**, not a claimed bonded or threaded joint. The retained carrier is real, but that does not make the overall barrel a retained finished assembly. Connector shoulders and the two20 mm access regions are boundaries, not qualified endcaps or installed terminal assemblies.

## Finite wiring and the full corridor correction

Three continuous stationary L/N/PE envelopes extend from X−135 to107; each path is246.942 mm long. Source-bay axes are Y−8/0/+8,Z−29. Two tangent R12 arcs raise them to Z−16 over21.330729 mm, followed by5.669271 mm straight before the core. Actual OD4.5 wire envelopes and separate OD5.5 assembly corridors are saved solids. **The exact swept OD5.5 BReps have zero volume outside the complete bore reduced0.2 mm.** `motion-clearance.json` additionally reports the exact distance to its boundary. The sampled normal-ring calculation is supplementary; no centreline-radial subtraction is used as fit proof.

The three trunk envelopes have no rotating segment. Their ends stop at the unqualified terminal boundaries, not invented connector contacts. Neutral has a continuous finite branch to the source N pin. Line has two branches ending at X−112 and−108,Y20,Z−17: the missing fuse has a4 mm centreline gap and1 mm gap between the allocated conductor envelopes. The unselected fuse/service region is deliberately marked unbuilt; no full line-circuit continuity is claimed. Mains splice/terminal insulation, fuse selection/rating/clearing, strain relief and wiring approval remain open. Proposed branch centreline radii are only2.329/3.365/6.714 mm; these tight bends require a selected wire/process and may force more space.

Both secondary conductors are rebuilt from the translated LV source pins to the existing J0 solder features and correct lands. Copper-equivalent diameter1 and insulated OD2 are engineering envelopes, not ampacity or wire-family qualification. Lengths are128.271 and145.479 mm. Thirteen explicit contact checks prove source-pin/secondary/solder/J0 and mechanical seat contacts; they do not prove continuity through the unrouted S12 protection board. No circuit, copper route, component, footprint, local board position or net was changed. The frozen45+12 footprints and153+36 numbered pad features remain represented. Existing S12 protection-energy, startup, routing, thermal and USB gates remain UNMET.

## Assembly and access sequence

1. Keep both source halves separate and the neck/core interface open. Fit the film over the lower posts and onto their collars. Its lead passages and pin-area construction need an approved process.
2. Place the module onto the carrier seats, with pins through the four actual passages. Make the primary/secondary source-pin terminations while the carrier underside is accessible, before lowering it. The fuse and qualified terminal construction are not yet supplied; this step is not a released assembly instruction.
3. Lower the carrier/module onto the posts and fit the four carrier screws from above. The modeled vertical module/pin/carrier insertion and driver screens clear the lower shell, film and carrier. Formed wires, insulation damage, solder strain and physical handling remain process gates.
4. Install the unchanged S12 boards using CIR’s existing axial rail sequence, before connecting the new secondary wires. The new parts are checked against the actual board-part35 mm insertion sweeps. Existing retainer removal and solder-tool sequence still apply. Do not claim complete board removal through an attached source bay; detach the currently unbuilt neck interface and disconnect/unsolder leads first.
5. Fit the upper source half and its four closure screws. The fuse service screen assumes this half removed. Closure screws, carrier screws and film have explicit seats/passages, not volumetric mounting whitelists. Neck/endcap retention and complete source replacement procedure remain unfinished.

The lock-access relief clears the existing tool/finger allocation. New parts have axial or exact R24 containment certificates relative to the preserved rotor, valid across all181 angles. Both released pin pieces and the frozen compressed-spring envelope are checked against every new physical part (84 pairs). The13 detents and181 independent-stop positions are recalculated; beyond±90.5° the stop again intersects. The actual frozen USB plug/relief/cable screens clear new parts by axial separation or checked radial bounds. These are engineering screens only, not universal cable fit, a known connector mating pose, or fixture acceptance.

## Evidence and reproduction

`prototype.FCStd` contains356 valid, closed, individually connected solids, including named screens and alternative ribbon poses; this is not a manufactured-part count.317 preserved objects match CIR BRep topology/numeric coordinates within1e−12 serialization tolerance. The150-solid physical STEP omits pad detail and nonphysical screens, and is reopened and checked. The native retains all actual lands.9,086 new-versus-physical pairs produce14 individually bounded positive contacts and zero unintended overlaps. Eight are analytically bounded pilot engagements; six are named electrical endpoint envelopes, not qualified electrical joints. Existing unchanged-part internal checks remain inherited CIR evidence, not newly claimed global tolerance qualification.

Commands, from repository root, using existing tools only:

```sh
python3 hardware/compact-dmx/rotary-compact-candidate/cylindrical-source-repair/calculate.py
# Run each script through the same wrapper, substituting SCRIPT:
QT_QPA_PLATFORM=offscreen ALLOCATION_SCRIPT=SCRIPT /home/juicebox/.local/bin/freecadcmd hardware/compact-dmx/rotary-compact-candidate/cylindrical-source-repair/run.py
# SCRIPT: build.py, check-cad.py, access.py, contacts.py, motion-clearance.py, export.py, sections.py
python3 hardware/compact-dmx/rotary-compact-candidate/cylindrical-source-repair/classify.py
python3 hardware/compact-dmx/rotary-compact-candidate/cylindrical-source-repair/draw.py
python3 hardware/compact-dmx/rotary-compact-candidate/cylindrical-source-repair/draw-collar.py
python3 hardware/compact-dmx/rotary-compact-candidate/cylindrical-source-repair/verify.py
```

Do not rerun `freeze.py` to conceal mutations. Drawings are native-section-derived SVG/PDF with labeled scales; existing `pdftoppm` rendered the PDFs for visual inspection. The sources remain the fetched[IRM20 manufacturer specification](https://www.meanwell.com/Upload/PDF/IRM-20/IRM-20-SPEC.PDF),2025-11-21,p3, and[installation manual](https://www.meanwell.com/Upload/PDF/IRM-01/PCB.pdf),p1(2), plus frozen GCT/CI/CME source provenance. `sources.json` holds the reused source hashes. No installation, procurement, hardware operation, firmware, vendor contact or git publication occurred.

**Stop status: constructed partial mechanical evidence, HOLD.** No approved mains/source construction, complete source-neck attachment, fuse/connector termination, molded NEMA end, full tolerance/strength/thermal system, electrical protection, dynamic-flex equilibrium/endurance, USB compliance, fixture fit or manufacturing release is claimed.
