# CYL-R1 — bounded phase-0 cylindrical screen, HOLD

This is a **partial dimensional screen**, not an accepted compact envelope or a retained mechanical assembly. No new FreeCAD/STEP assembly is issued. The one arrangement reduces width but does not establish a materially smaller complete product: its classic panel-to-panel planning length is297.131 mm,22.131 mm longer than the already rejected CIR275 comparison. Bounding-box volume falls only6.835%, before the unresolved construction below. This is an engineering stop decision for this bounded pass, not a numerical owner acceptance criterion or proof that cylindrical sources cannot work. No supply-family or alternative-arrangement loop was undertaken.

The stray `Current source125V?` fragment is ignored as corrected by the parent. IRM20-12, its existing mains/derating assumptions,12 V isolated bus and5 V/1.5 A USB remain unchanged. Both S12 boards, all CIR geometry and the sidecar are untouched. Parent records remain authoritative; this README is the task-local checkpoint.

## One arrangement and its assumptions

The81×52×44 inherited whole-carrier reservation is recentered by−2 mm in Z, so its cross-section is Y±26/Z±22. The maximum module remains52.9×27.7×24.5 with4.5 mm maximum pin projection. Module top/bottom become Z12/−12.5 and pin bottom−17: the reserved top22 and bottom−22 retain10/5 mm, respectively. The61×32×1.6 planning carrier would be Z−15.1..−13.5 with four pin passages, but **is not treated as retained**. The inherited0.25 mm film would occupy Z−22.75..−22.5, spanning53 mm width; its outer corner radius34.926 mm fits the proposed35.1 mm bore nominally, but leaves only−0.026 mm after a−0.2 mm bore allowance. This is an additional concrete tolerance failure, not waived film space. Film grade, retention and installation approval remain open.

An additional0.5 mm on every reservation face gives82×53×45. The reserved corner radius34.7635 mm plus proposed3 mm wall leads to the screened OD76.2/ID70.2. The bore has a−0.2 mm engineering allowance, not a supplier tolerance. Only0.1365 mm remains at the rectangular tolerance-envelope corner. The round housing, split/seam, bosses, retained carrier and insertion tooling have not been designed; no material or strength approval follows from this radial arithmetic.

Three stationary L/N/PE corridors use OD4.5 wire plus0.5 mm radial assembly allowance, axes Y−8/0/+8,Z−29. They remain outside the insulation reservation, with3.75 mm to its toleranced bottom and2.5 mm between adjacent screens. These are engineering wire envelopes, not a selected cable's ratings. Two tangential R12 arcs change Z from−29 to−16 over21.3307 mm axial run. `trunk-centrelines.json` contains continuous paths, not disconnected named endpoints. They cover **only the source-to-core transition**, not complete electrical terminals. The trial linear conical bore35.1→21.5 mm fails by0.039478 mm at an intermediate section. A local relief could address this small collision, but it would not close the film/retention/termination interfaces or reverse the length result; it was not silently added.

Axial allocation:88 mm source bay (81 plus two0.5 mm tolerances and two3 mm end walls),21.3307 mm transition, unchanged87 mm CIR core, two20 mm engineering termination/tool regions, then actual nominal connector rear depths. The20 mm regions are explicit planning allowances, **not demonstrated sufficient** for selected insulated terminals, wire bends or tools. Front projections and mated cables are not included. Therefore these are panel-to-panel planning values, not complete product dimensions or universal lower bounds:

| Interface comparison | Panel allocation | Transverse screen | Box-volume relative to CIR275×91×74 |
|---|---:|---:|---:|
| Classic30.4+30.4 mm rear |297.131 mm|76.2×76.2 mm|93.165%|
| TRUE1 31.2+32.8 mm rear |300.331 mm|76.2×76.2 mm|94.168%|
| NEMA flange comparison45.3+43.6 mm rear |325.231 mm|76.2×76.2 mm|101.975%|

The NEMA flange row is **not a selection**: molded NEMA cord construction remains intended and lacks a selected gland/cord/strain-relief envelope. Compared with330×89×72, the classic planning box is81.587% of the volume; neither historical baseline is an approved finished construction. Comparing unlike terminal completeness cannot establish a qualified percentage improvement. No installed mate, latch or hand pose is invented. Classic B outlet still requires a B-to-A jumper, not direct mating to fixture A.

## Actual CIR/S12 evidence and exact gaps

FreeCAD opens the frozen360-shape native document read-only. `native-screen.json` records251 source-board/lock objects including their actual bounds, and181 angular axial-separation screens. Source bay ends X−21.3307; the original rotating bodies and USB are farther +X at every rotation about X. This establishes **source-bay-only** axial separation, not full neck/endcap/plug-relief/cable or lock-release assembly acceptance. Existing13 detents, stops, fixed-length active flex and local board positions are unmodified and remain covered only by their frozen CIR proofs. No fresh whole-assembly Boolean or STEP reopen PASS is claimed.

The source Z recenter changes all four pin endpoints by−2 mm; old CIR primary/secondary wires cannot be called connected without rerouting. Actual S12 J0/J2/J3 pads and circuits remain unchanged. Primary branch/fuse/insulated terminal constructions, carrier load paths across the installation reservation, secondary routing to actual J0, film support, and source/board insertion sequence are not closed. They are the exact interfaces needed before an editable integrated assembly can be responsibly produced. The current screen does not supply floating support blocks or label electrical endpoint gaps as contacts.

## Sources and reproduction

`sources.json` records retrieved primary PDF URLs, page callouts and SHA256s. Mean Well IRM20 mechanical drawing p3 specifies body/pin dimensions; installation manual p1(2) specifies bottom/Mylar and surrounding distances. The81×52×44 whole-carrier box and0.25 mm film are inherited engineering allocations, not manufacturer housing requirements. CI/CME frozen contracts retain exact connector provenance and missing mating transforms. No new download, source family, electrical change or software/hardware evaluation was performed.

Commands from repository root:

```sh
python3 hardware/compact-dmx/rotary-compact-candidate/cylindrical-source-repack/screen.py
QT_QPA_PLATFORM=offscreen ALLOCATION_SCRIPT=read-native.py /home/juicebox/.local/bin/freecadcmd hardware/compact-dmx/rotary-compact-candidate/cylindrical-source-repack/run.py
python3 hardware/compact-dmx/rotary-compact-candidate/cylindrical-source-repack/check.py
python3 hardware/compact-dmx/rotary-compact-candidate/cylindrical-source-repack/draw.py
python3 hardware/compact-dmx/rotary-compact-candidate/cylindrical-source-repack/verify.py
```

`freeze.py` was run once before screening; do not rerun to conceal mutation. Receipt verification reports hash integrity separately from geometry failures. SVG/PDF use the same geometry and labeled scale; the PDF was rendered with existing `pdftoppm` and visually inspected. No CAD/STEP is present because this pass stops at phase0. S12 protection/startup/routing/thermal gates, source installation/safety, flex equilibrium/endurance, actual USB cable acceptance, manufacturing and owner compactness acceptance all remain UNMET.
