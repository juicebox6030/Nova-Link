# Qualified 1.5 A separated-power prototype

This directory is an independent, editable prototype at shared `main/b42c0e6284aac734fde851c69146abf73920f337`. The owner selected **5 V USB-C advertising 1.5 A or 3 A**, including the barrel. No PD voltage negotiation, USB data, second radio, ESP, firmware, programming, installation, canonical integration, commit or publication is included. The CC1352R shares 2.4 GHz and US915 operation; the existing conservative **1.11 W** load allocation is retained, without inventing an RF measurement.

Open [qualified15.kicad_sch](qualified15.kicad_sch), its [control sheet](control.kicad_sch), [schematic PDF](qualified15.pdf), and [complete placement](qualified15-placement.kicad_pcb). The [component ledger](component-ledger.csv) lists exact primary MPNs, values and physical packages. Its body column is a comparison estimate; complete lands and their courtyards determine packing. The horizontal cell row uses its maximum 28.4×13.5 mm projection, with a separate 35×13.5 mm mechanical reserve. [Placement ledger](placement-ledger.csv) adds every land, side, position and occupied courtyard. Source hashes and original URLs are in [source-manifest.json](source-manifest.json); the [land-source record](land-sources.json) distinguishes manufacturer examples from prototype process choices. This is not a manufacturing release.

## One selected circuit

`VBUS_RAW → TPS259474L → LIMITED_5V → TPS2116 main mux → BACKUP_RAW → TPS62132 → SYS_3V3` supplies normal operation. The **BQ25173** charger is a separate branch directly from `LIMITED_5V` to the unchanged **HV1325-2R7156-R 15 F** cell. **TPS61023** boost draws only from that cell. Its nominal 3.939 V output is the main mux backup input and the independent AON mux backup input. No TPS61094 or TPS2553 remains in this candidate.

The main TPS2116 is manual: MODE=AON_2V5, PR1=SOURCE_VALID, VIN1=LIMITED_5V, VIN2=BOOST_3V9. A second TPS2116 (U40) supplies AON_RAW in priority raw-first mode: MODE=VIN1=AON_USB_LIMITED, VIN1=VBUS_RAW through 330 Ω, PR1=22.1 kΩ/10 kΩ from this input, VIN2=BOOST_3V9. TPS7A0225 supplies AON_2V5. The raw AON feed is independent of main/charger startup and their PG signals. TPS2116 reverse blocking replaces the earlier diode-OR reverse-leakage assumption. Its 0.15 µA maximum is explicitly associated with the published VOUT=5.5 V, VINx=0, VINy=open, 105°C test; dynamic reverse response has no specified maximum.

The approved extra source headroom removes the former branch TPS2553, branch-fault hold logic, large 500 mA startup reservoir, additional startup latch and their support parts. It does **not** prove a maximum startup current. A failed charger may shut down the whole main power path; continued main operation through that failure is not required.

## U40 correction to the reviewed capture — 2026-10-23

The original reviewed capture connected U40.5 MODE to ground. TI TPS2116 **SLVSFG1A §7.3.1, table on PDF page 10**, makes that external-low-bias manual mode: PR1 HIGH commands **Hi-Z**, not VIN1. Thus a valid source shut off AON on empty-cap cold boot and also on hot reattach, irrespective of a valid backup. The earlier pin checker matched the incorrect wire and the numerical proof incorrectly assumed priority selection. The immutable review snapshot is unchanged; [historical receipt](history/pre-u40-fix-receipt.json), [historical hashes](history/pre-u40-fix-file-hashes.json), netlist and board preserve the pre-correction state, whose functional claims must be read with this defect.

The **only exported pin/net change is U40.5: GND_USB → AON_USB_LIMITED**, directly tied to U40.3 VIN1. No new part, value, buffer, gate or interface is added. This is TI's MODE=VIN1 priority configuration, with PR1 still sensing that input through 22.1 kΩ/10 kΩ. It needs neither AON-powered MODE bias nor AON logic to select the raw input. Raw absent with boost valid selects VIN2; raw above the priority threshold selects VIN1 even with boost absent. When neither selected input is within the operating range, no regulated-AON or logic behavior is asserted. A cap alone cannot rearm the actual SR latch after reset: its set path still requires externally qualified SOURCE_VALID.

