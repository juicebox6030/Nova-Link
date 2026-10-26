# Unplaced USB/NOR physical integration candidates

Only this new directory is owned/changed. Existing power circuit, BOM, 37-part placement, library and CAD remain untouched. Two editable footprints, a generator, independent numeric/pin checker and actual KiCad SVG/PDF plots are supplied. The inspection `.kicad_pcb` is not a product board, has no routing or outline, and has not passed product DRC/assembly qualification.

## Sources and coordinate conventions

Hirose **EDC3-61479**, revision entry1 dated2015-12-10, released2015-12-11, sheets1–2; exact CX70M-24P1. Current retrieved drawing bears Oct2026 watermark. Exact handling guide Rev2.0,2022-04-15, pp5/11/12 supplies solder-side pin map, recommended copper and stencil. Direct CLI retrieval failed403; existing T3 browser same-origin fetch recovered both PDFs with HTTP200. Hashes/URLs are in sources.json. Drawing pages and guide5/11/12 were rendered and visually inspected; no raster scaling generated dimensions.

USB datum is the midpoint of the six signal plated holes, viewed from PCB top; +Y points toward the mating edge. Contact holes B9,B8,B7,B6,B5,B4 are x−2,−1.2,−.4,.4,1.2,2 at y0; Ø.4 finished hole with Ø.6 copper. The18 SMT contacts are B12,B11,B10,A1…A12,B3,B2,B1 at x−3.4…3.4, pitch.4, y−.925; copper.23×.85. Two extra .46×.85 SMT shell lands at x±3.915 are **not additional USB contacts**. Signal stencil openings are.25 wide for16 interior SMT contacts and.23 for the two end contacts per guidep12, despite its general100% statement. Stencil thickness recommendation is.10mm. Hole stencil openingsØ.6 are present. Shell slots have .6×1.7 drills; top copper1.2×2.3 at(±5.55,−.45), lower at(±5.55,4.6) with inward copper extension to x±4.85. Six shell attachments use proposed local `SH`; two overlapping lower extensions add primitives, not physical terminals. **No SH net binding exists in the current schematic.** Ground/ESD/chassis policy and attachment naming must be integrated explicitly.

Copper shapes follow these dimensioned extents. Lower stencil openings are1.3×2.3 centred at±5.5. The supplied rectangular stencil primitives do not reproduce the reference's rounded shell stencil corners; stencil rounding/process approval is an explicit remaining gate. Mask openings currently equal copper geometry; manufacturer mask expansion is not specified in these sources. Paste and mask are editable separate primitives. No isolated mechanical locator holes are inferred: the six signal holes and four shell slots are plated attachments.

The notch guide is on Dwgs.User, **not automatically inserted Edge.Cuts**: width9.34 (x±4.67), rear edge y.55, inner cornersR.3 (centres±4.37,.85), open toward nominal board edge y7.2. Copper overall span12.3. Outline/cutout integration must preserve side tongues and attachment copper. Example only: aligning board edge to CADy51 gives datumy43.8 and notch rear44.35, versus provisional slot rear45.1; these are different geometries, not accepted fit. No origin is assigned to the product board.

Hirose recommends **PCB0.8mm**; the source supplies no approved PCB-thickness tolerance range. Existing PCB1.0mm is therefore **not qualified**. Drawing's free mounting reference shows approximately1.30 above top and1.56 below bottom at.8mm PCB (total3.66); do not transplant these projections to1mm board or treat parenthesized reference dimensions as tolerance limits. Body width11.4,length8.35. Courtyard is an added design margin, not manufacturer qualification. The current primary product page marks this exact part **Not Recommended for New Designs** (page updated2026-10-06, read2026-10-22); no substitution was authorized or made.

Renesas **DS-AT25SF161B-188 RevH,2024-09-19**, p59 section15.3 describes MHB5×6×.6DFN. Top-view local pin1 is upper left; left1–4 and right8–5 at1.27 pitch. E6.0±.1 is horizontal, D5.0±.1 vertical; height.45–.60. Exposed pad E2=3.2–3.6,D2=3.8–4.2; terminal width.35–.48,length.50–.75. EP is not internally connected; notes3–4 recommend solder/ground attachment for EMI and mechanical stability. LocalEP9 matches existing U2.9=GND_USB.

**NOR lands are derived prototype geometry, not an exact manufacturer recommended PCB land.** Chosen signal lands1.2×.6 centredx±2.7 provide external toe and heel allowances around the package range; EP copper3.4×4 nominal. Four1.4×1.7 paste windows give70% nominal EP area; mask equals copper. These stencil/mask/land choices need assembler/DFM approval, thermal/voiding review and source package-tolerance review. No thermal vias are invented. Courtyard7.1×5.6 encloses lands and maximum body with design margin. Mounted projection is up to.6mm above seating plane plus solder/process allowance; no below-board projection absent vias. This package does not prescribe a particular PCB thickness or board cutout.

## Electrical contract and checks

`verify.py` independently checks source-dimensioned contact coordinates/sizes and actual exported U2/J_USB pin nets.24 USB contacts match the power-only boundary; all data/SBU pads NC; A5/B5 each have separate5.1k1% Rd toGND_USB. U2 pins1–8 match CS/MISO/WP/GND/MOSI/SCK/HOLD/VCC; EP9 ground agrees with datasheet recommendation. USB shell pins are missing from the boundary and intentionally not silently tied to signal ground. No existing electrical mismatch was found for the33 captured identifiers; shell integration remains incomplete.

Run using existing tools:

```
flatpak run --command=python3 org.kicad.KiCad hardware/compact-dmx/eda/service-footprints/generate.py
flatpak run --command=python3 org.kicad.KiCad hardware/compact-dmx/eda/service-footprints/verify.py
flatpak run --command=kicad-cli org.kicad.KiCad pcb export svg --layers F.Cu,F.Fab,F.CrtYd,Dwgs.User --mode-single --page-size-mode 2 -o hardware/compact-dmx/eda/service-footprints/footprints.svg hardware/compact-dmx/eda/service-footprints/footprints.kicad_pcb
flatpak run --command=kicad-cli org.kicad.KiCad pcb export pdf --layers F.Cu,F.Fab,F.CrtYd,Dwgs.User --mode-single -o hardware/compact-dmx/eda/service-footprints/footprints.pdf hardware/compact-dmx/eda/service-footprints/footprints.kicad_pcb
```

This is physical-integration candidate evidence, not source-complete manufacturing acceptance. Remaining gates: connector lifecycle, thickness/tolerances, cutout/shell circuit, stencil/mask details, NOR land/process approval, actual placement/height/access, routing/isolation and assembly tests. No firmware or hardware operation occurred.
