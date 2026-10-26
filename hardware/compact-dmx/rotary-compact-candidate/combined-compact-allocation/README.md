# Combined compact allocation — one bounded pass

**Not an accepted product envelope.** The selected in-line comparison removes 60 mm of unused axial allocation: **270 × 89 × 72 mm**, versus the rejected 330 × 89 × 72 mm. The 18.18% reduction is real for the frozen old-source spatial comparison. It is not proof that the owner's compactness goal, the new 12 V electronics, or mains construction is achieved.

Only this directory is owned. Earlier collar, source-pod, protected25, source12, electrical and mechanical candidates remain immutable. The root's repair/allocation briefs are parent engineering instructions, not quotations attributed to the owner. The source12 completion update superseded the earlier prohibition on reading that folder; only its frozen dimension/placement records and board files were read and hashed.

## Two arrangements, one CAD attempt

`screen.py` / `screen.json` compare exactly two arrangements before CAD:

* **In-line:** retain the 128 × 82 × 62 mm pod, its finite primary/fuse/harness space, both full Ø48 × 24 mm generic connector blanks, and the complete old collar mechanism. Move every actual collar shape −22.8 mm in X. Shorten the provisional Ø48 core from 142 to 82 mm; move the output blank −60 mm. Released collar X4..81.37; output blank X82..106; input blank X−164..−140. Total X−164..106 = 270 mm. Neither generic blank is an approved legacy powerCON, TRUE1 or NEMA interface.
* **Offset:** align the same pod X−12..116, Y−117..−35, on the negative-Y side outside the forward 180° USB sector. Count the input blank X−36..−12 and the output blank X82..106. Optimistic bounds **152 × 150 × 72 mm**, before a new transverse harness neck. Its 1.642 L bounding volume is only 5.12% below the in-line 1.730 L, while width increases 68.54%. It is rejected here for fixture-adjacent transverse bulk and the additional harness interface, **not** on an invented USB collision. Actual 181-position obstruction results are in `checks.json`.

This is not a global minimum search. The source-only lower-bound axial sum is **72.9 + 77.37 + 48 = 198.27 mm**. Retaining the conservative 81 mm whole-carrier envelope raises it to **206.37 mm**. These omit walls, film, tolerance, terminal bends, tools, lock access and retention. They are not achievable housing dimensions or manufacturer-approved minima. The chosen pod remains conservative; no unsupported reduction of source distances or deletion of interfaces is credited as compactness.

## Primary source distances versus engineering allocations

`sources.json` identifies and hashes the actual cached primary assets:

