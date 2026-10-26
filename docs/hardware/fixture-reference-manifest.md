# Compact fixture fit reference assets

Research snapshot retrieved 2026-10-22 (UTC). These references are suitable for early enclosure and connector-clearance studies. They do not establish a universal fit or production fit. The accepted set now contains **4 fixture models from 3 manufacturers**: ETC ColorSource Spot V 19° and Fresnel V, CHAUVET Ovation E-910FC, and GLP impression X5. The additional bounded pass stopped after GLP qualified; Elation and Cameo were not investigated.

## Accepted source matrix

| Manufacturer / exact model | Qualifying asset actually retrieved | Source page and direct asset | Retrieval and file evidence | Inspection and fit-relevant evidence |
|---|---|---|---|---|
| Electronic Theatre Controls (ETC), ColorSource Spot V, 19° fixed lens | Manufacturer CAD bundle; member `Colorsource Spot V-19.dwg` (DWG 2013/AC1027, 1,394,596 bytes). The file contains a 512×306 PNG CAD thumbnail showing the fixture in 3D. | [Spot V documentation / drawings](https://www.etcconnect.com/products/entertainment-fixtures/colorsource-spot-v/documentation.aspx); [3D CAD ZIP](https://cdn.etcconnect.com/ColorSource%20V_3D%20CAD.zip) | Retrieved 2026-10-22T17:31Z; HTTP 200; `application/octet-stream`; ZIP signature `PK\x03\x04`; archive 13,497,647 bytes; SHA-256 `e8bcf36cf7ea80b4726969d9288b3a66a883be3c1f0501b5521004f3770a9b95`; cached at [`source-cache/etc-colorsource-v-3d-cad.zip`](../../hardware/fixture-fit/source-cache/etc-colorsource-v-3d-cad.zip). | Archive listing and DWG signature/embedded 3D thumbnail inspected; DWG geometry itself was not rendered/measured. Official [installation guide](https://www.etcconnect.com/WorkArea/DownloadAsset.aspx?id=10737516501), page 6, was rendered and inspected. It shows the rear panel and documents two five-pin XLR DMX connectors plus two powerCON TRUE1 connectors for input/thru. The drawing shows their general arrangement; no connector pitch, recess depth, or opening dimensions are supplied there. The archive's internal DWG date is 2017-07-13 while the current ETC page lists the CAD bundle as April 2026. Filename and current package are exact to Spot V, but that age mismatch lowers model-identity confidence until a designer checks the drawing in CAD. Do not substitute the legacy non-V ColorSource Spot. |
| Electronic Theatre Controls (ETC), ColorSource Fresnel V (standard, not V MAX) | Manufacturer CAD bundle; member `ColorSource fresnel V.dwg` (DWG 2018/AC1032, 402,086 bytes). | [Fresnel V documentation / drawings](https://www.etcconnect.com/Products/Entertainment-Fixtures/ColorSource-Fresnel-V/Documentation.aspx); [3D CAD ZIP](https://cdn.etcconnect.com/ColorSource%20V_3D%20CAD.zip) | Retrieved 2026-10-22T17:31Z; HTTP 200; `application/octet-stream`; ZIP signature `PK\x03\x04`; archive 13,497,647 bytes; SHA-256 `e8bcf36cf7ea80b4726969d9288b3a66a883be3c1f0501b5521004f3770a9b95`; cached at [`source-cache/etc-colorsource-v-3d-cad.zip`](../../hardware/fixture-fit/source-cache/etc-colorsource-v-3d-cad.zip). | Exact current model name appears as an archive member (member date 2026-04-01). DWG header inspected; its embedded thumbnail could not be decoded by available local tools, so no geometry was measured. Official [installation guide](https://www.etcconnect.com/WorkArea/DownloadAsset.aspx?id=10737516500), page 3, was inspected; it shows a rendered fixture view and documents two five-pin XLR DMX connectors and two powerCON TRUE1 power connectors for input/thru. The rear connector arrangement is illustrated, but no connector pitch, recess depth, or opening dimensions are given. The guide explicitly distinguishes Fresnel V from Fresnel V MAX; this reference is the standard Fresnel V. |
| CHAUVET Professional, Ovation E-910FC (non-IP) | Manufacturer CAD ZIP; member `OVATION E-910FC_3D.dwg` (DWG 2018/2019/2020, AC1032, 111,808,283 bytes). Its embedded 180×180 PNG is a 3D rendered fixture view. | [Ovation E-910FC product page](https://chauvetprofessional.com/product/ovation-e-910fc/); [3D CAD ZIP](https://www.chauvetprofessional.com/wp-content/uploads/2015/01/OVATION-E-910FC_3D_CAD.zip) | Retrieved 2026-10-22T17:31Z; HTTP 200; `application/zip`; ZIP signature `PK\x03\x04`; archive 94,839,001 bytes; SHA-256 `5032128181480201b3815f67699c6e264825188e3399b2341cf1f2d4c665051f`; cached at [`source-cache/chauvet-ovation-e-910fc-3d-cad.zip`](../../hardware/fixture-fit/source-cache/chauvet-ovation-e-910fc-3d-cad.zip). | CAD member signature and embedded 3D view were inspected. A bounded LibreDWG 0.14 conversion returned zero, but all 82 converted `3DSOLID` entities have empty SAT/SAB bodies and no ACDSDATA entities. No preserved 3D geometry was available to measure; see the [metrology receipt](../../hardware/fixture-fit/measurements/README.md). The [manufacturer user manual](https://www.chauvetprofessional.com/wp-content/uploads/2015/01/Ovation_E-910FC_UM_Rev18.pdf), page 4, provides orthographic rear/front and side illustrations with connector labels; page 20 supplies overall fixture dimensions: 495 × 285 × 487 mm (fixture only). It identifies 3- and 5-pin XLR DMX in/out and Seetronic Powerkon IP65 power in/out. The rear-panel ports are grouped near the control display and fuse holder. No connector pitch, recess depth, or opening dimensions are provided. The IP65 cable connector is listed separately from the fixture inlet; do not assume connector maker compatibility from that alone. |
| German Light Products (GLP), impression X5 (standard X5) | Manufacturer CAD ZIP; member `GLP impression X5 3D Shell Rev20211111-1.stp` (STEP, 19,814,428 bytes). The original STEP text was inspected and contains B-rep surface geometry (4,519 `ADVANCED_FACE` entities); its unit declarations specify millimeters. | [GLP impression X5 product page and downloads](https://glp.de/en/products/entertainment-lighting/moving-lights/impression-x5-en); [CAD ZIP](https://glp.de/files/products/impression-x5-product-data/GLP_impression_X5_CAD_Rev20240202-1.zip) | Retrieved 2026-10-22T17:34:36Z; HTTP 200; `application/zip`; ZIP signature `PK\x03\x04`; archive 18,464,564 bytes; SHA-256 `94d87167d1a155785ec6de431817982aecd296ba1767d4882c8d617ef2e61da5`; cached at [`source-cache/glp-impression-x5-cad.zip`](../../hardware/fixture-fit/source-cache/glp-impression-x5-cad.zip). Extracted member signature `ISO-10303-21;`; SHA-256 `25fed40decfcf0a511e4f6f78657a2386962d98e7a1f58fcea01bb32823af8e3`. | The exact model and CAD download are linked on GLP's official page. The fetcher inspected STEP geometry and millimeter declarations as text. Parent subsequently imported the file in FreeCAD 1.1.3 and viewed a tessellated rendering using existing Blender 4.5.13 tools: the file contains 4,519 faces and zero solids. A bounded metrology pass subsequently measured two analytic Ø22.20 mm base mounting features on parallel Z axes 86.00 mm apart, and local lands at source Z=58.00 mm. These are mounting-feature measurements, not identified XLR/powerCON mating interfaces. No clearance overlay was performed. The source is one surface part with baked coordinates and no component assembly placement hierarchy; the new orthographic render is spatially coherent. See the [numeric/source-entity receipt and images](../../hardware/fixture-fit/measurements/README.md). GLP's product technical data states overall height 402–434 mm, width across yoke 415 mm, and depth 290 mm; it lists Neutrik powerCON TRUE1 power in/out and Neutrik five-pin XLR DMX in/out. The page does not give connector panel pitch, recess depth, or opening dimensions, and the overall dimensions do not establish panel coordinates. The [manufacturer manual](https://glp.de/files/products/impression-x5-product-data/GLP_impression_X5_User_Manual_EN_Rev_20240207-01.pdf) is also cached at [`source-cache/glp-impression-x5-user-manual.pdf`](../../hardware/fixture-fit/source-cache/glp-impression-x5-user-manual.pdf); its SHA-256 is `bc7a3cbf9950e89910e149fe87206b76ae20a920208f24f840bb1c764f0f3d66`. |

## Unqualified candidates and gaps

| Candidate | What the official source exposed | Why it does not count |
|---|---|---|
| Martin MAC Aura PXL | [Manufacturer product page](https://www.martin.com/en-US/products/mac-aura-pxl) lists 3DS and 3D DWG files. | Direct product-page access returned HTTP 403 during retrieval; no file was downloaded or inspected. Search-index listing alone does not qualify. |
| Robe Robin T1 Profile | [Robe product page](https://www.robe.cz/t1-profile) links to its GDTF materials; Robe's manufacturer page on [GDTF Share](https://gdtf-share.com/userPage.php?name=Robe+Lighting+s.r.o.&page=fixtures) lists the T1 Profile and T1 Profile FS. The public metadata endpoint returned a latest revision record naming 5-pin DMX and power inputs, but no model binary. | The revision download redirected to login; the public download endpoint returned HTTP 401 (authentication required). Metadata and product photos are not an actual retrieved 3D asset. No Robe model is counted. |

The bounded continuation met the multi-manufacturer target with GLP's retrieved STEP model, bringing the set to four fixtures across three makers. No Elation or Cameo candidates were needed for that acceptance threshold.

## Scope and confidence

- These files are references for layout exploration, not confirmed housing, mount, or connector compatibility. No prototype was tested against any fixture.
- Connector type and broad panel placement are documented above. **No identified rear connector mating pitch or recess depth has been verified for any accepted model.** GLP has a measured 86.00 mm spacing between two nominal Ø22.20 mm cylindrical mounting features; port assignment and socket mating planes remain unverified. Do not invent those dimensions from screenshots or marketing images.
- Units and scale are explicit for the E-910FC overall dimensions (millimeters in the manual), GLP's overall dimensions (millimeters on the technical data page), and the GLP STEP model (millimeter units declared in the file). The ETC DWGs' units/scale were not verified in a CAD application. GLP local mounting-feature geometry was measured from analytic CAD surfaces, with original source IDs and units retained in the [metrology receipt](../../hardware/fixture-fit/measurements/README.md). The ordinary GLP B-rep bounds are approximately 289.96 × 561.71 × 452.37 mm, while the 0.4 mm tessellation spans about 289.91 × 482.33 × 415.03 mm. The ordinary bounds are loose on B-spline faces; their mismatch is not evidence of an exploded assembly. The original coordinates render coherently without repositioning. Neither bounding box resolves socket mating depth or establishes installed fit.
- ETC Spot V identity has lower confidence due to the archive member's 2017 internal timestamp despite its presence in the current Spot V documentation bundle. Resolve this in CAD before using its shape as a fit constraint.
- Third-party source files are excluded from version control. The ignored cache is reproducible with [`fetch_sources.py`](../../hardware/fixture-fit/fetch_sources.py); checksums are pinned in that script.

## Retrieval and verification

Run from the repository root:

```sh
python3 hardware/fixture-fit/fetch_sources.py
unzip -l hardware/fixture-fit/source-cache/etc-colorsource-v-3d-cad.zip
unzip -l hardware/fixture-fit/source-cache/chauvet-ovation-e-910fc-3d-cad.zip
unzip -l hardware/fixture-fit/source-cache/glp-impression-x5-cad.zip
file hardware/fixture-fit/source-cache/*.pdf
sha256sum hardware/fixture-fit/source-cache/*
```

Inspection utilities used in this research: `curl`, `file`, `unzip`, `sha256sum`, `pdftotext`, `pdfinfo`, and `pdftoppm`; no software was installed. Source-cache files are ignored by Git to avoid committing large third-party binaries.

Parent follow-up after explicit tool approval: LibreDWG 0.14 was built locally
and converted the ETC Spot V19 and Fresnel V DWGs to DXF. Both conversions returned
zero and parsed in ezdxf, but their logs contain unsupported object/surface data;
Spot V also reports a missing SAB-body error. Spot V yielded one `3DSOLID` entity
and Fresnel V two. Converted headers declare `$INSUNITS=1` (inches), which is a
file declaration, not independently verified physical scale. These conversions
do not establish complete, accurately preserved geometry or connector coordinates.
Converted files and logs remain in the ignored cache; original pinned archives
are retained as the source of truth.

Parent also extracted and rendered the GLP bundle member
`GLP impression X5 PDF Rev20230112.pdf` (SHA-256
`f1ed52225cc1f433d3fc04dc08445d437709bc009c9be956643a46361341164b`).
Its orthographic views include base connectors, mounting feet and explicit
482/457 mm vertical and 418 mm width dimensions. The current official product
page, retrieved again on 2026-10-22, lists height 402–434 mm and yoke width 415 mm.
The drawing's mounting configuration and revision must be reconciled with those
technical data before treating the views as the installed fit reference. The
sheet explicitly says “DO NOT SCALE”; no connector pitch was inferred from its
raster rendering. This inspection does not close the connector-coordinate gap.


## Bounded source-geometry metrology follow-up (2026-10-22)

The [measurement package](../../hardware/fixture-fit/measurements/README.md) retains
editable FreeCAD/STEP-inspection and bounded DWG-conversion scripts, source revisions
and hashes, numeric receipts, diagnostics and source-coordinate renders. GLP's
paired mounting features have centers on source Z axes through
`(-43, -17.75, 57)` and `(43, -17.75, 57)` mm, radius 11.10 mm, and local
modeled axial span Z=55.50–58.00 mm. The selected planar lands span approximately
Y=-35.00 to -0.50 mm. A separate opposite-side cylindrical feature is Ø23.80 mm.
None is assigned a DMX/power function from size alone. STEP connectivity uncertainty
is 0.0586981 mm; it is not a manufacturing tolerance.

The GLP STEP has one product, 62 source open shells, and no component assembly
transform hierarchy. FreeCAD returns 215 shells, six closed, but zero solids.
This topology does not prove the shape is exploded or identify installed connector
parts. The source lacks an established socket mating datum, recess/protrusion and
latch envelope, so no compactDMX fit or comparative clearance overlay is claimed.
A manufacturer installed I/O assembly STEP or dimensioned interface drawing with
exact socket identities and mating planes is the next useful asset.

The CHAUVET conversion reproduced the unsupported-body barrier seen in prior ETC
conversions: 82 solid records, zero usable body payloads. That ends this bounded
pass. No fixture was newly qualified and no mechanical design was changed.