[Independent behavioral regression](mux-mode-proof.py) transcribes all seven rows of §7.3.1 separately from the generator, exercises 24 raw/boost states and 48 qualified-source corner cases, and retains two negative mutations of the original grounded MODE connection. Both original coldboot and hotattach resolve to Hi-Z; both corrected cases select VIN1. The exported gates are additionally exercised using the modeled physical AON path for cold boot, default-current source, hotattach, backup and source-free rebound. The exhaustive 1536 stable cases remain conditional on established logic supplies, explicitly separate from analog startup. Exact pin and all passive checks still run. Numerical corners now check the actual MODE topology through this model rather than inferring mode from PR1 alone.

**Specified DC limits and conditional load screen:** §6.3 gives inputs 1.6–5.5 V and controls 0–5.5 V; §6.1 absolute limits are −0.3–6 V and are not operating permissions. MODE follows the raw-fed VIN1 up to the existing 5.5 V maximum; it is not boost-fed. VREF is 0.92–1.08 V and PR1/MODE leakage maxima are 0.1 µA each (§6.5). Including the existing ±0.35% total resistor allowance and PR1 leakage gives an input threshold span **2.937–3.486 V**. At the existing 4.4 V raw minimum and **2 mA total AON-feed engineering allocation**, the 330 Ω feed leaves at least **3.73769 V**, giving **251.9 mV** priority margin. Loss of guaranteed priority occurs at about **2.761 mA** at that raw minimum; retaining 200 mV of margin allows only about **2.157 mA**. This is a load headroom limit, not a specified total AON current maximum.

The divider draws at most **171.95 µA** at 5.5 V. Conservatively summing U40 IQ maxima 4.4/4.5 µA, 2.1 µA standby and two 0.1 µA pin leakages gives another **11.2 µA**, with the individual TI voltage/test conditions retained. About **1.817 mA** of the 2 mA allocation remains for the LDO, AON logic, pull networks and other loads. The new MODE connection adds at most the published 0.1 µA pin leakage within this allocation; the resistor-bounded raw-source fault-current screen already covers this path. There is **no published whole-board switching/startup current maximum** supporting a guaranteed 2 mA limit. Effective capacitance/inrush, supply ramps, load steps and hot switching require measurement. No PR1 hysteresis bound is invented to guarantee absence of chatter near the threshold.

**U19 as AON rises:** its external MODE remains AON_2V5. With MODE≤0.35 V and PR1 LOW it can select the higher input, including LIMITED_5V on an empty-cap start, so BACKUP_RAW must not be treated as isolated before AON qualifies. With PR1 HIGH in that same range it instead shuts down. The external MODE interval **0.35–1 V is unspecified**. Consequently the original 11 µF initial eFuse capacitance screen is conditional on U19 already selecting VIN2. Early VIN1 selection can add the 20 µF common node, totaling 31 µF nominal /39.215 µF under the existing allocation. At the same unguaranteed slew allocation this is 19.58 mA, still only a conditional screen; neither the ordering nor a peak-current maximum is established. At MODE≥1 V, PR1 selects VIN1/VIN2 in manual mode; an absent selected input has no valid output guarantee. Once logic is valid, AON_OK holds SOURCE_VALID low until the actual supervisor releases; BUCK_EN/CHARGE_DISABLE remain separate logic conditions. Sub-1.65 V gate outputs and transition races are still unproven. §7.3.2 softstart has no guaranteed maximum startup current/time; §7.4 fast-collapse restrictions and unspecified handoff/RCB maxima still apply. No startup, protection, thermal, routing, strict source-current or runtime gate is closed by this correction.

