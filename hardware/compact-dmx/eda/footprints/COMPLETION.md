Current update: [five RF substitutions and remaining switch datum](REPLACEMENT-PASS.md) supersedes the earlier six-provisional counts below. Earlier sourcing history retained.

# Footprint assignment follow-up — 2026-10-22

All37 physical MCU/RF/DMX components now have explicit footprint assignments.31 assignments are supported by manufacturer dimensions or exact TI reference lands. Five Johanson tuning components use a clearly provisional TI0402 reference land; the PCM12 switch remains parent-owned/pending. This is not a claim that every selected legacy MPN is currently in production, nor a PCB release. Exact values/MPNs and source status are in `assignments.json` and actual KiCad exports.

## IPC extraction

The local SWRC354 archive contains native binary `CC1352EM-IPC.brd`, expanded electrical netlists, Gerbers and `docs/Pick n Place.txt`. It does **not** contain an AllegroASCII `.alg` file. The available17MBASCII is the separate LaunchPadR1RevB export; its package/padstack records were inspected, including crystal pin positions and padstack dimensions. It was not mislabelled as the IPC board or substituted for IPC copper. No native Allegro installation/conversion service was added.

`extract_ti_lands.py` uses SWRC354's exact GerberRS274X numeric geometry: `%FSLAX25Y25*MOMM*%`, outline aperture macros, flash coordinates and PnP location/rotation. It extracts copper, paste and solder-mask layers separately. Position advances on all coordinate commands, not only flashes. All selected copper/paste polygons agree; mask openings are preserved as separate vector apertures rather than assuming a generic mask margin. There is no raster scaling or guessed rounded rectangle. SourceSHA256 and original aperture/flash coordinates are recorded in `ti-vector-lands.json`.

TR1 is located at127.135,117.960mm and rotated180° in the source. The ten lands are mapped to the current Johanson0900PC15A0036001E Rev2.0p3 **top-view** pins:1/2/3/4 across the upper row right-to-left,5 left middle,6/7/8/9 lower row left-to-right,10 right middle. After unrotation and KiCadY-axis conversion, upper/lower centres are y±0.78mm and x±0.75/±0.25mm. Their bounding dimensions are0.25×0.80mm. Middle lands are centredx±1.155mm and have0.80×0.35mm bounds. Asymmetric/rounded polygon contours are retained exactly. Eight0.5mm-pitch terminal positions and separate grounded pads are not collapsed into a body rectangle. The source part was namedIPC1352_EXPERIMENTAL; applying its lands to the later production0900PC15A0036001E is an explicit reference-derived prototype choice supported by the same terminal topology/package, with manufacturer/process/RF approval still required.

## Support and passive lands

| Footprint | Source and numeric dimensions | Assigned parts |
|---|---|---|
| TI_CAPC1005_Vector | SWRC354 C131, centres±0.462; copper bounds0.524×0.500 | MCU C103–C111; DMX C1/C3; **provisional only** C115/C116/L102–L104 |
| TI_CAPC1608_Vector | SWRC354 C331, centres±0.700;0.750×0.900 | C101/C102 |
| TI_CAPC0603_Vector | SWRC354 C41, centres±0.280;0.350×0.400 | C112/C113 |
| TI_BLM18_Vector | SWRC354 FL1, centres±0.700;0.750×0.900 | FL101 BLM18HE152SN1D |
| TI_MLZ2012_Vector | SWRC354 L331, centres±0.900;1.150×1.450 | L101 MLZ2012N6R8LT000 |
| Epson_FC135_Manufacturer | Epson FC135_E_Ver2.0p4, centres±1.25;1.0×1.8 | Y101 FC-13532.7680KA-AG0 |
| NDK_NX2016SA_Manufacturer | Current NDK dimension drawing, x±0.675/y±0.525;0.85×0.75 | Y102 NX2016SA48MHzEXS00A-CS05517 |
| Vishay_CRCW0402 | Vishay20035 2026-04-14 reflow table:gap0.45;0.6×0.6lands | R1–R3 CRCW040210K0FKED; R4 CRCW04021K00FKED |
| Murata_GRM21_Reflow | Exact GRM21BR71A106KE51-01 specification NoticeTable2; gap1.2; chosen0.7×1.3 within0.6..0.8×1.2..1.4 range | C2/C4 GRM21BR71A106KE51L |

