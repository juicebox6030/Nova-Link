# Exact JS102011SAQN candidate — pending footprint qualification

Parent retrieved the official Littelfuse product page on 2026-10-22:
<https://www.littelfuse.com/products/switches/slide-switches/js/js102011saqn>.
It lists Active, maintained On-None-On, side actuation, surface-mount terminals,
0.3 A maximum and 6 V DC maximum. See `js-parent-status.json` for the DOM receipt.
This is an alternative candidate; the active circuit/BOM still uses provisional PCM12.

The page links the official JS-series datasheet:
<https://www.littelfuse.com/assetdocs/littelfuse-ck-slide-js-series-datasheet?assetguid=aba42b08-0d2c-423b-813d-a2faa5a3bb14>.
Retrieved by same-origin browser fetch (HTTP200, application/pdf), 1107422 bytes,
SHA256 `0f35cdf47a1f93da71bb7235581f3c77915516488be930d7a3ea4f4942ff0f3b`.
Ignored local source `.tools/references/js-official.pdf`; text extraction and
page4 render are alongside it. Revision VL01/14/26; parent visually inspected page4.

Page4 explicitly identifies JS102011SAQN as right-angle SMT SPDT. A historical
description of this exact SA variant as THT was incorrect. Page1 distinguishes
SA gullwing from A/C through-hole variants. The exact product's 0.3 A at6 V
rating exceeds the current approximately50.84 mA at6 V termination corner.
Family specifications include 5000 electrical cycles and -40 to85 C operation.

Page4 gives three 1.2x2.5 mm recommended lands at2.5 mm pitch, two diameter0.9 mm
locator holes spaced6.8 mm, and a4.0 mm dimension from the hole row to the far
land edge. Body views show8.5/9.0 mm width references,3.6 mm depth,3.5 mm height
and2.0 mm actuator travel. These callouts require reconciliation between views;
they are not yet a verified coordinate table. In particular, prove horizontal
registration of the hole pair to the terminal row and body-to-locator datums.
Do not infer unlabelled symmetry or treat an enlarged drawing as a dimension.

Qualification must establish complete lands, locator/body/actuator registration,
terminal numbering, actual isolated-side placement, nearby hole/reserve clearance,
height and enclosure access. Larger body/actuation may require repacking.
No source-complete footprint, accepted replacement, assembly fit or release claim
follows from this parent source retrieval.