The saved board changes only the U40.5 net token: all other board bytes, including every position, actual contact/pad geometry, footprint, reserve and original 37 parts, are preserved. Validation uses [refresh-u40-placement.py](refresh-u40-placement.py) instead of rerunning the historical packing search. The independent KiCad saved-board checker confirms the one actual pad/net difference and unchanged geometry. Counts, courtyard areas, 150 mm² reservation failure and unrouted state remain unchanged.

## Actual CC qualification and power-off behavior

The physical connector is **GCT USB4125-GF-A**, drawing revision A6, blank stake option nominally for 1 mm PCB. “A6” is the drawing revision, not an extra MPN suffix. The real contacts are A5=CC1, B5=CC2, A9/B9=VBUS_RAW, A12/B12=GND_USB. Four actual SH plated slots also connect to GND_USB as a prototype shell decision. There are no phantom unused 24-contact pins. The old CX70M comparison is untouched.

TUSB320LAIRWBR is raw-powered through 150 Ω and TPS70933, with no boost supply path. PORT=GND selects UFP; ADDR=open selects GPIO; EN_N=GND; VBUS_DET uses 909 kΩ. Its internal dead-battery Rd is used on both CC pins: no duplicate external Rd. OUT1 and OUT2 pull up only to CC_3V3 through 10 kΩ. Both orientations use the datasheet GPIO codes:

| Physical state | OUT1 | OUT2 | External main permitted |
|---|---:|---:|---|
| Unattached/detached | 1 | 1 | No |
| Default advertisement | 1 | 0 | No |
| 1.5 A advertisement | 0 | 1 | Yes, after supply/MR qualification |
| 3 A advertisement | 0 | 0 | Yes, after supply/MR qualification |

SN74LVC1G14 inverts OUT1. **TPS3808G33DBVR U26**, supplied and sensed from CC_3V3, takes this actual advertisement result on MR. CT is open: release requires valid supply and MR continuously for **12–28 ms**. Its open-drain RESET directly drives eFuse EN/UVLO. This replaces a separate POR plus AND gate, whose output below 1.65 V could not prove main-off during a ramp.

CC_ALLOW pulls up through **115 kΩ** to CC_3V3 and down through **249 kΩ**; CC_3V3 has a 10 kΩ bleed. Independent corners include initial 0.1% plus 100 K × 25 ppm/°C resistor error, ±5 µA AON input leakage, eFuse EN leakage, supervisor output leakage, and conservatively all raw-mux reverse leakage injected at the enable node. Results:

- Normal qualified CC_ALLOW minimum **1.782 V**, above the AON logic 1.7 V VIH and eFuse 1.223 V maximum rising threshold.
- Below the supervisor's 0.8 V valid-reset supply, even an open RESET gives CC_ALLOW ≤**0.963 V**, below eFuse UVLO's 1.183 V minimum rising threshold.
- At 0.8–1.3 V the calculated worst reset sink load is **14.849 µA**, within its 15 µA/0.2 V valid-reset specification. Above 1.3 V the published 0.3/0.4 V VOL limits stay below eFuse's 0.45 V minimum shutdown threshold.
- With CC off, calculated CC_ALLOW ≤**0.4385 V** and CC_3V3 ≤**36.6 mV**. These are narrow static margins, not measured transient levels. The TPS3808 valid-reset specification assumes supply rise time ≥15 µs/V; the actual CC ramp must meet that condition, in addition to the TUSB maximum-ramp requirement. Raw reverse response, supply ramp, leakage at actual test conditions and coupled noise remain physical tests.

The CC LDO 3.234 V engineering minimum allocation exceeds U26 maximum rising threshold including hysteresis, 3.1928 V, by only **41.2 mV**. TPS709 effective output capacitance and the TUSB320 **≤25 ms supply-ramp requirement** must be checked on the assembled circuit. TUSB320 IQ and 168 ms debounce are typical, not invented maxima. Correct barrel CC advertisement is an external product obligation; a 5 V/1.5 A label alone is insufficient.

Default/invalid CC disables the **USB main path**. A previously armed cell may supply the bounded backup interval after downgrade/detach; its existence never keeps source status high. No uncharged default-source boot is permitted. This distinction preserves the requested buffer rather than treating CC detach as an immediate load kill.

