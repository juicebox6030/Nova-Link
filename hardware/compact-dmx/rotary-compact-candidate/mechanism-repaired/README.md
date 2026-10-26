# Repaired constant-length collar — geometric prototype

2026-10-23. Requested Astra low/default. Own path only: `hardware/compact-dmx/rotary-compact-candidate/mechanism-repaired/`. Shared main HEAD `b42c0e6284aac734fde851c69146abf73920f337`. No baseline, failed candidate, power circuit, source routing, BOM, canonical document, mains/PE, hardware, firmware or Git publication changes.

Owner correction retained: “Repair the concrete defects in your just-completed constant-length collar; do not return another incomplete pass merely identifying your own readily repairable geometry.” The original failed receipt and29 artifact hashes are preserved in `failed-receipt.json` and `frozen-inputs.json`; the verifier compares them against the read-only original folder.

This package repairs the modeled clamp, structural connection, screw passage and captive-lock defects. **Geometric prototype acceptance is distinct from supplier/physical qualification.** The active flex remains a prescribed constant-length path family, not a demonstrated passive elastic equilibrium. See `receipt.json` for final check counts and `checks.json` for every modeled component pair.

## Exact repairs

| Defect | Modeled repair |
|---|---|
| Fixed backing/stiffener shortfall | Fixed backing outer radius24.6, inner24.1. Real0.05 adhesive and0.20 polyimide stiffener layers follow the static-tail normal. Minimum unpadded gap0.055676mm; fitted compliant ear pads fill it outside the active width. Moving backing inner30.9/outer31.5 has the same stack and approximately0.055676mm minimum gap. |
| Abrupt/omitted static transition | Adhesive and stiffener taper to zero over0.08rad: about2.0mm fixed /2.44mm moving. The centreline and nonzero endpoint slope remain continuous. Active bend has no plated features/stiffeners. Skived/graded laminate process is an engineering proposal requiring supplier approval. |
| Disconnected moving backing | Two radial bridges at X45..46 and68..69, R31.35..32.15, angle0.08..0.22rad join the backing to the shell outside the active X47..67 flex width. Both structural halves are independently one connected closed solid. |
| Four frame-head collisions | Ø1.90 counterbores run from Y3 outward through the positive half, with Ø1.10 shaft clearance and Ø0.76 negative-half pilot. M1 envelope headØ1.80/shaftØ1.00; only the bounded negative-half thread region overlaps. Ø1.20 tool cylinders clear the assembled body. |
| Fixed ear screw/guide intersections | Actual Ø1.10 clearance cuts in guide links; fixed backing retains its separate Ø0.76 pilot/thread envelope. Small curved shim/link overlap is trimmed against the real fused support, not exempted. |
| Three overlapping stationary joints | Journals, links, backing, stop track, saddles and index housing are fused into one valid connected `StationarySpool`. No overlapping mount parts remain. Two explicit0.10mm external core bondline rings at X40..42 and72..74 join spool to the unchanged core envelope; no core penetration. Bond strength/creep/material compatibility remain qualification gates. |
| Missing lock spring/captivity | Actual annular spring envelope, guided Ø2 pin, Ø3.6 captive flange, front shoulder, rear travel-stop annulus integral with the tool-removable threaded cap, removable threaded knob and keyed stem. No hold-open latch. Stroke4.2; engagement1.3; released tip clearance2.9. Independent angular hard stops remain. |
| Additional full-pair findings | Re-drilled13 index holes through the final fused frame so it cannot refill their back ends. Reduced housing nose toØ4.6 from X42.1..42.8, clearing front bearing by0.20mm. |

All dimensions in mm. Proposed PEEK stationary/rotor structure and dielectric shoes, acetal bearing surfaces, polyimide stiffeners, insulating adhesive/compliant ear pads and stainless index pin/screws are **engineering material choices**, not approved supplier parts or allowable stresses. The native model uses connected structural parts, not body-only disconnected envelopes. The M1 thread strength, thin-wall machining, adhesive taper and bearing finish require prototype DFM and physical qualification.

## Geometry and packing

