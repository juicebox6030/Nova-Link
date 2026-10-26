# Independent 25 F cell-protection prototype

This is one **captured development prototype, with protection acceptance still UNMET**. It adds an independent cell-overvoltage charger disconnect and a cell-local fuse to the qualified 5 V / ≥1.5 A architecture. Source maxima do not establish fault-voltage overshoot or clearing of a decaying capacitor short. Those are concrete limitations of the selected parts, not checks passed by ERC. No manufacturing release, all-single-fault safety, healthy 10 s minimum or sidecar fit is claimed.

Editable capture: [cell-protection.kicad_sch](cell-protection.kicad_sch), [PDF](cell-protection.pdf), [exported netlist](cell-protection.net). Exact parts and scope are in [component-ledger.csv](component-ledger.csv). The independent checker and its numerical/fault results are [verify.py](verify.py) and [checks.json](checks.json). All writes are confined here. Qualified15, the historical siblings, budgets, main docs/BOM/CAD and Astra's integrated25 work remain untouched.

## The one selected circuit

`LIMITED_5V → U103 TPS22963CYZPR → CHARGER_IN_PROTECTED → existing BQ25173 IN`

`25F cell positive tab → F101 045101.5MRL → CAP_POS → existing charger OUT / cap-only boost / existing UVLO and arm sensing`

Ground stays GND_USB. U101 **TPS3700DDCR**, with its own reference and divider, senses **CELL_TAB_POS before the fuse**, not BQ's feedback node. Its OUTB pulls CHARGER_PERMIT_OD low on overvoltage. U102 **TPS3808G33DBVR** senses and is powered by LIMITED_5V; its RESET output shares that open-drain node. It holds the charger switch disabled during startup and brownout. Its CT is explicitly open and MR tied to its supply. The permit pull-up is 82 kΩ; the switch ON pin has a 10 kΩ series resistor and 56 kΩ pull-down. U103 is the **no-output-discharge TPS22963C**, not TPS22964C. The actual six BGA balls and both duplicate power balls are captured.

All detector/control power comes from the existing protected USB branch, independently of the BQ output, AON, MCU and firmware. No new main-power switch or CC logic is introduced. U103 need not operate from the cell at its 1.706 V loaded floor: it switches the charger input only. F101 is passive in the discharge path. Existing CHARGE_DISABLE continues to control BQ normally, and neither the protection node nor its startup delay overrides SOURCE_VALID or VBUS_GOOD.

The OVP response is **hysteretic cutoff/retry, not latched shutdown**. It disables charging while cell voltage is high and may retry once voltage falls below the comparator's hysteresis threshold. A permanently failed charger can cause repeated bounded-threshold attempts; actual chatter, overshoot and fault heating must be tested before accepting this behavior. The non-resettable fuse requires replacement after it opens. No assumption of continued operation through a fault is used in the acceptance argument.

This adds **14 purchased protection parts**: three ICs, one fuse, five resistors and five capacitors. C202 is a new local 1 µF BQ output filter because the fuse/formed leads separate the large cell from that node. The rest of the charger is shown as context; two existing feedback resistors are tuned as below. No arbitrary charge-current increase is proposed; nominal charging remains 25 mA.

## Operating, threshold and startup bounds

Primary documents are cached and hashed in [sources.json](sources.json): TI TPS3700 SBVS187G §§6.3–6.7/7.3/8.2, TPS3808 SBVS050N §§5/6/7, TPS22963C SLVSBS6A §§7/8/10/11.1.4, BQ25173 SLUSDY6 (November 2021) §§6/7/8, Vishay TNPW document28758 pp1–4 and Eaton Technical Data4376 pp2–3. These are original manufacturer documents. The original Littelfuse PDF mirror and the current primary crosscheck are distinguished below.

U101 operates at 1.8–18 V; U102 at 1.7–6.5 V; U103 at 1–5.5 V, with output and ON limited to its published ranges. LIMITED_5V must remain within the existing nominal 5 V source envelope; an overshoot above 5.5 V is not justified by a 6 V absolute rating. U103 is rated −40…85°C; the system cannot charge this Eaton cell at 2.576 V throughout that full range. **The cell must remain ≤65°C**; extension to 85°C requires 2.3 V derating. No new full-85°C operating requirement is assumed.

The OVP divider is **56.5 kΩ /10 kΩ**, each TNPW0402, 0.1%, **10 ppm/K** (`BYED`). Initial tolerance plus a conservative 100 K TCR allowance gives ±0.2% per resistor. With TPS3700's 396–404 mV rising reference and ±25 nA input-current bound, independent enumeration gives:

| Quantity | Result | Evidence/limit |
|---|---:|---|
| OVP rising threshold | **2.623059–2.697164 V** | Specified reference/resistor/input-current corners, before lifetime drift |
| Separate falling-threshold envelope | **2.563412–2.670473 V** | 387–400 mV reference corners; not a correlated per-device hysteresis interval |
| Sense hysteresis | 5.5 mV typical /12 mV maximum | No specified minimum; no anti-chatter guarantee invented |
| Maximum static threshold room below 2.7 V | **2.836 mV** | Does not include propagation or overshoot |
| TPS3700 startup | **450 µs maximum** | Supply must exceed 1.8 V |
| U102 reset release | **12–28 ms** | CT open; startup inhibition while source remains above its threshold |
| U102 worst rising threshold incl. hysteresis | **3.1928 V** | Below the existing 3.83578 V qualified-source floor |
| ON minimum high | **1.419 V** | Above U103's 1.3 V VIH |
| ON maximum pre-POR /inhibited low | **0.330 /0.341 V** | Below even U103's 0.4 V low-voltage VIL |

The ON calculation includes both OD leakages, the switch's 150 nA ON leakage, ±0.35% allowance on its three resistors and attenuation of the supervisor's 0.4 V maximum low. The worst low-voltage supervisor sink screen is **14.21 µA**, below its 15 µA POR test. TPS3808's POR guarantee has the published **Trise ≥15 µs/V** condition; the actual LIMITED_5V waveform must satisfy it. Nothing is asserted about U103 functionality below its 1 V operating minimum. At established supply, the 12 ms minimum reset hold exceeds the independent detector's 450 µs startup maximum. This prevents healthy empty-cell startup from intentionally enabling the switch before the detector starts; transient ramp/glitch behavior remains unmeasured.

There are **32 static supply/startup/OV/CE/fuse states**. The supply flag means LIMITED_5V exceeds the supervisor release threshold; it does not independently assert CC qualification. Existing CHARGE_DISABLE remains the external source/load-sequencing control. Each static case is checked, with actual exported pin and passive topology checked separately. Existing cap-arm/no-source-free-rearm hardware is an external unchanged boundary, not a newly validated function of this small capture. A detached source does not intentionally receive cell power through this control circuit. TI specifies reverse protection when U103 is disabled and either VIN or VOUT exceeds 1 V (§11.1.4); turnoff response and leakage maxima are still absent. No ideal-zero-backfeed assertion is made.

## Necessary charger tuning and runtime cost

Keeping the old 2.6 V nominal setting, its 2.639335 V conditional maximum and its old 50 mV overshoot allocation would cross this OVP window. This proposal therefore uses **R201=22.2 kΩ /R202=10 kΩ**, both 0.1%/10 ppm/K, giving **2.576 V nominal**. The top changes from 22.5 kΩ; the bottom value stays 10 kΩ with tighter TCR. These changes exist only in this candidate; parent integration must change the existing feedback-role parts explicitly. No cap-arm, loaded-UVLO, buck, main mux or charger-current setting changes.

Using BQ's ±1% reference and the existing **25 nA FB-bias engineering allocation** gives **2.542667–2.609506 V**. BQ does not publish the full-temperature FB-bias maximum needed to make that a complete regulation guarantee. A **5 mV healthy overshoot test target** leaves **8.553 mV** to the earliest OVP trip. This replaces the old 50 mV allocation only in the proposal and is a new physical validation gate, not a measured improvement. Resistor lifetime drift is not included in those numbers. With the conditional 27.60 mA charge maximum and a 126 mΩ fuse-resistance allocation, the minimum charge voltage still exceeds the unchanged 2.533074 V arm maximum by **6.116 mV**. That is narrow, conditional arm headroom.

The reserve start must change too: `min(2.448, Vcharge_min −0.100 −Icharge_max×0.126)` gives **2.439190 V**. It would be incorrect to retain 2.448 V silently after this tuning. The cell ESR remains the owner's 54 mΩ aged test screen; C remains **25×0.9×0.7=15.75 F**, load1.11 W and electronics efficiency80%. The existing loaded cutoff1.705917 V is applied **after** the added fuse/trace drop. Added cell-side OVP-divider current is bounded by the intact top resistor at about47.9 µA; a separate **10 µA switch-reverse-leakage allocation** is not a manufacturer maximum.

| Conditional discharge screen | Runtime |
|---|---:|
| Parent basis:2.448 V,54 mΩ ESR,no new protection | **16.343 s** reproduced |
| New2.439190 V start,63 mΩ nominal fuse,10 mΩ trace allocation,added leakage | **14.564 s** |
| Same,126 mΩ hot-fuse test allocation | **13.256 s** |

