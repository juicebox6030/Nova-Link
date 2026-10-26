# Bounded fixture metrology receipt — 2026-10-22

Result: **source geometry measured; compactDMX clearance remains unverified.**
Two CAD candidates were analyzed in this pass: GLP impression X5 STEP and one
CHAUVET E-910FC DWG conversion. Prior ETC conversion logs were read, not retried.
No design, cache original, tool installation, hardware, staging or publication work
was performed. Base revision: `b42c0e6284aac734fde851c69146abf73920f337`.

## GLP: what was actually read

Original manufacturer archive `GLP_impression_X5_CAD_Rev20240202-1.zip`, member
`GLP impression X5 3D Shell Rev20211111-1.stp`, already retrieved from GLP's
[official CAD URL](https://glp.de/files/products/impression-x5-product-data/GLP_impression_X5_CAD_Rev20240202-1.zip).
Archive SHA-256: `94d87167d1a155785ec6de431817982aecd296ba1767d4882c8d617ef2e61da5`.
STEP SHA-256: `25fed40decfcf0a511e4f6f78657a2386962d98e7a1f58fcea01bb32823af8e3`.
Internal `FILE_NAME` is `HUELLE_SW0001`, timestamp `2021-11-02T12:58:24`;
the member and archive revision dates are distinct.

FreeCAD 1.1.3 read all 4,519 faces: 1,026 planes, 1,167 cylinders, 466 cones,
478 tori, 1,153 B-spline surfaces, 83 extrusions, 108 spheres, 38 revolutions.
The original STEP has 62 `OPEN_SHELL` entities and zero `CLOSED_SHELL` entities.
FreeCAD returns 215 shells (6 closed) and **zero solids**. These counts describe
different topology representations; they do not establish missing assembly parts.

The original file has one `PRODUCT`, one surface part, no
`NEXT_ASSEMBLY_USAGE_OCCURRENCE`, no context-dependent assembly shape, and no
representation relationship with an assembly transform. `#269283` relates the
part shape to its surface representation. `#269340` and `#269349` are representation
maps used by the drawing/presentation mapped items, not component installation
placements. No assembly transform was applied or invented. All measurements below
use original source XYZ and an identity transform. Source Y is vertical in the
coherent orthographic view; this is not a connector mating coordinate system.

**Correction to the earlier bounding-box interpretation:** ordinary `BoundBox`
reports 289.95865 × 561.71029 × 452.36780 mm. The actual 0.4 mm tessellation spans
approximately 289.91483 × 482.32729 × 415.02809 mm. Four B-spline face bounding
boxes (imported faces 3672, 4114, 4116, 4158) extend above Y=450 mm while the
whole rendered mesh reaches only Y=417.52729 mm. The tighter FreeCAD
`optimalBoundingBox()` result is retained in `glp-x5/topology.json` and labeled
triangulation based. The ordinary box is loose; it is **not evidence of an
exploded assembly**. The rendering is spatially coherent without repositioning.
Neither box is an installed fit measurement, and this does not reconcile the
2021 model, 2023 drawing and current product's mounting configurations.

## Actual local mounting-feature measurements

Units are millimeters (`#269269`, `SI_UNIT(.MILLI.,.METRE.)`). These are nominal
analytic surface parameters, not dimensions measured from images.

- Two paired base mounting features: radius **11.10**, diameter **22.20**;
  axes parallel to +Z through **(−43, −17.75, 57)** and **(43, −17.75, 57)**.
  The Z coordinate identifies a point on each axis, not a connector mating face.
  Axis spacing is **86.00 mm**, and the X interval between the two cylindrical
  envelopes is **63.80 mm**. That interval is not free space for an enclosure.
- Original cylinder surfaces are `#14257`, `#14274`, `#14409`, `#14426`;
  they belong to original source shell `#15060`. Their advanced-face IDs and
  placements are joined in `glp-x5/measurement-receipt.json`. Imported faces
  243/244 and 253/254 form the two cylindrical pairs.
- The selected planar lands are at **Z=58.00**, with Y limits approximately
  **−35.00 to −0.50**: **34.50 mm** of local land height. Their curved side
  boundaries mean this is not a rectangular panel width/height specification.
  The modeled large cylindrical surfaces span **Z=55.50 to 58.00**, an axial
  span of **2.50 mm**. These planes do not define socket engagement or recess.
- Adjacent small cylindrical features have radius **1.60** (Ø3.20 shank),
  with X and Y offsets **9.90 mm** from the large-feature axes. Opposing small
  axes have diagonal separation **28.00143 mm**. These shanks are not the larger
  visible front countersink openings; no fastener or connector model is assigned.
- An opposite-side central cylindrical feature has radius **11.90** (Ø23.80),
  axis through **(6.75, −17.75, −77)** parallel to −Z. Imported faces 187/188
  span **Z=−76.50 to −74.50**. Its function is not established by geometry.

These features are **not identified as XLR or powerCON interfaces**. The bare
shell has mounting lands and simplified/covering surfaces; it does not supply
identifiable five-pin mating contacts, latch geometry, connector seating plane,
or installed socket protrusion. A matching hole diameter or diagonal screw
pattern alone cannot establish connector identity. The selective view omits
covering/opposite surfaces to expose measured features; it is not the complete
exterior or a clearance model.

Error limits: STEP `#269274` declares connectivity uncertainty **0.05869810163750
mm**. This is neither a manufacturing tolerance nor a guaranteed coordinate error
bound. Source parameters are retained at full precision; reported nominal dimensions
are rounded to 0.01 mm. Comparison assertions use 0.000001 mm numeric tolerance.
Render deflection is 0.4 mm for whole-fixture views and 0.05 mm for selected faces;
images supply visual identification only. Physical production tolerances, socket
identity and mating-depth error bounds remain unknown.

## Saved visual evidence

- [Whole source, looking from +X, Y up](glp-x5/plus-x.png).
- [Whole source, looking from +Z, Y up](glp-x5/plus-z.png).
- [Base from +Z](glp-x5/base-plus-z.png) and [base from −Z](glp-x5/base-minus-z.png).
- [Selected paired lands and cylindrical features](glp-x5/selected-paired-panels.png):
  looking from +Z, X right and Y up. Cyan is only imported faces 215/216;
  cylindrical faces are included, other shell surfaces deliberately omitted.

Reverse X/Z, both base X sides and underside were also rendered and inspected;
only the views relevant to the receipt are retained. Raster positions were not
used to calculate any dimension.

## CHAUVET: concrete format barrier

Source archive SHA-256:
`5032128181480201b3815f67699c6e264825188e3399b2341cf1f2d4c665051f`.
Member `OVATION E-910FC_3D.dwg`, 111,808,283 bytes, AC1032,
SHA-256 `bf0f9b1d80d933d96a6662b505ed2f9f5476c6970f4a5730307403f5f1ebc5a7`.
LibreDWG 0.14 returned **0**, producing a 6,574,296-byte DXF. ezdxf found **82
3DSOLID entities, all 82 with zero SAT lines and zero SAB bytes**; ACDSDATA has
zero entities. The header declares INSUNITS=4 (mm), but no physical scale could
be validated without preserved geometry. Diagnostics include `bit_read_BL:
unexpected 2-bit code: '11'` and `AcDs blob01 segment yet unhandled`.
See [numeric receipt](chauvet-e910fc/receipt.json) and
[converter log](chauvet-e910fc/conversion.log). Temporary extracted source and
converted files were removed; pinned cache originals were untouched.

This repeats the unsupported-body problem already present in the ETC conversions.
The pass stops here; conversion exit zero is not geometry preservation.

## Fit conclusion and next asset

**No comparative compactDMX overlay was performed, and no fixture fit or universal
fit is claimed.** The source supplies useful local mounting-feature dimensions,
but a fixture socket mating datum and recess/protrusion remain unknown. Aligning
the sidecar to these cylindrical axes would silently assume the port assignment,
connector seating and installed shell configuration. A bounding-box overlay would
not close those gaps.

The smallest useful next manufacturer asset is an X5 installed base/rear I/O
assembly STEP (or a dimensioned connector-interface drawing) identifying exact
socket part numbers, center coordinates, seating/mating planes and shell recesses
for the applicable revision. For CHAUVET/ETC, a manufacturer neutral STEP/IGES
export containing connector-panel surfaces would bypass the demonstrated missing
ACIS/SAB-body conversion barrier. No new asset or fixture was qualified here.

## Reproduction (existing tools only)

Run from repository root. The analysis writes only beneath `measurements/`;
original cache files are hash checked and read only. No network is needed.

```sh
NOVA_FIT_RENDER_MESH=1 ~/.local/bin/freecadcmd hardware/fixture-fit/measurements/analyze_glp.py
python3 hardware/fixture-fit/measurements/extract_glp_receipt.py
blender -b -t 4 --python hardware/fixture-fit/measurements/render_glp.py
blender -b -t 4 --python hardware/fixture-fit/measurements/render_glp_panels.py
python3 hardware/fixture-fit/measurements/check_chauvet.py
```

`view-mesh.json` is a transient 86 MB render input, intentionally removed after
rendering. `analyze_glp.py` without `NOVA_FIT_RENDER_MESH=1` regenerates numeric
census files and the small editable selected-face mesh without that large input.
The retained receipt contains the selected measurements; full `faces.json` and
`circles.json` are transient census outputs, reproducible with the script.
