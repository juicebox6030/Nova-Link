# Buffer fit candidate — isolated proposal, 2026-10-23

**Preferred engineering candidate: Eaton HV1625-2R7256-R, 25 F**, with a local PCB aperture and lowered horizontal cradle. Conditional aged runtime is **16.343 s**, versus **9.730 s** for the existing 15 F. This is useful margin over the owner's 10 s minimum and the approximately12 s engineering screen, not measured runtime or lifetime qualification. The case remains98×34×24. No baseline or other candidate was edited. Parent must choose/integrate after Sol's concurrent startup correction.

## Sources and bounded comparison

Three families only: Eaton HV, KYOCERA AVX SCC, CDA CXHP. Actual primary PDFs and extracted text are in `sources/`; exact URLs, document identifiers and SHA256 are in `sources.json`. Eaton's primary asset was recovered through the existing browser after CLI failures. AVX and CDA were retrieved directly. Manufacturer dimension pages were rendered and inspected, with no pixel-derived dimensions.

| Exact MPN | Maximum body Ø × L mm | Initial ESR used | Aged C / ESR screen | Runtime s | Disposition |
|---|---:|---:|---:|---:|---|
| HV1325-2R7156-R |13.5×28.4|30mΩ|9.45F /60mΩ|9.730|Existing, fails conditional10s |
| **HV1625-2R7256-R** |**16.5×28.4**|27mΩ|15.75F /54mΩ|**16.343**|Preferred with explicit cutout |
| SCCT30B186SRB |13.5×32|60mΩ DC5s|11.34F /120mΩ|10.764|Little margin; body consumes3.6mm more lead reserve |
| SCCT35B226SRB |13.5×37|58mΩ DC5s|13.86F /116mΩ|13.230|Body alone exceeds35mm longitudinal reserve; not selected |
| CXHP2R7206R-TW |13.5×26.5|60mΩ DC|11.2F /120mΩ|10.631|Fits old body envelope, insufficient useful margin |

Sources: Eaton Technical Data4376 effectiveJan2020 pp2–3; AVX TDS-SC-0001 Rev11 pp2–4; CDA2024 catalog pp4,10–11. For AVX use the slower DC5s resistance, not the attractive1kHz figure. AVX maxima include +1mm diameter/+2mm length; CDA includes +1mm diameter/+1.5mm length. These are nominal starting-value substitutions only; no supplier procurement/lifecycle approval was obtained.

## Reproducible energy/ESR screen

`screen.py` independently solves constant-power discharge. With output load1.11W and electronics efficiencyη, cell terminal power is P=1.11/η. At internal voltage V and ESR R, terminal voltage is `(V+sqrt(V²−4RP))/2`; current is P/Vterminal. Stop when **loaded** terminal voltage reaches1.705917V, so internal end voltage is floor+RP/floor. Integrate `dt=C*Vterminal/P*dV` from this end to2.448V. ESR loss is explicit, not deducted twice through an assumed combined efficiency.

Initial tolerance and aging remain separate:25×0.9×0.7=15.75F. Eaton's endurance/cycle limit permits200% initial maximum ESR;54mΩ is the screen. These test limits at stated conditions are **not a field-age or cold guarantee**. Simpson integration agrees with an independent100µs forward-time integration within0.001s;10k vs20k integration panels agree within1e−8s. Existing15F result reproduces9.729548s.

At cutoff the25F screen draws0.813A and dissipates35.7mW in ESR. Manufacturer20°C references list3.4A continuous for15°C rise in open air and20A one-second pulse; neither qualifies the enclosed fixture duty cycle. At70% efficiency and twice aged ESR (108mΩ), runtime13.018s; at70% and162mΩ,11.893s. These are sensitivity allocations, **not sourced cold multipliers**. Cold capacitance can fall as well: an additional0.7 capacitance factor would reduce the latter to8.325s. Eaton does not provide a guaranteed combined aged/cold bound here. AVX typical temperature plots and CDA's temperature-change limits likewise do not establish a simultaneous lifetime/temperature guarantee for the preferred cell.

Retain2.6V nominal charging and all existing cutoff/rearm thresholds; no resistor changes proposed. Raising voltage is not the selected fix: even ignoring ESR, the aged15F needs2.5365V usable starting voltage for12s, above the existing2.448V reserved start. Removing the100mV historical reserve would require validating regulation/arming/load behavior; it is not free energy margin. At2.7V maximum rating there is no justification to consume the existing tolerance/overshoot allowance.

## Exact packaging proposal

Editable `geometry.py`, `buffer25-proposal.FCStd` and analytic `buffer25-proposal.step` are a **separate** geometry proposal. They copy frozen GCT shapes read-only; no baseline writer is imported. `fit-section.svg/pdf` are dimensioned equal-scale views.