- Unchanged stationary core: Ø48, X0..142. Mains, PE and isolated module remain stationary. No slip rings or wire-torsion substitute.
- Collar OD66; shell X42..98.8, ID64. Locked complete mechanism X31..98.8 = **67.8mm**. Released head reaches X26.8 = **72.0mm operating span**. This is3.5mm longer than the failed64.3/68.5 trial, needed for a real spring cavity and captive travel stops. It exceeds the original45–55mm axial target; no false compactness acceptance.
- Active flex: X47..67, width20, allocated maximum stack0.16, single RA70µm layer/two8mm traces. Active centreline radii25..30.5. Static tails X45..69 with ears outside active width. Inner guideR24.6 and outer guideR31 retain0.32/0.42 nominal active clearances. CAD is a finite-thickness, bounded polygon approximation of the smooth path, not production bend tooling.
- Static ear screws do not enter the active width. Screw-head axial gap0.35. Both normal-offset tails preserve endpoint slope0.30/(2π) mm/rad:0.109426745° from tangent at R25 and0.089694089° at R30.5. No kink is substituted for that slope.
- Stop track X72.5..73.5; Ø2 peg atR28.5. Finite pin radius is included in stop face angle using asin(1/28.5), giving nominal±90° contact.13 detents span±90° at15° intervals. The stops are independent of the index pin and outside the flex bay. The stop stub is fused into the connected negative rotor half, not a loose touching pin; its proposed polymer material and cantilever strength need qualification. The carrier/track face is the nominal axial thrust datum. Opposite journal shoulder geometry permits up to0.20mm positive axial play before tolerances; qualification must control axial wandering and its effect on the planar flex family. At that extreme pin engagement reduces from1.3 to1.1mm. No loaded axial-stability claim is made.
- Source board remains **PLACEHOLDER**,25axial×18tangential×1 nominal, X73.8..98.8/Y25.1..26.1/Z±9, requiring the port mouth at axial+X. Parent's frozen regulated board uses another port edge; the new axial routing candidate was not read or integrated.
- Source height reserve is now **3.46 maximum +0.15 assembly allowance** above nominal PCB top, reachingY29.71. The0.15 allocation covers +0.10 PCB thickness and +0.05 assembly position. True reserved corner radius is about31.043mm, leaving about0.957mm to shell innerR32. This is envelope evidence, not actual32-component packing acceptance.
- GCT USB4105-GF-A: primary B4 drawing nominal8.94wide×7.35long×3.31high. Parent-directed conservative screening envelope9.09×7.65×3.46 is retained;7.65 is a conservative length screen, not a new manufacturer tolerance claim. Default stake0.95±0.15 and proposed PCB1.0±0.1 produce≤0.20 underside projection. The model has finite stake envelopes and PCB holes; their registration remains placeholder until the axial board is integrated. No USB4125 dimensions are reused.
- Engineering plug screen12wide×6.5high×12long approaches axially at X98.8..110.8, with nominal0.58 clearance above the core. Only6.5 maximum height/1.85 shoulder-related spacing come from the GCT drawing; width/length are engineering test assumptions, not universal plug maxima. Existing endcaps/fixture clearance remain parent gates.

## Captive lock and spring contract

Carrier rearX34, frontX42.8; main OD6, noseOD4.6. Pin locked tipX44.3, flangeX40.8..41.4, knobX31..32.5. Front shoulderX41.4 defines full engagement. Pulling4.2mm brings flange rear face toX36.6 against the rear stop, preventing overtravel/ejection; pin tip thenX40.1,2.9 before the index faceX43. Cap has Ø0.60 spanner holes at ±2.6 from its axis; Ø0.40 tool pins clear the knob and housing. The rear stop is part of the removable cap so the flange can pass through the open housing during assembly. The knob is a separate M1.2-envelope threaded part with0.8mm engagement and a0.6mm-wide face slot. A flange D-flat atZ1.5 and housing key startingZ1.65 restrain stem rotation during knob service. Cap removal is a tool-only service operation; thread-lock process remains a qualification item.