## Source, cap, buck and charger sequencing

Three real open-drain outputs form SOURCE_SENSE_OD: eFuse PG, raw VBUS undervoltage, and post-eFuse LIMITED_5V undervoltage. The latter two use TPS3700 and 89.8 kΩ/10 kΩ dividers. This node cannot be asserted by the cap-fed common rail. A Schmitt buffer and triple AND form `SOURCE_VALID = source_sense & CC_ALLOW & AON_OK`.

TPS3700 monitor dividers are source-checked independently of the generator:

| Monitored rail/function | Top/bottom | Rising corners V | Falling corners V |
|---|---|---|---|
| Raw VBUS and LIMITED_5V/source validity | 89.8 kΩ/10 kΩ | 3.9250–4.0597 | 3.8358–4.0195 |
| BACKUP_RAW/main readiness | 80.6 kΩ/10 kΩ | 3.5635–3.6851 | 3.4825–3.6487 |
| BOOST_3V9/boost readiness | 80.6 kΩ/10 kΩ | 3.5635–3.6851 | 3.4825–3.6487 |
| Loaded cell cutoff | 32.4 kΩ/10 kΩ | 1.6693–1.7230 | 1.6313–1.7059 |
| Cell arm, near full charge | 52.3 kΩ/10 kΩ | 2.4513–2.5331 | 2.3956–2.5080 |

U9 TPS3839G25 holds AON_OK low through its 120–350 ms reset delay. Its minimum delay exceeds the TPS3700 450 µs maximum valid-output startup delay once its supply exceeds 1.8 V. This is startup inhibition, not a false-good mask.

The control sheet contains actual supported multifunction gates and one cross-coupled SN74LVC2G132 NAND SR latch:

```
cap_set_n   = !(SOURCE_VALID & CAP_START_OK)
cap_reset_n = CAP_OK & AON_OK & (SOURCE_VALID | (MAIN_READY & BOOST_READY))
CAP_ARM / CAP_BAR = actual cross-coupled NAND outputs
CAP_BOOST_EN = buffered CAP_ARM
BUCK_EN = (SOURCE_VALID | CAP_ARM) & MAIN_READY
CHARGE_DISABLE = !(SOURCE_VALID & BUCK_PG)
```

The independent checker evaluates the real exported gates and latch, not this prose notation. Set requires the higher cell threshold and a real external source. Loaded UVLO, AON reset, or loss of both source and a ready backup clears it. Cell/rail rebound without a source cannot rearm. Analog propagation races and operation below the AON logic's 1.65 V minimum remain bench gates.

Healthy empty-cell sequence: raw CC and AON start independently; valid CC enables eFuse; after AON/source qualification U19 selects USB; main readiness allows the buck; actual buck PG enables charging. Once the cell reaches its near-full arm threshold the cap-only boost starts, while the USB source remains in control of the buck. The boost precharge current is drawn from the cell, not the USB main/charger input. A failed boost start does not force raw AON or the USB buck to restart. Backup handoff and loaded-cap cutoff are separate from charging.

TPS3808G01 U27 generates **VBUS_GOOD_3V3** from actual SOURCE_VALID on SENSE and **buffered actual BUCK_PG** on MR, with another 12–28 ms continuous-valid assertion delay. It asserts low asynchronously on a fault, subject to real propagation delay; there is no timed forced-good interval. Its output pulls up only to SYS_3V3. The BUCK_PG buffer prevents the supervisor MR internal pull-up from injecting AON power into the off MCU supply. This status is a future loader's source-presence input, not evidence of completed flash installation, a guaranteed buffer time, or firmware policy.

TPS3831K33 holds MCU reset. SYS-powered dual AND gates enforce `SYS_READY = BUCK_EN & RESET_OK`, `DMX_DE_SAFE = MCU_DE_REQUEST & SYS_READY`, and `DMX_POWER_EN = MCU_ISO_REQUEST & SYS_READY`. MCU/DMX/factory logical **18/7/6** maps remain literal. SERVICE remains distinct from ROM DIO3. No INPUT_FAULT_N translator is implemented or wired into reserved DIO18/pin28. Flash WP/HOLD pulls provide the existing register-dependent protection, not an invented immutable write lock.