- Existing board mainx4..94,y23..51,z10..11 and USB tongue remain. **New aperture** x26.5..55.9,y25.5..35.8,29.4×10.3 through the board; square corners are conceptual and require routed internal radius/strength/DFM design. It stays right of isolation boundaryx26 and below the RF allocationx59.
- Cell maximum body moves fromx26..54.4,cy30.25,cz18.75 to **x27..55.4,cy30.65,cz18.1**. Maximum body bottom9.85/top26.35 and y22.4..38.9. It crosses the PCB plane, so an unchanged board is impossible. High-body projection extends outside the oldy23.5..37 reserve; this is explicitly a new3D reserve, not silent reuse of its area.
- Two proposed PA12 saddles x28..31 and50..53,y25.8..35.5,z7..12.5 are cut to radius8.60. They contact the case floor atz7 and clear the aperture. Nominal radial gap0.35 is for a **not yet modeled/specified compliant liner**. Cell-position0.15 plus saddle-process0.10 leaves0.10 rigid radial margin. Positive retention, adhesive/mounting method, vent relief, load/creep and compression must be designed/qualified; no retention solution is claimed from the saddle alone.
- Supplier leads change fromØ0.60 to **Ø0.80±0.02**, pitch **7.5±0.5** (previous5mm). Existing C23 lands atx27.5 are removed from this proposal's check and must be replaced, not reused. Proposed **lead-form reservation** x55.4..58.9,y26..35.3 with potential landing nearx58 and nominaly26.9/34.4, stays before RFx59. This is an allocation only: allowable bend radius/seal standoff, lead strain relief, hole/annulus/pitch accommodation and solder volume are unresolved. No exact formed-lead CAD or released footprint is fabricated.
- GCT support/stop/port, NOR, screw bosses and external98×34×24 remain untouched. No cable-fit, PCB-strength, EMC or RF-clearance qualification follows from this geometry.

Nominal wall/lid clearance0.40/0.65mm. Inflating the maximum cell by0.15mm radially and each end gives wall0.25/lid0.50; a further0.10mm inward case/lid process allowance leaves **0.15/0.40mm**. With aperture edges inset0.10 and PCB top11.10, the inflated cell has **0.231mm** actual BRep PCB clearance. These are allocated process limits requiring manufacturer agreement, not measured assembly capability.

The independent geometry screen finds16 valid closed solids,15 cell-to-other-solid comparisons, and173 component-courtyard extrusions with **zero intersections**, plus cradle checks. Four mounting footprints have empty courtyard caches; physical bosses/holes are instead in the frozen solids. Top heights use conservative2.23mm, except nearbyU24/U26 at source DBV maximum1.45mm andR15 at deliberately loose1.45mm (Vishay actual0402 maximum0.40mm); bottom heights1.45mm. The initial uniform2.23mm screening flagged these three, then source-height refinement cleared them. This is not supplier-exact assembled component CAD. The original37 positions, USB, NOR and power placements are not edited or re-routed. **No new KiCad DRC is claimed**: this is an aperture proposal, not a modified electrical board.

## Charge, voltage, protection and release gates

25mA remains: nominal empty-to2.6V takes**43.33min before CV tail**, versus26min. Using32.5F,2.652V and22.42mA gives**64.07min before tail**, conditional on the existing charger assumptions; no recharge-interval requirement is invented. Leakage45µA is nominal after72h at20°C, not a worst-case aged/cold bound. NormalUSB still requires5V advertisement≥1.5A; no changes to qualification or current limiting.

Preferred cell rating2.7V,−40..+65°C; extension to85°C requires linear derating to2.3V.2.6V nominal is not authorized across that entire extended range.3.0V surge is not a permissible charge target. Do not reverse or overvoltage. Stored energy grows to84.5J nominal at2.6V, up to118.46J at32.5F/2.7V.100A short-circuit reference is a safety number, not operating current or protection guarantee.

Existing absence of independent cell OVP/fuse remains a **hardware protection-policy gate**: a charger feedback fault can overcharge below input-current-trip level; a cell-side short bypasses upstream protection. Larger capacitance increases fault energy. This package does not quietly add or qualify protection. Before release: supplier lead/temperature/capacitance/ESR confirmation; cell OVP/short policy; charger low-voltage behavior and leakage; empty startup/hot reattach afterU40 correction; measured worst-activity runtime at temperature/age; cradle/retainer/vent/assembly tolerance; new C23 lands and routing/PCB cutout strength; full RF/mechanical qualification.

## Concurrency and reproduction

`inputs.json` records initial read hashes; `placement-boxes.json` separately records the exact actual-board hash used for173 volume screens. Sol changed `DESIGN.md`, `corner-proof.py`, `corner-proof.json` and the live board during this pass, as expected. `screen.json` reports those changes rather than overwriting input hashes. **This proposal is against the frozen extracted geometry and fixed user-specified electrical corner, not acceptance of the final Sol revision.** Parent must compare/re-extract after integration; no power-file mutation was made here.

From repo root:

```sh
python3 hardware/compact-dmx/eda/buffer-fit-candidate/screen.py
NOVA_BUFFER_FIT="$PWD/hardware/compact-dmx/eda/buffer-fit-candidate" QT_QPA_PLATFORM=offscreen /home/juicebox/.local/bin/freecadcmd hardware/compact-dmx/eda/buffer-fit-candidate/geometry.py
python3 hardware/compact-dmx/eda/buffer-fit-candidate/draw.py
```

`extract-placement.py` is the read-only KiCad extraction tool used once; it writes only here. Do not rerun it against a changed source and call that the same evidence. `freeze.py` refuses to overwrite its initial record. `receipt.json` holds artifact/source hashes and final checks. No hardware operation, firmware, installation, publication, baseline edits or product acceptance.
