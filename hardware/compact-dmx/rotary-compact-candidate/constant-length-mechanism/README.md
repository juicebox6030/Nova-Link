# Constant-length mechanism — bounded failed assembly candidate

2026-10-23; requested Astra low / standard. Own path only. **Stop disposition: the constant-length path works geometrically, but this particular Ø66 mechanism is not an accepted assembled prototype.** Its clamp/stiffener construction and retention joints fail completion. The failed details are retained in editable CAD and checks, rather than omitted from a purported PASS. This is not a proof that compact clocksprings are impossible. No baseline, parent `.tools`, other candidate, circuit, BOM, canonical record, mains or PE geometry was changed.

## What is actually present

- `motion.py`, `motion.json`: independent reimplementation of the supplied beta-CDF family, 181 positions, 8193 stations per position. Exact copied parent evidence is `parent-screen.py/json`.
- `poses.json`: three finite-thickness normal-offset ribbons, −90/0/+90°. CAD uses 2049 stations; its chord approximation bounds are explicit. These are closed, faceted BReps, not smooth supplier manufacturing surfaces.
- `build.py`, `mechanism.FCStd`, `pose--90.step`, `pose-0.step`, `pose-90.step`: editable/source-regenerable diagnostic assembly. The FreeCAD spreadsheet records dimensions but does not drive the Part features; edit the Python parameters to regenerate geometry. STEP includes the unchanged Ø48×142 core *envelope*, not an approved mains assembly.
- `exploded.step`: separated diagnostic parts, not a proven assembly sequence. The retained failed joints prevent a released service/assembly instruction.
- `cad-checks.json`: every shape validity/solid count, three-pose ribbon checks, selected stationary/moving checks, and every positive neutral intersection. No support-collision blanket exclusion.
- `mechanism-screen.py/json`: 181 analytic keeper/stop/bay screens, explicit tolerance allocations, target torque arithmetic and the failed clamp stack.
- `sections.svg/pdf`, `sections-preview.png`: same vector geometry in SVG/PDF; PDF raster was visually inspected. These drawings label the failure.
- `sources.json`, `receipt.json`, `verify.py`: primary source evidence, artifact hashes and narrow acceptance checks.

## Geometry, source facts and packing

Core axis X remains X0..142, radius24. Shell X42..98.8, OD66/ID64, 1mm wall. Complete **locked** trial collar including index pull head is X34.5..98.8 = **64.3mm**, exceeding the requested approximate45–55mm axial target. A 4.2mm release stroke reaches X30.3: **68.5mm operating span**. All remains within the142mm axial core envelope; that does not establish endcap/fixture access. Baseline comparison is Ø84×26 collar, not an equivalently complete source/lock packing claim.

Active FPC occupies X47..67, radial centreline25..30.5. Total stack0.16mm is an allocated maximum, not a supplier-approved stack. Width20mm; two8mm conductors,1mm gap,1.5mm edge margins; single70µm RA copper layer. No plated features or stiffeners in the active bend. Static tails expand to24mm width X45..69. The inner tail continues θ−0.30..0, outer θ0..+0.30 relative to the rotating end. Their linear radial slope matches the family at both endpoints, including the nonzero tangent deviation: inner0.109426745°, outer0.089694089°. No sharp tangential kink is substituted. **A controlled stiffness transition is not completed**, as explained below.

The dielectric inner guide outerR24.6 and outer guide innerR31 give minimum nominal active-ribbon gaps0.3200 and0.4200mm. Guide reliefs accommodate the static tails. M1 ear screws lie outside active width; nominal nearest screw-head-to-active axial gap0.35mm. Materials proposed for further engineering: PEEK dielectric guide/shoes, acetal bearing surfaces, stainless index/stop pins; no manufacturer material allowables or dielectric/flammability system approval are asserted. The stationary saddles are contact envelopes, not qualified clamp preload or permission to penetrate the mains core.

The independent stop is at X72.5..73.5, radius28.5, Ø2 peg in an annular sector. Its radial faces account for finite peg radius using asin(1/28.5), giving nominal ±90° contact. The index ring X43..44.5 has13 Ø2.2 holes at R28.5/15° spacing. Ø2 pin must retract4.2mm toward−X before rotation; holding it engaged between detents is prohibited. A return spring, captive release retention and proof against partial engagement/bypass are **not completed**. The ring and frame are not a qualified durable lock.

The provisional source board is25×18×1 at X73.8..98.8, Y25.1..26.1, Z±9. The +1.8mm local axial shift separates it from the fixed stop plate by0.30mm at all angles. Components target3.2mm above PCB; true outer corner radius sqrt(29.3²+9²)=30.65mm, below shell innerR32. Actual Sol placement, mounting, thermal and fanout remain pending. No actual board-fit acceptance is inferred from this envelope.

GCT primary USB4105 drawing **B4,18 December2023, sheet1** gives body8.94×7.35, above-PCB height3.31, shell stake S±0.15; proposed order **USB4105-GF-A-060**, S0.60. This is different from USB4125. Board bottomR25.1/topR26.1; maximum proposed stake projection reaches radial coordinate25.35 before off-axis stake position is considered. The connector nominal outer corner radius sqrt(29.41²+4.47²)=29.75mm. Generic two-decimal dimensions are±0.15 unless separately noted; mounting-pattern tolerance±0.05. The shell model is a sourced bounding envelope, not supplier 3D CAD or complete land registration. Stake longitudinal positions are a placement screen pending actual Sol footprint integration.

