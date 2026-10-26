# Five RF land assignments resolved; one switch datum remains open

This supersedes the five RF land-applicability gates in COMPLETION.md. It does not supersede RF tuning or whole-product qualification. No balanced-network connection, band or matching topology changed.

| Ref | New prototype MPN | Nominal starting value | Source-backed land |
|---|---|---|---|
| L102 | Coilcraft 0402HP-2N7XGRW | 2.7 nH ±2% | Coilcraft_0402HP_Manufacturer |
| L103 | Coilcraft 0402HP-5N1XGRW | 5.1 nH ±2% | same |
| L104 | Coilcraft 0402HP-12NXGRW | 12 nH ±2% | same |
| C115 | Murata GJM1555C1H1R0BB01D | 1 pF ±0.1 pF | Murata_GJM155_Manufacturer |
| C116 | Murata GJM1555C1H8R2DB01D | 8.2 pF ±0.5 pF | same |

The original Johanson MPNs remain in historical receipts as the antenna reference's starting BOM. Current schematic, export, assignment ledger and BOM use the replacements above. These are **not demonstrated equivalent RF components**. ESR, parasitic capacitance, self-resonance and board geometry change the match. Retuning and two-port/coupling measurements remain mandatory.

## Source geometry and electrical limits

[Coilcraft Document526](https://www.coilcraft.com/pdfs/0402hp.pdf), p1 revised12/20/23, p2 electrical table/order codes. The current official product page still lists the selected G/R/W configuration. Drawing H=.66, I=.36 and J=.51 define two .36×.66 mm pads, centres ±.435 mm after a 90° drawing rotation. Body maximum1.09×.71×.61 mm before optional solder; optional solder can increase length/height as noted in source. The added .25 mm courtyard is our assembly margin, not manufacturer approval.

| Value | Q typical900MHz /1.7GHz | SRF typicalGHz | DCR maxΩ | Irms mA |
|---|---|---|---|---|
| 2.7nH | 62 /85 | 13.0 | .085 | 1500 |
| 5.1nH | 54 /76 | 6.80 | .125 | 1200 |
| 12nH | 66 /100 | 4.40 | .100 | 1200 |

These are component test-fixture results, not assembled RF-path loss. The table does not guarantee Q at2.4GHz; Irms is a thermal-rise rating, not an RF power rating. No voltage rating is inferred from it.

Murata exact reference sheets [1pF](https://search.murata.co.jp/Ceramy/image/img/A01X/G101/ENG/GJM1555C1H1R0BB01-01A.pdf) and [8.2pF](https://search.murata.co.jp/Ceramy/image/img/A01X/G101/ENG/GJM1555C1H8R2DB01-01A.pdf), product specifications as of2026-04-15: p2 dimensions/rating/order suffix, p3 Q, p25 land table. Body1.0±.05 ×.5±.05 ×.5±.05 mm; C0G50V. Chosen reflow dimensions a=.4 gap,b=.4 padlength,c=.5 padwidth lie within a=.3–.5,b=.35–.45,c=.4–.6. Pad centres ±.4 mm. Nonpolar terminal numbering1left/2right is local and consistent with the circuit. Q≥420/564 respectively at1MHz; **this is not GHz Q or ESR evidence**. Exact GHz SRF, RF current and loss are not specified in these sheets and remain component-model/bench gates. The combined DC+AC peak must respect50V; no RF-power guarantee is claimed. Package D is explicitly listed. Current exact manufacturer sheets support this prototype selection, not procurement availability or approval-sheet signoff.

Both manufacturer dimension drawings were rendered and visually read; no pixel scaling was used. Source PDF hashes and URLs are in replacement-source-evidence.json. Only one direct datasheet route was needed per replacement family; prior unsuccessful Johanson routes were not repeated.

## PCM12SMTR — specific unresolved datum, no invented correction

The cached official VL03/14/25 p2 was rendered and inspected again. The product is Active per parent's primary-page receipt. Signal-pad top to locator centre2.5mm and bottom to centre1.0mm establish signal-pad length1.5 and vertical centre−1.75 relative to the locator. Signal widths.7, pin spacing3/1.5, Ø.9 locators spaced3, mechanical pads1×.8, inner horizontal mechanical gap6.3 and inner vertical gap1.13 are dimensioned. **No unambiguous dimension locates either mechanical row vertically relative to the locator centre.** Do not derive that offset from drawn symmetry. The present library's1.41mm row gap remains knowingly provisional; changing only the gap without a datum would still not establish the full pattern. A bounded primary CAD/drawing search returned the same PDF/guide, not an independently dimensioned native land drawing. No third-party generated footprint was promoted to manufacturer evidence and no switch alternative was added.

Supplier-confirmed row-to-locator datum/native drawing is required to close this last assignment. Pin2common, position1connects1–2 and position2connects2–3 remain unchanged; NC pin1 makes shipping position1 termination OFF. This is latching/manual, not power-on automatic OFF. Existing normal-DMX load/300mA6V switch limits, isolated metal-pad handling and polymer tool-access gates remain. Source dimensions/body locatorsØ.8 are not confused with PCB holesØ.9.

## Current check scope

17 KiCad-parsable footprint files;16 dimension-checked patterns;113 numbered library pads dimension-checked. All37 physical assignments/pin sets are checked against real exports:36 source-backed,1 provisional switch. MCU26components/57nets/zeroERC; DMX14components/15nets/zeroERC. Regenerated partial placement:37parts/156pads/67nets, semantic TX/RX/RE joins checked, gated requests distinct, all five isolated parts in their region, zero geometric DRC violations and89 unrouted connections. Six antenna NC islands remain independent. No power or CAD edits, no manufacturing/fixture-fit claim.