Spring is a **modeled engineering envelope**, not a solid annulus to manufacture. Proposed wire0.20, mean coilØ3.0,5 active/7 total turns, free length7.0, solid1.4, installed5.8, fully released1.6. Target rate0.114N/mm is consistent with k=Gd⁴/(8D³n) using an explicitly assumed G77000MPa; it is not a sourced spring rating. Nominal preload0.1368N, maximum-stroke force0.6156N. With allocated±15% rate, free length−0.1 and installed length+0.05, minimum return force is about0.102N. Proposed friction acceptance is <0.08N; this must be measured. Solid-height margin0.20 nominal and0.065 under the stated wire/length allocations. Spring sourcing, stress, temperature and life remain open.

No hold-open groove permits bypassing spring return. Engaged rotation between detents is geometrically blocked; the181-position check expects interference for those prohibited states, not a fake all-angle locked PASS. At the13 detents the full pin clears its hole. Between holes the pin cannot advance its final1.3mm; assembly instructions require a witness band at locked-shaft X33.4..34.7, hidden only on full engagement. A marking is not substituted for mechanical captivity. Partial-engagement strength and contamination/jamming remain physical tests.

## Assembly and tool access

1. Machine/finish the connected stationary spool and its bores; assemble its static tail adhesive/stiffener, fitted ear pads, shoes and M1 screws before installing rotor halves. Ø1.20 radial driver paths are checked against this stationary subassembly.
2. Bond the spool's two specified external bondlines to the Ø48 core before fixed endcaps obstruct axial assembly. This does not authorize changes inside the mains core. Validate bond preparation, material compatibility, process and retention before any product release.
3. Assemble the rotating tail to the positive half using the modeled inward Ø1.40 access passages and a Ø1.20 driver, before installing around the core. Supplier-form the static laminate; do not manually kink the active copper. Flex placement is prescribed kinematics, not proven free-form equilibrium.
4. Install the two rotor halves around the spool; four frame M1 screws use the full head/shaft passages. Their driver cylinders clear the assembled neutral mechanism. Hole sizing/threads/torque are proposed, not purchased-fastener qualification.
5. With cap and knob removed, insert the keyed pin through the housing, then the spring over its rear shaft. Install the cap (which carries the rear stop) with its two-pin tool; attach the threaded slotted knob last. `containment.json` checks the rear insertion path, axial overtravel stops and stem anti-rotation interference. Front and rear shoulders bound travel. Verify automatic return and complete engagement at all13 detents. No torque rating is asserted.
6. Integrate the actual axial source board/static LV fanout only after its separate geometry is accepted. The placeholder and finite plug screen do not establish completed electrical routing, mounting or cable fit.

`access.json` distinguishes these assembly stages; it does not pretend the inward rotating-ear screws are accessible with the core already installed. All11 modeled tool paths are checked against their applicable parts. `exploded.step` separates those subassemblies for inspection.

## Evidence and limits

`checks.json` records **4,446 full component pairs**, three angles−90/0/+90 × locked/released. All modeled physical components are included; alternate pose ribbons and nonphysical component/plug reserves are not treated as simultaneous parts. Source PCB/connector/stake placeholders are also screened. The only positive volumes permitted are ten named screw/cap/knob thread interfaces, each with a numerical upper bound. `reopen.json` independently bounds those intersections to the actual thread regions; heads and mount bodies are not exempted.

`sweep.json` uses a frozen saved-BRep conservative envelope (`sweep-envelope.FCStd`) for181 released rigid-mechanism positions and181 locked-pin tests. The final cap/knob assembly repair is contained within that envelope. `containment.json` proves unchanged rotating geometry, the final pin/knob union within the original pin, and identical engagement-tip geometry. The only added stationary key lies atX<=41.4, at least0.6mm before every rotating part. Thus the final mechanism is covered without silently treating an older geometry as current. The active ribbon is independently reproduced by `motion.py`: constant length1046.167655992167, minimum screened surface gap0.139821868, minimum bendR24.9999544, maximum length error5.0e−12. Three full CAD poses include the actual finite ribbon. For intermediate angles, guides, core and frame remain outside its invariant radial/axial envelope; static stiffeners lie inward of the fixed endpoint and outward of the moving endpoint, and ear hardware is outside active width. This is a numerical geometric screen, not a continuum contact or elastic-equilibrium proof.