The checker solves the constant-power voltage/current relation with ESR plus protection resistance and integrates discharge. An independent 100 µs forward-time integration agrees within0.2 ms; quadrature refinement is also checked. The calculation also includes Eaton’s **45 µA cell-leakage reference at20°C after72h hold**, plus a conservatively bounded47.88µA sense branch and a10µA switch-reverse-leakage engineering allocation. Cell leakage at other temperatures or earlier in charging is not bounded by that reference. These figures are useful prototype headroom, **not a guaranteed healthy10 s result**. Fuse resistance is nominal at25°C, not a maximum; hot resistance, added reverse leakage, actual RF/DMX/boot load, efficiency, temperature and cold/age C/ESR remain unmeasured. `checks.json` gives the conditional fuse-resistance ceiling for10 s: **286.62 mΩ**, with all other stated allocations fixed; this is not a fuse selection guarantee. The 2.7 V maximum remains a rating; 3 V surge is not a charge target.

The added source-side operating-current allocation is **250 µA**, separate from25mA cell charging. Published point bounds include TPS3700 13µA at5V, TPS3808 6µA at6.5V and TPS22963C 96µA at5V; the resistor network draws at most67.31µA at5.5V. This is not a complete guaranteed5.5V sum: switch IQ at5.5V and fixed-supervisor SENSE current lack corresponding maximum entries. Parent must carry that allocation and the unmeasured switched2µF input inrush into integration, rather than silently preserving an old source-current maximum.

Charging at25 mA to2.576 V takes nominally **42.93 min before CV tail** for25 F; actual empty-cell current behavior, KISET accuracy conditions, feedback bias, effective capacitance and filter stability remain the existing BQ source/bench gates. The cell contains84.5 J at25 F/2.6 V and up to118.46 J at32.5 F/2.7 V. The lower proposed target does not remove the need to consider maximum stored energy.

## Fault interruption and the exact remaining objections

| Fault | Intended physical interruption | What is not established |
|---|---|---|
| BQ feedback top open /bottom short | Separate U101 cell reference/divider drives U103 OFF, removing BQ input | Maximum trip-to-block time /fault overshoot; hysteretic retry behavior |
| BQ IN-to-OUT short | U103 opens the upstream5 V path even though BQ CE/feedback cannot stop it | U103 fault SOA/peak/turnoff and disabled reverse-current maximum |
| BQ OUT-to-ground or boost VIN-to-ground short | F101 is before the split and carries cell discharge into either branch | Decaying-fault clearing, arc/interrupt performance and fuse/conductor thermal energy |
| F101 open | Cell is disconnected from power branches | No buffer. CAP_POS can rise on charger-side capacitance, so existing arm alone cannot prove fuse continuity and may cycle the boost. No new protection-good MCU/loader promise is made |
| Cell internal short /positive conductor ahead ofF101 | No external interruption | Mechanical isolation, retention and minimum exposed length are essential |

**Source objection1 — OVP:** TPS3700 propagation and TPS22963C turnoff have typical-only entries. At a hypothetical constant1.5 A fault and15.75 F, the2.836 mV remaining rating margin permits only **29.78 ms** from crossing the worst trip threshold to stopping charge. Typical18 µs comparator and2.5 µs switch values are encouraging but cannot prove that bound. Existing input-breaker protection is not a guaranteed instantaneous1.5 A limiter, so the29.78 ms calculation itself is conditional. The two1 µF capacitors downstream of U103 add only about0.45 µV to the cell under the stated capacitance allocation once charging is actually interrupted; they do not bound the unmeasured switch delay or source pulse.

**Source objection2 — short clearing:** F101 **045101.5MRL**,1.5 A, has **63 mΩ nominal cold resistance and0.853 A²s nominal melting I²t**. The manufacturer's hard timing statement is5 s maximum at **constant200% rating**; its curves are averages. At the nominal aged-cell/fuse/trace screen, a hard short starts near19.28 A and decays below3 A after **3.72 s**. The5 s-at3 A condition is therefore not a guaranteed clearing proof for that waveform. No maximum total-clearing I²t, minimum fuse resistance or minimum cell ESR is supplied to close interruption/thermal bounds. The current primary table gives300 A interruption at32 V for this rating; actual prospective current must be established and remain within the applicable interrupt rating. Eaton's100 A short reference is not a guaranteed current ceiling.

At the loaded cutoff, healthy bus current is about0.813 A. With126 mΩ fuse resistance the instantaneous fuse loss screen is **83.35 mW**. After Littelfuse's standard75% continuous-current derating, the temperature rerating factor must remain above **0.723** at that current; assembled fuse temperature and cycling must be measured. Boost startup maximum current and pulse I²t remain unspecified. Do not compare unknown boost inrush against the nominal0.853 A²s and mark nuisance immunity passed. Neither post-opening insulation nor an arbitrary high-resistance/partial short is treated as ideal isolation or guaranteed fuse clearing.