## Current, inrush and fault evidence

U6 is specifically **TPS259474LRPWR**, the latch-off **circuit-breaker** variant. ILM=3.32 kΩ. PGTH=10 kΩ/10 kΩ, dVdt=10 nF with 100 Ω series, ITIMER=10 nF. PGTH is not the system source qualifier; the higher TPS3700 thresholds perform that job. OVLO is grounded: this candidate requires nominal 5 V within the 5.5 V power-mux contract and does not claim protection from a wrong high-voltage source.

| Independent calculation | Result and qualification |
|---|---|
| Main trip envelope with resistor tolerance | 0.8470–1.1540 A; table limits use VIN=12 V default test condition |
| Resistor-bounded raw CC+AON feeds, bleeds/detection and eFuse IQ allowance | 54.744 mA maximum screen; default-source main off |
| Trip maximum plus raw feeds | **1.2088 A**, leaving 291 mA to 1.5 A, conditional on table applicability at 5 V |
| Normal source allocation | **387.2 mA**, using 1.11 W, 85% buck efficiency, conditional charge maximum and actual-source floor |
| Normal main margin to minimum trip | **465 mA** |
| Buck VIN when source-valid, including 50 mV allocated undershoot | **3.7165 V**, above the 3.41 V dropout design floor |
| Main-ready floor less 50 mV | **3.4325 V**, only 22.5 mV above that floor |
| eFuse initial directly attached capacitance | **11 µF nominal**, not the later common node |
| Later main-mux common capacitance | **20 µF nominal /25.3 µF maximum allocation**, separately charged after source selection |

The **1.2088 A number is not a guaranteed full-5-V-range or instantaneous maximum**. eFuse IQ maximum is also specified at VIN=12 V. Obtain supplier confirmation or characterize the applicable voltage/current corners; do not mark this strict source-bound gate closed from the 12 V table alone. The generous margin is a design choice, not an invented missing limit.

eFuse's specified dVdt charging-current limits and capacitor tolerances yield a 499 V/s allocation; the internal output-transfer formula is typical, so this is not a guaranteed output slew maximum. The calculated ITIMER-cap interval is 3.935–18.353 ms, excluding unspecified response/initialization maxima. The circuit-breaker passes a finite overload during blanking; fast-trip ratio and response are typical. **It does not enforce an instantaneous 1.5 A ceiling.**

The upstream dVdt capacitor **does not limit later U19 common-node precharge** or a live backup-to-USB switchover. TPS2116 §7.3.2 applies soft start with output below 1 V; the table gives 1.7 ms typical at 5 V/10 µF/100 Ω, without a minimum or maximum current. The numerical screen uses that typical value, a 25.3 µF capacitance allocation, and the separately soft-started buck. Charge conservation also bounds continuous overcurrent attributable to that capacitance to about 0.31 ms under the allocated background load, below minimum ITIMER interval. Neither argument bounds peak current, excludes fast-trip, or proves survival of a source's foldback/dead time. **Healthy empty-cell startup, hot reattach with a charged cell, and actual source behavior remain mandatory transient tests.** No “eventual convergence” claim replaces them.

The separate [fault budget](fault-budget.json) records ten source/current states. The 1.2088 A envelope assumes a healthy ILM programming resistor: the TI table permits a **2.1 A** threshold at ILM short (VIN=12 V test condition). A charger OUT-to-ground or boost VIN-to-ground internal short connects directly to the cell; U6 cannot interrupt that discharge. A charger FB top-open/bottom-short fault can overcharge at only 25 mA, below U6 trip. No independent cell OVP or cell fuse is captured. These are explicit **hardware/protection-policy gates before manufacturing acceptance**, not faults that a bench-only timing check can close. The nominal cell stores 50.7 J at 2.6 V; 19.5 F at 2.7 V is 71.08 J. The manufacturer's 90 A short-circuit figure is a safety reference, not a guaranteed peak limit. No all-single-fault safety claim is made.