`clearances.json` measures saved-solid stiffener, core, screw-head and source-reserve gaps independently, and checks the integral stop stub. The saved native document and all seven STEP exports are reopened and checked for valid closed solids. Both structural halves and stationary spool must each have exactly one solid. Native spreadsheet dimensions are a reference; the editable Python source regenerates geometry. SVG/PDF share drawing primitives, and both rendered PDF previews were inspected.

`dimensions.json` holds independent arithmetic and tolerance allocations. Examples: bearing0.15 minus0.03+0.03+0.05 runout leaves0.04; nose/bearing0.20 under the same allocation leaves0.09; stop/board0.30 minus0.05+0.05+0.05 leaves0.15. The compliant ear pads absorb the modeled static gap; their preload/creep is not qualified by exact unloaded contact. External core bondline is0.10 nominal, with a proposed minimum0.04 under the stated dimensional allocations.

For an engineering0.5Nm target atR28.5, pin force17.54N, Ø2 single-shear stress5.58MPa,1.5mm ring bearing stress5.85MPa and allocated1.7mm cantilever bending stress37.97MPa. These are loads, **not ratings**; there are no approved material allowables, shock, wear, thread-pullout or creep results. Two2mm-wide core bond rings have about603mm² nominal cylindrical area; average shear alone cannot establish peel/thermal/retention strength.

Outstanding physical/supplier gates: approved dynamic FPC stack and transition process; passive equilibrium, friction and lateral stability; cycle life; spring source/return/jamming; thread locking and allowable loads; bond/creep and manufacture tolerances; actual axial source PCB/static fanout; USB thermal/current qualification; cable/endcap/fixture fit; unchanged mains/PE/module/barrier certification. No hardware operation, source-current guarantee or manufacturing release is claimed.

## Reproduce

Existing local tools only; from repo root:

```sh
python hardware/compact-dmx/rotary-compact-candidate/mechanism-repaired/motion.py
python hardware/compact-dmx/rotary-compact-candidate/mechanism-repaired/dimensions.py
NOVA_ROTARY_CANDIDATE="$PWD/hardware/compact-dmx/rotary-compact-candidate/mechanism-repaired" QT_QPA_PLATFORM=offscreen /home/juicebox/.local/bin/freecadcmd hardware/compact-dmx/rotary-compact-candidate/mechanism-repaired/run.py
NOVA_ROTARY_CANDIDATE="$PWD/hardware/compact-dmx/rotary-compact-candidate/mechanism-repaired" QT_QPA_PLATFORM=offscreen /home/juicebox/.local/bin/freecadcmd hardware/compact-dmx/rotary-compact-candidate/mechanism-repaired/access.py
NOVA_ROTARY_CANDIDATE="$PWD/hardware/compact-dmx/rotary-compact-candidate/mechanism-repaired" QT_QPA_PLATFORM=offscreen /home/juicebox/.local/bin/freecadcmd hardware/compact-dmx/rotary-compact-candidate/mechanism-repaired/sweep.py
NOVA_ROTARY_CANDIDATE="$PWD/hardware/compact-dmx/rotary-compact-candidate/mechanism-repaired" QT_QPA_PLATFORM=offscreen /home/juicebox/.local/bin/freecadcmd hardware/compact-dmx/rotary-compact-candidate/mechanism-repaired/reopen.py
NOVA_ROTARY_CANDIDATE="$PWD/hardware/compact-dmx/rotary-compact-candidate/mechanism-repaired" QT_QPA_PLATFORM=offscreen /home/juicebox/.local/bin/freecadcmd hardware/compact-dmx/rotary-compact-candidate/mechanism-repaired/containment.py
NOVA_ROTARY_CANDIDATE="$PWD/hardware/compact-dmx/rotary-compact-candidate/mechanism-repaired" QT_QPA_PLATFORM=offscreen /home/juicebox/.local/bin/freecadcmd hardware/compact-dmx/rotary-compact-candidate/mechanism-repaired/clearances.py
python hardware/compact-dmx/rotary-compact-candidate/mechanism-repaired/draw.py
python hardware/compact-dmx/rotary-compact-candidate/mechanism-repaired/verify.py
```

Inspect structured check outputs, not only FreeCAD's process status. Serialization timestamps can change FCStd/STEP hashes on deliberate regeneration; review results before issuing a new receipt. The verifier never blindly refreshes hashes.
