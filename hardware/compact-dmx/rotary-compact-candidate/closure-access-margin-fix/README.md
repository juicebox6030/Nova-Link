# CAF-R2 — closure-driver passage margin

**Targeted geometric correction; product HOLD.** This parent-authored revision follows [Astra's CAF-R1](../closure-access-fix/README.md), which removed the four installed-lid driver collisions identified by GLM Flash. Parent verification found that CAF-R1 still allowed accidental zero-distance contact between the driver tip plane and a ledge at a passage entrance. CAF-R2 removes that contact without moving any components.

Four Ø5.5 mm passages at X −110/−32, Y ±32 now start at Z4.0 and end at Z41.5. The existing Ø5 tool envelopes extend from Z4.5 to Z40.5. Actual saved geometry has **0.25 mm nominal minimum tool-to-upper-shell distance**, with zero volume interference at all four positions. The change removes another 0.349388 mm³ from the upper shell. All material below Z4.0, all four 8.042477 mm² screw bearing seats, 355 other shapes and all 356 placements are preserved. The upper remains one valid closed connected solid.

The proposed radial tolerance budget is 0.25 − 0.10 hole-radius undersize − 0.05 driver-radius oversize − 0.05 axis error = **0.05 mm**. The cut starts 0.50 mm below the tool tip; allocating 0.10 mm each to cut-start and seating-datum errors leaves **0.30 mm**. These are engineering allocations, not supplier-qualified tolerances or strength limits. The 0.50 mm axial offset is not a solid-web thickness claim.

- [Editable FreeCAD](prototype.FCStd) · [STEP](prototype.step)
- [Dimensioned PDF](closure-section.pdf) · [SVG](closure-section.svg)
- [Saved-geometry verification](check.json) · [Patch measurements](patch.json) · [Receipt](receipt.json)

`check.py` independently imports the saved CAF-R1/CAF-R2 BReps, compares all unaffected shapes and placements with numeric tolerance 1e−12, checks the fixed upper is strictly subtractive, and checks all four tools and bearing seats. OCC check-state flags and last-bit numeric serialization are normalized; actual shape/topology changes are not ignored. `section.py` reopens the native document; `export.py` exports and reopens 150 valid closed STEP solids. The PDF was rendered and visually inspected.

CAF-R1's full 1,356 installed-driver pair checks, 334 conservative lid-insertion checks and 1,352 screw-insertion checks are **retained, not rerun**. Their noninterference results persist because the sole changed part is fixed and only loses material; seats and every other shape/placement remain unchanged. This does not establish load capacity, insulation or enclosure protection. The original reviewed CYL-R2, CAF-R1, frozen source boards and review snapshot remain unchanged; 77 input hashes are pinned.

From this directory, using existing local tools:

```sh
QT_QPA_PLATFORM=offscreen ALLOCATION_SCRIPT=build.py /home/juicebox/.local/bin/freecadcmd run.py
QT_QPA_PLATFORM=offscreen ALLOCATION_SCRIPT=check.py /home/juicebox/.local/bin/freecadcmd run.py
QT_QPA_PLATFORM=offscreen ALLOCATION_SCRIPT=section.py /home/juicebox/.local/bin/freecadcmd run.py
QT_QPA_PLATFORM=offscreen ALLOCATION_SCRIPT=export.py /home/juicebox/.local/bin/freecadcmd run.py
python3 draw.py
python3 verify.py
```

Regeneration can change native-file serialization and hashes; retain the original inventory and investigate differences rather than refreshing it silently. The reproduction commands verify geometry; the receipt pins this particular generated state.

The ports remain open holes. Sealing/caps, foreign-object access, local wall strength, screw/driver selection, material/process tolerances and torque remain unqualified. All previous source-installation, neck attachment, fuse/terminal, connector mating, fixture fit, mains/electrical, thermal, flex endurance and runtime gates remain open. No product-size improvement, firmware work, hardware testing or manufacturing release is claimed.