Persistent charger input OCP/short may open U6 and remove normal power. EN remains CC-qualified rather than depending on U6 PG/output, so output collapse alone cannot clear the internal latch. Clearing CC qualification or an actual raw supply collapse clears/reinitializes it; a source foldback is electrically an input power cycle and may cause retries. Retention through arbitrary source collapse is not claimed. The independently raw-fed AON avoids the known intentional RUN/AON feedback loop during healthy startup; fault/source-foldback and thermal pulse behavior still require measurement.

## Charge, magnetics, capacitance and runtime

BQ25173 has **100 Ω +11.9 kΩ** ISET with 100 nF filtering, nominal 25 mA; FB=22.5 kΩ/10 kΩ, nominal 2.6 V. Its low-current filter/stability is a prototype choice requiring measurement. KISET=270–330 AΩ gives a conditional 22.42–27.60 mA screen. The accuracy rows explicitly test 3.8/7.6 V, ICHG_RANGE refers to an undefined VBAT_LOWV, and the empty-cell curve is typical. No full-temperature FB bias maximum is published; ±25 nA is an allocation. With it, regulation corners are 2.5610–2.6394 V and even an allocated 50 mV overshoot remains below 2.7 V. Nominal empty-to-2.6 V is **26 min before tail**; the retained conservative capacitance/voltage/current corner is **38.44 min before tail**, not a guaranteed maximum. No arbitrary faster charge is selected. Near-full arm has only about 28 mV margin below the conditional low regulation corner; verify the actual curve and thresholds.

TPS61023 FB=562 kΩ/100 kΩ: nominal 3.939 V in PWM. XGL4020-222MEC 2.2 µH ±20% remains within TI's 0.37–2.9 µH recommended range before saturation. Buck uses XFL4020-222MEC 2.2 µH ±20%, fixed 3.3 V TPS62132, 10 nF SS. Each converter output and the main common node have 2×10 µF. Boost input has 10 µF; CC raw and regulated nodes each have 10 µF; AON rails have 1 µF/2×1 µF groups and every relevant logic IC has its own 100 nF. Exact rail assignments are independently checked. Effective capacitance, buck LC stability, magnetics saturation/DCR/temperature, startup switch current, PFM maximum output voltage and low-VIN conversion efficiency remain physical/source gates. The boost's specified *minimum* precharge current is never used as a maximum.

The unchanged conservative reserve is 15 F ×0.9 initial ×0.7 aging=**9.45 F**, start **2.448 V**, loaded floor **1.705917 V**, **80% combined efficiency**, **1.11 W**. It yields **10.497 s**. The extra 100 mV start reserve is historical conservatism, **not invented BQ25173 termination hysteresis**; this charger maintains CV. With the near-full arm divider the idealized first-arm energy is at least this reserve, but there is no guaranteed energy-ready output.

An explicit alternate calculation with 80% *electronics* efficiency before cell ESR gives **10.112 s at 30 mΩ** and **9.730 s at aged 60 mΩ**, using the manufacturer's 20°C ESR basis. This does not double-count ESR in the combined-efficiency model; it demonstrates why that assumed combined 80% must be established. Cold ESR, actual combined efficiency and simultaneous MCU/DMX activity are unmeasured. **A healthy 10 s minimum is not demonstrated; 10–30 s remains a target.**

## Complete placement and compactness disposition

This uses the frozen **proposed** GCT tongue branch, not the baseline board: USB origin **(42.7,47.6)**, face y54, NOR **(32,41.2)**, main rectangle **90×28 mm**, and tongue x36.5..48.9/y51..53.3 (**12.4×2.3 mm**). The case remains **98×34×24 mm**. The supplied board's original 37 electrical footprints and four holes retain exact pad positions, nets, values and orientation; only their local-copy references receive `BASE_` to avoid collisions with this candidate. USB/NOR pad geometry and mapping exactly match Astra's source.