The source connector provides D+/D− contacts; Sol owns their charger connection and source qualification. Drawing electrical ratings5A collective VBUS,6.25A collective GND and operating−40..85°C are connector ratings only. The drawing's20,000 mating cycles do not rate the rotary flex. Drawing shoulder-related1.85mm minimum and6.5mm maximum plug height do not specify a universal overmold. A12×6.5×12 engineering plug screen approaches+X at X98.8..110.8 and clears the nominal core by0.58mm. Width and length are engineering choices, not manufacturer plug maxima. No universal plug, fixture or full endcap clearance claim.

## Precise failed details / bounded stop

1. **Chosen stiffened clamp stack does not fit.** At the fixed tail's far end, normal-offset inner surface is R24.905676201; constant-radius backing outer surface isR24.9. Available gap is only0.005676201mm. A proposed0.20mm static stiffener plus0.05mm assembly gap needs another **0.244323799mm**. Those values are engineering choices, not a claimed supplier minimum. Adding that stiffener would intersect the present backing; omitting it does not establish an acceptable unsupported copper/clamp transition. A changed shoe/clip/stiffener construction must be modeled and qualified, not silently inserted into these exports.
2. **The positive-Y rotor feature contains two disconnected solids.** The moving backing island has no completed structural connection. Valid closed solids are not a connected load path. It cannot be manufactured as the claimed single half without a joint or changed geometry.
3. **Frame screw heads lack completed access counterbores.** Each currently overlaps the positive-Y rotor by approximately0.57334mm³. Fixed ear screws also intersect the guide links by approximately0.04968mm³ each. These are retained defects, not intentional thread engagement.
4. Fixed backing/guide-link overlaps and stop-track/rear-saddle overlap are separately reported. They need deliberate fusion/joint and assembly treatment. The M1 pilot-hole thread engagement overlaps are distinguishable but do not certify strength. Do not label all positive-volume contacts as intended.

The first simple stop-plane interference was corrected locally; the final stop/board axial separation is explicit. No repeated redesign or alternative flex family was pursued after the above clamp/retention completion failures. **Next bounded direction:** retain the kinematic family and revise the static clamp/retention joints with actual stiffness/preload construction, then integrate Sol's actual board. This is a concrete design objection to this candidate, not a request for external services or owner hardware work.

## Checks and what they do not establish

The181-position family reproduces length1046.167655992167mm, maximum length error5.0e−12mm, minimum screened inter-turn surface gap0.139821868mm and minimum bend radius24.9999544mm. Fixed radii and endpoint slopes are verified. These are dense numerical screens, not continuum or physical equilibrium proofs. Active-ribbon CAD checks and stationary/moving checks are reported independently from the failed neutral assembly joints.

Allocated bearing radial clearance0.15mm minus two0.03mm radial tolerances and0.05mm runout leaves0.04mm. Stop-to-board0.30 minus two0.05mm location tolerances and0.05mm endplay leaves0.15mm. Ear clearance0.35 with the same allocation leaves0.20mm. None bounds elastic lateral wander, creep, assembly preload or actual supplier flex thickness. The clamp gap fails even before ordinary process tolerances.

For a **target**, not rating,0.5Nm applied at R28.5: tangential force17.54N; Ø2 pin single-shear stress5.58MPa;1.5mm index-ring bearing stress5.85MPa; allocated1.7mm pin cantilever gives37.97MPa bending. No material allowable, fatigue, impact, polymer creep, pullout or retention qualification exists. No cycle count is inferred from static radius.

Active-copper-only resistance:0.064418Ω at20°C and0.080873Ω at85°C using engineering copper resistivity0.017241Ω·mm²/m and α0.00393/K. At1.5A this is0.12131V drop/0.18196W; that is **not** necessarily converter input current. At2A it is0.16175V/0.32349W. With allocated−10% copper and7.8mm trace width, hot resistance increases by0.56/0.4914 to about0.0922Ω. Static tails/fanout, terminations and controller losses are additional. Sol owns actual TPS63070→TPS25810 source budget and whether IRM10/IRM20 can supply the declared line/temperature/current. No1.5A port, module thermal, safety, mains or endcap claim is made here.

Physical elastic guidance/equilibrium, friction, forces/hysteresis, dynamic stack approval, active-to-stiffener transition, static electrical fanout, durable locking/release, source-board retention, cable/fixture fit and manufacturing/safety release all remain open. Mains/PE stay stationary; no slip rings or wire-torsion substitute.

## Reproduce locally

From repo root, with existing tools only:

```sh
python hardware/compact-dmx/rotary-compact-candidate/constant-length-mechanism/motion.py
python hardware/compact-dmx/rotary-compact-candidate/constant-length-mechanism/mechanism-screen.py
NOVA_ROTARY_CANDIDATE="$PWD/hardware/compact-dmx/rotary-compact-candidate/constant-length-mechanism" QT_QPA_PLATFORM=offscreen /home/juicebox/.local/bin/freecadcmd hardware/compact-dmx/rotary-compact-candidate/constant-length-mechanism/build.py
python hardware/compact-dmx/rotary-compact-candidate/constant-length-mechanism/draw.py
python hardware/compact-dmx/rotary-compact-candidate/constant-length-mechanism/verify.py
```

`verify.py` verifies a **failed-candidate evidence package**, not an assembled mechanism PASS. FreeCAD's process exit code alone is insufficient; inspect `cad-checks.json` and build log. Regeneration changes native/STEP serialization hashes; the receipt must be regenerated deliberately after reviewing results, never blindly by the verifier.