* MEAN WELL IRM-20 specification, **2025-11-21, page 3**, [manufacturer PDF](https://www.meanwell.com/Upload/PDF/IRM-20/IRM-20-SPEC.PDF): nominal 52.4 × 27.2 × 24 mm, general ±0.5 mm; maximum body 52.9 × 27.7 × 24.5 mm. Pins 3.5 ±1 mm; nominal Ø1 mm. Pin coordinates derive from the **nominal centered body**, not its maximum tolerance edge: AC/N (−98.3,−10.4), AC/L (−98.3,+10.4), −V (−53.3,−10.4), +V (−53.3,−2.4) in this allocation. The bottom-view labels are retained.
* MEAN WELL PCB installation instruction, **page 1, Installation (2)**, [manufacturer PDF](https://www.meanwell.com/Upload/PDF/IRM-01/PCB.pdf): 10 mm general surrounding reservation, at least 5 mm below plus Mylar. The saved source box retains 10 mm about the inherited 61 × 32 mm carrier, 5 mm below maximum pin projection and 10 mm above maximum body. **81 × 52 × 44 is inherited whole-carrier conservatism, not a published minimum enclosure.**

The separate ±0.5 mm tolerance envelope and proposed 0.25 mm film remain. Film grade/flame rating, terminal insulation, support bridges and carrier retention are unresolved. Four support zones remain visibly separate allocations; the carrier is **not retained**. No waiver is inferred for conductors entering the source connection region: every such intersection is explicitly recorded as an **unqualified electrical interface crossing**, not a source-distance pass.

## Continuous finite wire envelopes

`wire-paths.json` records editable cubic control points, lengths and 1,001-sample minimum bend radii. Continuous L/N/PE bypass paths preserve the previous R12 bends and Ø4.5 wire / Ø5.5 installation envelopes, shortened only at the output end. They meet actual finite input/output joint allocations. PE never rotates.

The L branch reaches a finite fuse bay, then a separate continuous curve reaches the L pin. The N branch reaches the N pin directly. The fuse itself and its terminal construction remain unselected; continuity through that **explicit fuse boundary** is not falsely modeled as a wire short. Primary curves use Ø3 insulated-wire allocations; minimum sampled curved radius after the local crossing repair is 7.05 mm (N branch; L is 9.87 mm). Two isolated LV routes use Ø2 allocations, source-pin approach, core transition and radial fixed-tail approach, with minimum sampled radius 10.67 mm. These are engineering bend choices, not approved wire/material/ampacity values. Bézier endpoint tangents are aligned at the chained segments.

The proposed core exit is 4 mm axial ×6.8 mm tangential, through the wall at X20.2..24.2, Y18..27, Z−7.8..−1. Its insulating bushing, strain relief, termination lands and safety construction are not designed. Pair checks deliberately retain any contact with actual clamp parts. No disconnected endpoint box is presented as a finished route; the saved contact graph reports exact endpoint gaps and intersections. This is an old-source spatial route comparison, **not a wired S12 protection-board integration**.

## Frozen S12-R1 changes the result

The completed S12 receipt hash is separately frozen. Both new boards are counted, but neither is silently substituted for the old actual source:

* Rotating **32 × 26 × 1 mm**, 45 footprints, maximum top allocation 3.46 mm. Proposed dimensional transform is `X=52.2+x, Y=26.1+z, Z=13−y` (proper rotation, determinant +1). Its USB body ends X86.37, **5 mm beyond the old comparison**, and is not a mating-plane datum. Existing retention and source housing are not accepted for this board.
* Its exact provisional external clamp reserve maps to X52.95..73.45, Y26.1..28.1, Z−18..−13. The outer corner is **R33.370796**, exceeding Ø66 even before a wall. A merely illustrative 1 mm wall +0.25 mm assembly allocation gives **Ø69.241591**. No enlarged collar CAD was fabricated to call this solved. Existing FPC static fanout and retention cannot be inherited without redesign/checking.
* Stationary **24 × 16 × 1 mm**, 12 footprints, maximum top 2.5 mm. A dimensional allocation occupies X−90..−66, Y26.75..42.75, Z0..1, with components to Z3.5. Its 20.5 ×5 ×2 mm external clamp occupies Y42.75..47.75. It has only **0.25 mm nominal lateral margin** to the source tolerance envelope and the inner pod wall. The full 20 mm solder-access allocation is visible. This is not a supported, routed or assembly-qualified installation.

Moving the output interface 5 mm for S12 gives a **275 mm axial screen only**. If a concentric Ø69.24 collar were eventually feasible, the existing pod/blank extrema would give approximately **275 ×90.62 ×73.62 mm**, 1.835 L, about 13.24% below the rejected baseline. This is arithmetic, not a completed housing or thermal fit. The old assembly CAD remains clearly labeled spatial comparison. No application of 12 V to the old AXIAL-R1 circuit is authorized.

## Verification and disposition

Run from repository root:

```sh
python3 hardware/compact-dmx/rotary-compact-candidate/combined-compact-allocation/screen.py
QT_QPA_PLATFORM=offscreen /home/juicebox/.local/bin/freecadcmd hardware/compact-dmx/rotary-compact-candidate/combined-compact-allocation/run.py
ALLOCATION_SCRIPT=check.py QT_QPA_PLATFORM=offscreen /home/juicebox/.local/bin/freecadcmd hardware/compact-dmx/rotary-compact-candidate/combined-compact-allocation/run.py
python3 hardware/compact-dmx/rotary-compact-candidate/combined-compact-allocation/draw.py
python3 hardware/compact-dmx/rotary-compact-candidate/combined-compact-allocation/classify_findings.py
python3 hardware/compact-dmx/rotary-compact-candidate/combined-compact-allocation/receipt.py
python3 hardware/compact-dmx/rotary-compact-candidate/combined-compact-allocation/verify_receipt.py
```

`allocation.FCStd` is editable; `inline-assembly.step` contains the neutral actual old collar plus the new allocation, while `allocation-detail.step` isolates the source/housing/wire allocation. Alternative active-ribbon poses remain in the native document. `comparison.pdf` and the two SVG pages show equal-scale arrangement views, with a separately labeled section scale. The PDF was rasterized and visually inspected. The old 13 detents, independent stops, pin/spring mechanism and all other collar shapes are translated without modification; their frozen proof remains applicable internally, not automatically to new external interfaces.

**No complete geometry/product PASS is claimed.** Inspect `checks.json` for every positive volume and wire-contact gap. Source carrier pin holes, intentional electrical contacts, branch crossings of the source reservation, lock access and clamp interface findings are distinguished rather than broadly excluded. The new 12 V clamp already has a demonstrated radial conflict. Mains/PE construction, approved carrier retention, actual endcap variants, source12 routing/protection-energy/startup, thermal, flex equilibrium/endurance and fixture fit remain UNMET. Stop after this one allocation; do not interpret a valid closed STEP solid as manufacturing acceptance.

### Concrete failed interface, not a hidden pass

The first saved-solid pass is retained as `checks-initial.json`. It found two readily repairable primary-path mistakes (the N branch crossed L; part of the L approach entered the planning carrier); their control points were corrected within this same arrangement. The final check is `checks.json`.

The **fixed-tail LV approach remains blocked**, rather than being silently converted into an unsupported electrical contact. In the initial exact check, the minus approach intersected the stationary spool by 1.575624 mm³, plus 0.062768 mm³ of the ear pad, 0.005411 mm³ of adhesive and 0.107833 mm³ of stiffener. The plus approach intersected the spool by 0.255923 mm³ and screw by 0.019317 mm³, yet remained **0.581013 mm from the tail**. These unchanged interface shapes remain in the final allocation as failed route evidence. The core aperture alone does not solve access through the backing/clamp. A new stationary terminal/fanout and insulating support interface would need to be designed outside the active FPC and its ears; no qualified land, retention or developable transition is available in this frozen mechanism. This is a specific interface blocker, not a claim that all smaller collars or all clock springs are impossible.

Consequently this pass demonstrates removable axial waste and records two bounded layouts, but **does not deliver a continuous, interference-free completed electrical assembly**. The new S12 board/clamp dimensional conflict is additional. Do not approve either 270 mm comparison or 275 mm arithmetic screen as the product envelope.

Parent completion update: PE-R1 found no accepted protection remedy and captured no new circuit. This allocation adds no hypothetical protection part or volume; S12 remains the unchanged 32 ×26 rotating /24 ×16 stationary dimensional constraint and is unrouted/unqualified.

### Final measured outcome

The local primary-curve repair removed the N-to-L **trunk** crossing and the L-to-carrier overlap, but did **not** close the primary route: the two primary **branch** envelopes now overlap by **24.141856 mm³**, and the N approach enters the planning carrier by **0.564065 mm³**. These are explicitly failed geometry, not approved terminal contacts. The pass stops here rather than repeatedly routing an unqualified source/carrier construction.

`findings.json` accounts for all **23** final positive volumes: **8 unintended physical interferences**, 7 intended electrical endpoint-envelope contacts whose actual termination is unqualified, 4 unimplemented carrier pin passages, and 4 unqualified source-reservation crossings. There is **one disconnected fixed-tail contact, 0.581013 mm**. Thus the acceptance result is **FAIL integration**, even though all 140 saved native shapes and the 108/27 solids in the two reopened STEP files are valid and closed. The 2,937 pair records are retained; no broad group exclusion hides the failed route.

The 4,344 in-line USB comparisons cover 181 angles and have zero intersections, with 0.58 mm minimum nominal gap. The 2,172 offset USB comparisons also have zero intersections, with 29 mm minimum gap to the tested pod/input shell. This does not qualify arbitrary cables, new S12 integration, primary routing or lock ergonomics. All 85 retained old collar shapes match their translated geometry descriptors; internal stops/detents remain the frozen mechanism, not a new endurance result. Active-FPC comparisons use a stronger R24.8..30.7 annular envelope justified by the frozen R25..30.5 path plus0.16 mm total thickness; nonoverlapping AABBs provide conservative lower-bound gaps, explicitly tagged in each row.

**Disposition:** one useful, editable failed allocation; no accepted smaller product. The numeric lower bounds and exact obstructions are the output. New routing, approved terminal/fanout construction and S12 fit would be separate implementation work, not implied completion of this bounded pass.
