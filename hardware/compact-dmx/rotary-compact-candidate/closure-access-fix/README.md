# CAF-R1 — installed-lid closure-driver access correction

This copy fixes only the confirmed CYL-R2 closure-access defect. **Only `UpperShellRetention` changes.** Four Ø5.5 vertical passages now admit the existing Ø5 driver envelopes with the upper half installed. All 355 other saved shapes and all 356 placements are preserved. The upper remains one valid, closed, connected solid and is a strictly subtractive subset of its frozen source. No board, electrical, rotary, source-support, screw-position or envelope change is made.

The source receipt is pinned to `0cc43cc3a2596b44cfa81834fe26f41583948954af58fdb4d292100895d1d61f`; source native SHA256 is `353f9fcd5e6a771725632639dbf5fb40095d77c71f9f8ced0421ec723903e58b`. `inputs.json` freezes all 47 CYL-R2 files plus both actual S12 boards. The old candidate and review snapshot are untouched. This is implementation of one confirmed defect, not another review round.

## Reproduced failure and correction

| Driver centre X,Y (mm) | Original installed-upper overlap (mm³) | Repaired overlap (mm³) |
|---|---:|---:|
| −110,+32 |127.759469815|0|
| −110,−32 |127.757987959|0|
| −32,+32 |127.764876224|0|
| −32,−32 |127.837711055|0|

The original shell crosses each tool centreline between Z15.370426 and21.406775. The Ø2.4 clearance hole below Z5 did not provide a route through that outer shell.

Each new cut is Ø5.5, Z4.5..41.5, centred on the unchanged screw/tool axis. The actual allocated driver is Ø5, Z4.5..40.5. Nominal radial clearance is0.25 mm. A proposed budget of0.10 mm passage-radius undersize,0.05 mm driver-radius oversize and0.05 mm axis error leaves0.05 mm radial clearance. These are engineering allocations, not a selected driver or machining supplier's qualified limits.

All original upper material below Z4.5 is preserved exactly. The screw bearing plane remains Z3; the1.5 mm difference to the cut-start datum is **not a claim of a1.5 mm solid web**. Each Ø4 head still bears around the Ø2.4 hole on a0.8 mm radial land; the actual checked bearing area is8.042477 mm² at every seat, unchanged before/after. The Ø1.6 pilots, boss positions, source-retention ribs and lower half are untouched. The source shell's nominal OD77/ID71 and3 mm radial wall remain; the new holes intentionally perforate that wall locally. The four openings remove640.529790 mm³ without disconnecting the upper or its bosses. No torque, strength, fatigue or material rating is assigned.

## Correct assembly/access sequence

1. Follow the existing source/carrier assembly sequence with the upper removed. Keep the four closure screws out while lowering the upper half.
2. Lower the upper along−Z onto its original seam. A conservative continuous60 mm insertion/removal envelope is checked against all334 fixed physical parts present in this assembly state. It encloses every intermediate lid position, not just sampled endpoints. No positive-volume obstruction is found.
3. Insert the four closure screws through the open access passages with the upper **installed**. The head has0.75 mm nominal radial passage clearance; the shaft retains0.2 mm nominal clearance in the original Ø2.4 hole. The complete screw insertion envelopes are checked against1,352 physical-part pairs. Only the four original, individually bounded M2-shaft/Ø1.6-pilot engagements have positive volume. Thread forming/turning, screw selection and allowable torque remain unqualified.
4. Reach the seated heads with the existing Ø5 driver envelopes through the four ports. All four tools are checked against **all339 physical parts in the closed assembly**, including the installed upper, lower, screw heads, boards and retained mechanism:1,356 checks, zero volume interference. Tool-tip/head contact at Z4.5 is intentional face contact; it is not excluded from the check.
5. Reverse the sequence for access: remove closure screws before lifting the lid. No cap or plug is modeled. A later decision on caps, sealing, foreign-object access or insulation protection must preserve the proven tool route and receive its own construction assessment.

Only explicit nonphysical screens, unbuilt interface reservations and alternative ribbon poses are omitted from the physical-parts list. There is no exclusion of the upper, frames, boards or screw heads to obtain a tool PASS.

## Evidence and proof reuse

`build.py` opens the saved CYL-R2 native and applies only four cuts; it does not rerun unrelated construction. `check.py` reopens both files and proves all356 native shapes valid/closed/single-solid, all placements equal, and355 unchanged BReps equal in topology with numeric serialization differences below1e−12. It independently proves the upper adds zero material and preserves its seat region. `section.py` checks all four actual bearing areas. `prototype.step` exports150 physical solids and reopens150 valid closed solids; all lands remain in the native file, as in CYL-R2.

The former9,086 pair checks,181 rotary checks, corridor containment and source clearances are **not claimed as rerun**. Their geometric noninterference results are retained by the explicit delta proof: all other shapes and placements are unchanged, and the one fixed changed shape only loses material. Existing intended seat contacts are checked separately. This reasoning does not establish strength, enclosure protection or insulation acceptability after introducing holes.

`closure-section.svg/pdf` shows the actual repaired section, original obstruction ghost, full driver route, curved bore/outer exit and unchanged head/seat. The PDF was rendered with existing `pdftoppm` and visually inspected. The source script and native/STEP remain editable; no manufacturer geometry is invented for a selected bit, screw head recess or sealing cap.

## Reproduction

From this directory, with existing local tools:

```sh
QT_QPA_PLATFORM=offscreen ALLOCATION_SCRIPT=build.py /home/juicebox/.local/bin/freecadcmd run.py
QT_QPA_PLATFORM=offscreen ALLOCATION_SCRIPT=check.py /home/juicebox/.local/bin/freecadcmd run.py
QT_QPA_PLATFORM=offscreen ALLOCATION_SCRIPT=screw-insertion.py /home/juicebox/.local/bin/freecadcmd run.py
QT_QPA_PLATFORM=offscreen ALLOCATION_SCRIPT=section.py /home/juicebox/.local/bin/freecadcmd run.py
QT_QPA_PLATFORM=offscreen ALLOCATION_SCRIPT=export.py /home/juicebox/.local/bin/freecadcmd run.py
python3 draw.py
python3 verify.py
```

`freeze.py` was run once; do not refresh it to hide mutation. Actual S12 board hashes remain rotating `f1931419a9a326e5db8364302c8d59cf1586a1ae810676db475f92b45bb97c30` and stationary `d6f79be09ed5e7984f2f915d9d3b9399978f7412795d7fff4c0ef8d8caabdbdc`.

**Local closure-access correction: geometrically checked. Product: HOLD.** Source-installation exceptions, neck attachment, fuse/terminals, connector/fixture fit, strength, materials/process, thermal, electrical, physical and flex/endurance qualification remain unchanged and open. The ports add unqualified sealing/access questions; no IP, safety or manufacture acceptance is claimed. No new children, tools, purchases, vendor contact, hardware operation, firmware or git publication was used.