All dimensions aremm. Gerber-derived shapes use full polygons, so bounding dimensions do not replace rounded contours. Two-terminal nonpolar pad numbering is explicitly local1left/2right. NDK crystal1/3 connect the resonator,2/4 the grounded cover, matching the schematic and current manufacturer top view. Epson's shaded underside must remain free of circuit patterns; this requirement still needs PCB-level enforcement. Family land drawings do not approve the legacy/custom crystal electrical suffix, load capacitance or oscillator startup margin. The original TI MPNs remain unchanged; no clock electrical substitution was made.

DMX C1/C3 now use the same source-backed100nF25VX7R MurataGRM155R71E104KE14D as TI MCU decouplers (voltage rating exceeds the former16V requirement). C2/C4 retain10µF10VX7R through the exactGRM21BR71A106KE51L selection. Its current manufacturer reference sheet explicitly includes package codeL. Effective capacitance at operating bias/temperature and assembled converter behavior remain unverified; assigning a land does not close those electrical tests.

Courtyards are design-added0.25mm perimeter margins around maximum of nominal body/pad extents; they are not manufacturer assembly qualification or spacing ratings. Existing MCU/isolator/antenna lands, all six isolated antennaNC lands, and isolation-domain nets are preserved. No IPC ground vias, RF feed routes, thermal-via array or whole-PCB placement is fabricated here.

## Six provisional assignments and bounded retrieval

C115=`QSCF500Q1R0B1GV001T`, C116=`QSCF500Q8R2B1GV001T`, L102=`LRC0402CS2N7GV001T`, L103=`LRC0402CS5N1GV001T`, L104=`LRC0402CJ12NGV001T` remain the actual antenna manufacturer's starting-value MPNs. They share the existing TI0402 reference land only as a provisional tuning footprint. The source establishes the parts/values, not approval of that land for all five parts. The manufacturer's pad-layout page was readable but its dimension image could not be retrieved; the second route, manufacturer catalog4860, returned403. Specific LRC/QSCF queries did not produce dimensioned part lands. Stop here rather than invent an exact pad approval: supplier part-specific footprint/process confirmation or a public dimensioned drawing is still required. This is a sourcing gate, not proof that the proposed pads cannot work. Retuning can require different values/topology and part envelopes; no RF-performance claim is made.

PCM12SMTR remains an explicitly provisional prototype. The initial primary lookup did not resolve its lifecycle. Parent subsequently read the live official page listing **Active** and recovered/visually inspected the official2025 PDF. The provisional footprint's mounting-row inner gap is1.41mm versus the manufacturer's1.13mm; correction and complete datum verification remain open. See [parent source and dimension receipt](pcm-parent-verification.md). No unsupported replacement was selected.

## Checks and reproducibility

Run from repository root:

```
python3 hardware/compact-dmx/eda/footprints/generate.py
python3 hardware/compact-dmx/eda/generate_dmx_sheet.py
python3 hardware/compact-dmx/eda/verify_kicad.py
python3 hardware/compact-dmx/eda/mcu-radio/generate.py
python3 hardware/compact-dmx/eda/mcu-radio/verify.py
flatpak run --command=python3 org.kicad.KiCad hardware/compact-dmx/eda/footprints/verify.py
```

The first command needs the existing ignored primary-source cache to re-extract TI geometry; the committed `ti-vector-lands.json` and `generate_support.py` also preserve the extracted vector source. The exact source files/hashes are listed, not presumed available to a recipient. Do not treat this library as a released PCB.

RealKiCad10.0.7 parses15footprints and verifies14dimensioned patterns/109numbered pads. Every one of37physical actual-export components has matching footprint pad numbers and selected MPN/value. DMX remains14components/15nets/zeroERC; MCU remains26components/57nets/zeroERC. The current power/DMX endpoint contract is independently exported and checked. Power has not changed in this pass; before/after hashes are in the new receipt. Package-wide validation is left to parent after independent power work settles.