All **137** candidate footprints exist: 134 purchased parts including USB and cell, plus factory/service/reset PCB features. The saved placement uses **86 top /51 bottom**, with all parts on-board. It is a single deterministic packing method, repaired for API/through-board-obstacle bookkeeping; there is no second electrical architecture or routing optimization round.

The independent saved-board check accounts for the top stop **x38..47.4/y44.6..46.6**, backed pad **x38.3..47.1/y46.6..47.2**, underside rails/shims **x36.9..37.4 and48..48.5/y49..52.7**, actual plated stakes, mounting bosses, cell x26..61/y23.5..37, RF antenna reserve x83.4..94, and isolation/isolated region. It also conservatively reserves the cell projection on the bottom and bottom MCU/RF routing region. New bottom components are ≤1.45 mm tall; nominal PCB-bottom z10 to case-floor z7 leaves ≥1.55 mm floor clearance. New top parts avoid the stop/pad; bridge underside z16 leaves 5 mm above PCB top z11. These dimensioned screens are not an assembled tolerance or cable-strength qualification.

| Comparison | Historical 500 mA separated candidate | Qualified 1.5 A candidate |
|---|---:|---:|
| Purchased parts, USB excluded /cell included | 170 | **133** |
| ICs | 44 | **30** |
| Package-body estimate, cell and USB excluded | 343.745 mm² | **253.180 mm²** |
| Complete core courtyard sum, cell/USB excluded, PCB features included | Not captured | **749.956 mm²** |
| USB courtyard | Not captured | **80.987 mm²** |
| Power core courtyard top/bottom | Not captured | **572.284 /177.672 mm²** |
| Combined existing37 +allcandidate electrical courtyards, both sides | Not captured | **1313.150 mm²** |

Minimum new-to-any same-side courtyard gap is **0.205 mm**; new-to-new minimum is 0.210 mm. Courtyard sums are assembly-side occupied areas, not a rectangular floorplan or remaining routing area. The 472.5 mm² cell projection, 296.8 mm² antenna projection and further reserve unions cannot simply be added without accounting for intentional overlaps. The actual board demonstrates nominal two-sided packing around these reserves, **not routing feasibility**. The requested **150 mm² power reservation fails by about 600 mm² of complete courtyards**; even the package-body estimate exceeds it by 103.18 mm². No reservation or housing constraint is silently relaxed. Routing/return paths, switching-loop/decoupling distance (worst bypass center distance about 6 mm), thermal vias, EMC and complete dual-band RF coexistence remain unresolved.

Real KiCad DRC reports **0 geometric violations and 452 unconnected items, zero tracks**. Five inherited default ignored categories are recorded verbatim in placement-check.json; they are not hidden. Every actual candidate courtyard and all 443 numbered pads are independently checked. No routed-board or fabrication clearance release is claimed. Prototype NSMD DQN lands differ from TI's SMD process example; RPW/EP paste and thermal-via details require assembly review. GCT stake section/1 mm tolerance, formed cell leads, pad/shim material, shell ESD, connector insertion/withdrawal strength, cable access and actual assembly tests remain the supplied mechanical branch's gates.

## Reproduction and stop condition

Run `bash hardware/compact-dmx/eda/power-service/qualified15-candidate/validate.sh` from the repository. [cli-checks.log](cli-checks.log) records exact actual commands, KiCad version and results. It regenerates only this directory. It runs true KiCad ERC with `--severity-all --exit-code-violations`, independent pin/passive/state checks, independent numerical corners and datasheet-mode regressions, a single-pad net refresh preserving the reviewed placement, actual DRC, a separate saved-board checker, and PDF/SVG exports. It does not run the parent's validator, change active BOM/power budget/contracts, or access hardware.

The bounded deliverable is the captured/checked/placed prototype and explicit failed compactness/remaining electrical conditions. It does not establish a strict full-5-V-range DC maximum, peak/USB transient compliance, guaranteed cold start, thermal acceptance, healthy 10 s minimum, routed fit, or manufacturing release. Parent integration and any further architecture/fit choice are subsequent work, not silently authorized here.