F101 short/bypass, U103 short, OVP-reference/divider failure, reversed assembly and pre-fuse faults are not covered by redundant protection. This is **not all-single-fault safe**. The full ten-state fault account is in checks.json. The unresolved physical tests are peak/current-time and clearing voltage acrossF101; lead/trace/PCB temperatures and residual energy; OVP fault/healthy overshoot and repeated retry; source attach/brownout/ramp and reverse charge; charger filter stability; boost startup pulses; runtime at actual activity/temperature/age; and cell temperature/retention/vent/insulation.

## Parts, sources and physical integration

The complete land/area coupon contains **21 actual footprints /61 numbered pads**, including seven retained/tuned charger-context parts. It is32×16 mm, unrouted, and explicitly **not a sidecar placement**. Saved-board pads match the real exported nets. It has zero geometric DRC violations and45 unconnected items. The five inherited default ignored categories are recorded in package-check.json; no new exclusions are added, and every actual courtyard is checked separately.

The **14 added protection parts** occupy **36.815 mm² of maximum body projections and85.765 mm² of complete courtyards**. These sums exclude integration wiring/spacing, are not free board area, and must not simply be added to a top/bottom floorplan as a fit claim. F101's maximum body is **6.30×2.94×2.94 mm** and courtyard7.36×3.65 mm. It is the tallest new part. Top-side placement is preferred; the existing3 mm nominal underside clearance would leave only0.06 mm before tolerances. It cannot occupy the rigid rear stop's0.5 mm top clearance. Astra's aperture/retainer/RF/USB reservations must be checked against an actual integrated placement. The case and sidecar are not enlarged here.

The6-ball TPS22963CYZPR uses TI's0.5 mm pitch /0.225 mm round NSMD lands, maximum die0.972×1.472 mm and0.5 mm height. Its source land pattern was rendered and inspected, avoiding confusion between bump view and top assembly view. DDC/DBV/DSG and passives are exact copies of the existing source-derived lands, with the source PDFs hashed here. Fuse lands preserve the manufacturer's6.86 mm outer span and1.96×3.15 mm pads; its separately rounded2.95 mm inner-gap callout differs by0.01 mm from the derived2.94 mm. That rounding and stencil/reflow details require assembly approval, not a false exact-dimension claim.

**Before the cell branches split**, put F101 at the actual positive lead landing. Target ≤2 mm of unfused PCB copper from that landing to the input fuse land, no unfused via/plane or power branch, and insulate/strain-relieve the entire necessary formed positive wire. Place R101 at the cell landing so its sense conductor is already current-limited. This is a physical integration target, not a measured layout: the required lead forming and actual placement belong to Astra/parent. Cell-internal and pre-fuse energy cannot be disconnected by the fuse.

The new boundary proposal is explicit: actual cell positive becomes **CELL_TAB_POS**; **CAP_POS** remains the protected existing charger/boost/sense bus. Existing BQ IN is rerouted from LIMITED_5V to **CHARGER_IN_PROTECTED**. MCU/DMX/factory maps, CC qualification, all main power nodes and the existing cap-arm/UVLO circuit stay outside this capture. No fault translator, status pin, loader implementation or active BOM edit is introduced.

The current Littelfuse manufacturer PDF was readable through web but returned403 to local retrieval. The cached original manufacturer document is the2011 distributor-hosted PDF, with its real byte hash; the critical row, dimensions,5 s opening and continuous derating were crosschecked against the current2025 primary PDF. [fuse-primary-facts.json](sources/fuse-primary-facts.json) records the distinction. No hash of uncached2025 PDF bytes is invented. Other cached PDFs retain original manufacturer bytes and URLs. TPS3760 and TPS3703 were the two alternative monitor families considered; startup-unlatch/window behavior adds unresolved sequencing or empty-cell constraints, so neither is substituted silently. No further architecture search is part of this result.

## Reproduction and stop

From the repository run `bash hardware/compact-dmx/eda/cell-protection-candidate/validate.sh`. [cli-checks.log](cli-checks.log) records actual commands. It regenerates only this directory, runs real zero-ERC, independent27-pin/17-passive/32-state and numerical/fault/runtime checks, opens the saved coupon's actual pads, performs real DRC and exports PDFs. Sources and175 protected inputs are rehashed. `receipt.json` and `SHA256SUMS` describe the current artifacts.

Stop after this bounded capture and validation. **The cell-protection requirement remains UNMET pending the specific source/physical bounds above.** Parent can integrate this concrete prototype with Astra's actual placement for bench qualification; integration and any later part change are not performed here. No publication, firmware, hardware operation, installation, new thread or review round is included.
