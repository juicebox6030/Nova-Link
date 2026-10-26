# Current power-only, buffer and RDM service hardware

This is a source-backed **prototype circuit capture**, not a routed, certified or
released product. The MCU/RF implementation and existing isolated DMX sheet are
explicit interfaces. Power-path, comparator, latch, POR, reset and DMX control gates
are actual components in this schematic, not unimplemented boundary boxes.

Owner correction retained verbatim: “Thats fine, we can skip usb interop and just leave wireless AND wired RDM as the main path. The key is going to be how do we flash updates to the device over the DMX port”.

The former USB bridge/recovery candidate is superseded under `../historical/` and
is excluded from current acceptance. No CP2102N, USB-data path, enumeration gate,
USB recovery rail, ESP or high-current CC decoder is an active product part.

## Power path and hardware states

J_USB represents the USB-C electrical interface: all four VBUS contacts and all
four returns join, each CC has its own5.1k1% Rd, all data/SBU contacts are NC.
Hirose shell tabs, exact footprint, ESD/protection and enclosure integration still
require layout capture. USB Type-C R2.4 October2024 §4.6.2.1, printed p226,
explicitly permits a PSD at Default advertisement to draw up to500mA while meeting
USB2.0 inrush. It also requires full Type-C Current support and no USB/Alternate
Mode communications. This design never increases draw for1.5A/3A advertisements.
That is a conservative design interpretation, **not USB certification**; source,
legacy-adapter, detach and inrush qualification remain required. The consulted
primary copy is `../../../../.tools/references/usb-type-c-r2.4.pdf` in this workspace
(the tools directory is ignored, not a redistributable package asset).

U6 TPS2553DBVR limits all sidecar VBUS loads except its own input current. R_ILIM
is60.4k,0.1%, with25ppm/°C procurement target. **U19 TPS2116DRLR replaces D_MAIN**
as the low-loss reverse barrier. VIN1, MODE and PR1 connect to LIMITED_5V;
VIN2 and GND are grounded; both VOUT contacts connect to NORMAL_IN; ST is NC.
The selected VIN1 channel replaces a diode drop with an on-resistance allocation
of60mΩ (datasheet maximum at3.3/5V,200mA and up to105°C). C_U19 is local100nF.
There is no second supply or increased USB draw. TPS2553's delayed reverse-voltage
response alone was insufficient as a reverse barrier. U19 also has finite reverse
threshold/current/response time and leakage; it is not a zero-current ideal diode.
R_INPUT_BLEED47k discharges the10µF normal input reservoir after removal.

U3 TPS61094: OSEL17.4k sets3.6V boost; ICHG9.53k sets**25mA** nominal charging;
VCHG9.53k sets2.6V. L_BOOST2.2µH joins SW5 to CAP_POS/SUP6. The15F cell returns
to GND_USB. U4 TPS62132 supplies fixed3.3V through a second2.2µH inductor,
22µF effective output capacitance and3.3nF soft start. FSW and DEF are low;
fixed-version FB is grounded; VOS senses the actual output. Effective ceramic
capacitance, DC bias, magnetics, dropout and transient behavior need qualification.

D_AON_USB and D_AON_BUF OR LIMITED_5V and BACKUP_RAW into AON_RAW. U7 regulates
AON_2V5 for supervision. **U3 MODE connects directly to AON_RAW, independently
of RUN**, so disabling EN does not intentionally select forced bypass while a
source rail exists. MODE's voltage rating is respected on the5V-only input.
After both source rails collapse, MODE may fall; the normal input is isolated and
bled down, and the downstream buck remains disabled. Startup/decay transients
must be measured; zero-time Boolean analysis is not a timing proof.

U8 compares loaded CAP_POS through20k/100k against its internal reference.
**U10 is now TPS3700DDCR**, with INA+ sensing **NORMAL_IN, the actual U3 VIN**,
through93.1k/10k, both0.1%,25ppm/°C procurement targets. OUTA is VBUS_OK with
10k pullup to AON_2V5. Its unused INB− is grounded and OUTB is NC. VDD is
AON_2V5; U9's POR gates downstream logic. The old10nF sense filter and reference
capacitor are removed; a slow filtered source-good must not mask a VIN collapse.
The detector's specified hysteresis is included in both rising and falling
thresholds below. This remains **a voltage indication, not proof of future
programming energy or instantaneous detection of an arbitrary supply step**.
U9 supplies AON POR. U11 retains the cutoff state:

- `PRE_N = NOT(VBUS_OK AND AON_OK)`
- `CLR_N = AON_OK AND (CAP_OK OR VBUS_OK)`
- `RUN = Q AND AON_OK`

RUN drives both converter EN pins and has an external100k pulldown. Valid VBUS
can start an empty capacitor after POR. On VBUS removal the latch holds while the
loaded cap is valid. A loaded-cell trip clears it. Cap rebound alone cannot set it;
a new valid VBUS condition is required. If AON itself dies, POR prevents an
uncontrolled restart. The verifier checks16 stable-state combinations against the
**actual exported gate pin nets**. Propagation skew, asynchronous pin transitions,
comparator startup and all rail ramps remain physical qualification gates.

U16 supplies3.3V reset with a manual-reset input. S_RESET and factory reset pad
assert its **MR input**, not a short across its push-pull RESET output. U17/U18
combine RUN and reset-good with MCU requests to drive DMX_DE_SAFE and
DMX_POWER_EN. Request pulldowns and the existing DMX sheet's DE/EN defaults hold
both off during reset. RE_N has a pullup. A resident loader can use these same
interfaces without starting the main app or radio; that loader is not implemented.

| Condition | Implemented hardware response |
|---|---|
| No VBUS, previously armed, valid loaded cap | RUN stays enabled; VBUS_GOOD_3V3 low |
| Cap below threshold, no VBUS | RUN clears; rebound does not rearm |
| Cap alone after AON lost / never armed | POR holds RUN off; VBUS required to start |
| Default-current source, good VBUS and POR | Same normal domain enabled, bounded current,25mA charge |
|1.5A/3A advertisement | Same circuit/current limit; no increased draw |
| SERVICE held across reset | Separate service GPIO low; loader policy remains future software |
| USB host suspend with VBUS present | No USB communications function; PSD power behavior, not USB-device enumeration/suspend gating |
| AON brownout / initial rise | RUN low until valid POR/rearm conditions |

## Numerical corners and their limits

`../power_budget.py` reproduces the arithmetic in `../power-budget.json`.
TPS2553 equations include0.1% initial plus0.25% temperature resistance allowance:
**389.80–488.21mA**, plus0.14mA switch-current allowance gives488.35mA static VBUS
bound. Inrush/short-circuit response can have transients; this is not an inrush test.

At an assumed4.4V receptacle voltage,0.135Ω limiter and0.060Ω U19,
the worst static limiter-current drop leaves **4.3048V at NORMAL_IN**.
For1.1W main load and85% buck efficiency,30mA maximum cap charging at2.652V
with80% charge efficiency, plus2mA auxiliary allowance: calculated demand is
**325.72mA**, leaving **64.08mA** below the minimum limiter.
**Actual load and efficiencies are unmeasured assumptions**, including MCU/RF,
isolation and flash activity. Owner selected **2.4GHz plus US915MHz on the same
CC1352R radio**; this is not two independently simultaneous RF loads. Retain the
conservative1.1W assumption until the complete hardware is characterized.
The resistance allocations, operating temperature, startup and load peaks need
qualification; the TPS2116 resistance test uses200mA, not this complete load sweep.
If those assumptions fail, revise the load/charge setting; do not silently rely
on a1.5A source or typical limiter current. Small static bleed/control loads are
inside the auxiliary allowance; its full corner sum remains to be qualified.

Charge-current accuracy is±20% under TI's stated VIN=5V and SUP=0.8..4V
conditions; the series-diode/lower-input application needs verification. Voltage
accuracy±2% yields2.548–2.652V. Ideal charge time is**1560s (26min)** nominal;
with+30%C,+2%target and-20%current it is2585.7s before soft-start/termination
extra time. Slower charging is intentional. An incompletely charged cell cannot
provide the full ride-through target.

The unchanged U8 loaded-cell calculation adds reference initial error and
100ppm/°C drift over100°C,9mV offset, full8mV hysteresis, and conservative2.5mV
common-mode/3.7mV supply terms, giving **1.424–1.555V** loaded-cell trip.

For U10, use the TPS3700's **separately specified** rising396–404mV and
falling387–400mV limits (already incorporating hysteresis), ±25nA bias, and each
resistor's0.1% initial plus0.25% temperature allowance. The combined envelope is
**3.9625–4.1940V**, including falling retention of an already-high VBUS_OK.
The low4.4V source has110.8mV above the highest assertion threshold; a separately
allocated50mV sag still leaves60.8mV. The lowest valid input after that sag is
3.9125V. OSEL remains3.6V: TI's2% target plus150mV bypass threshold requires
3.822V; even a stricter3.5% full boost envelope plus150mV gives3.876V, leaving
**36.5mV after the50mV sag allocation**. This replaces the old12.1mV full-source
margin and the false-good case at VIN≈3.306V. Lowering OSEL would have reduced
buck headroom and was not selected.

At the qualified3.9125V floor the assumed load/charge/control demand is358.18mA,
still31.62mA below the minimum limiter. A **0.300Ω engineering allocation** for
U3's bypass switch gives BACKUP_RAW≥3.805V, **79mV above the conservative3.726V
output/charge-mode condition**, and395mV above the3.41V buck-input allocation.
Both VIN and loaded VOUT charge-mode conditions are asserted by the checks.
TPS61094 specifies bypass resistance as typical only; neither that
allocation nor TPS62132's low-input dropout resistance is a newly guaranteed
datasheet maximum. The minimum boost output3.528V leaves118mV against the same
3.41V allocation. Converter load-step/dropout/stability and thermal measurements
remain required. TPS2116 operation is specified to105°C, not125°C.

A cap-fed BACKUP_RAW≤3.726V cannot reach the lowest3.9625V qualifier threshold,
even conservatively assuming no intervening forward loss. Cap rebound therefore
cannot qualify an external source or rearm the cutoff latch. This is a static
electrical check; comparator/gate delays, arbitrary fast source steps, TPS2116
reverse transients and supply behavior below the AON operating range remain
unproved. TPS3700 has typical response delays, **no guaranteed maximum response
for this complete ramp/overdrive/load case**. Removing the input RC reduces a
known masking mechanism; it does not create instantaneous commit authority.

`corner-proof.py` independently enumerates32 detector and256 mode corners from
the **real exported netlist**, without importing the generator or budget script.
It also reproduces the old failure, checks buck/input headroom, and rejects a
budget that omits charge hysteresis. See `corner-proof.json` for actual results.

For runtime,15F×0.9 initial×0.7 aging=9.45F. The energy floor is now**1.7V** to
cover the high cutoff corner, assumed aged ESR/interconnect sag and transient
reserve; the earlier1.6V floor is historical. At80% combined efficiency, low
charge2.548V **minus100mV maximum recharge hysteresis**, the available starting
voltage is **2.448V**. At1.11W including supervision the estimate is **10.57s**,
only0.57s above10s. The corresponding total-load ceiling for10s is1.1728W;
combined conversion efficiency must remain at least75.71% with every other
assumption unchanged. This is insufficient evidence for a production guarantee.
The actual15F cell, charge voltage, housing and cutoff are unchanged. Nominal
15F/2.6V/1.5V floor at0.8W is33.83s at termination, or30.94s after typical75mV
recharge hysteresis. The10–30s objective is an unmeasured
target, not a mandatory upper shutdown time or guarantee for an entire transfer.

### Cold-cap startup: D-B remains an unmet acceptance gate

TPS61094 §7.3.2 precharges its32µF output reservoirs before latching its resistor
settings. Its table gives **ISS≥500mA at VIN=3.6V/VOUT=1.8V**, already above
TPS2553's488.21mA maximum limit; no ISS maximum or full-startup envelope is given.
RUN still enables both converters. U19's own soft start only addresses its output
reservoir ramp; it does **not** bound the later U3 output-precharge current.
The new higher source qualification threshold reduces the permissible input sag
before VBUS_OK can clear RUN when CAP_OK is false. Repeatable startup has not been
proved, and the better steady-state path must not be presented as its solution.

For scale only,11.1µF input storage loses a50mV allowance in about5.04µs with a
500mA demand and389.80mA limiter. This is **not a waveform prediction**: precharge
current/impedance, effective capacitance, source/limiter dynamics and converter
sequencing vary, and maximum precharge current is unknown. Eventual convergence
after repeated RUN cycles does not pass. Before acceptance, require either a
source-backed precharge/enable sequence with bounded current/timing or measured
single-attach startup over empty/partial/full cap, source/cable/load/temperature
corners, recording VBUS_RAW, LIMITED_5V, NORMAL_IN, BACKUP_RAW, VBUS_OK and RUN.
No commit signal is blanked or forced good to hide this gate.

## RDM update and factory service hardware

U2 is **AT25SF161B-MHB-T**,16Mbit (2MiB),2.7–3.6V SPI NOR,5×6mm DFN. CS has
the manufacturer's recommended10k pullup; WP/HOLD have pullups; SCK/MOSI have
pulldowns; supply decoupling is captured. The electrically unconnected thermal
pad is grounded as recommended. Single-SPI operation is selected. Staging,
rollback metadata, image validation and interrupted-write recovery are future
loader responsibilities, not capabilities proved by adding flash.

The CC1352R has352KB internal flash; two complete maximum-size internal images
are **not assumed**. External2MiB allows storage planning for candidate and prior
images plus metadata, subject to actual image sizes and a protected resident
loader layout. No memory partition, CCFG contents, signature keys or updater
implementation is invented here.

S_SERVICE connects `SERVICE_N_DISTINCT_GPIO`. This is **not** the old DIO3 ROM
backdoor. Holding a ROM-backdoor input could cause ROM UART/SPI entry before a
custom RDM loader runs. The GPIO assignment remains explicitly proposed/unmapped
until MCU pin-mux and factory CCFG capture; do not alias it to ROM_BOOT_STRAP.
J_FACTORY retains VREF sense, ground, TMSC, TCKC, supervisor MR request and the
separate ROM strap. Do not inject power through VREF or drive RESET_OK directly.
Factory cJTAG remains the rescue path if resident flash code is corrupt.

VBUS_GOOD_3V3 and BUCK_PG reach the MCU interface. The future loader must require
sustained good external power for commit; the hardware status alone does not
promise that VBUS will remain present. DE/RE control and isolated power are
available through the same app-independent hardware interface. Future service
mode must be a bounded UID responder, not an uncontrolled DMX transmitter.

### INPUT_FAULT_N interface proposal — not connected in this capture

The parent/Astra allocation reserves **DIO18, package pin28**. It remains NC
pending a coordinated power-off-safe interface. Existing INPUT_FAULT_N is U6's
open-drain output with100k pullup to AON_2V5; it must **not** be wired directly to
the3.3V MCU. CC1352R's digital absolute maximum is VDDS+0.3V, including analog
DIOs. With VDDS=0, an AON pullup can violate it; limiting possible clamp current
to roughly22µA using100k is not a voltage-rating waiver. Powered operation is
also not guaranteed: MCU VIH=0.8×VDDS=2.64V at3.3V exceeds the2.5V pullup.

Proposed contract for parent/Astra integration, **not yet populated or mapped**:

- Preserve INPUT_FAULT_N on the AON side, but use **10k** pullup for a future
  translator's ±5µA input leakage (100k can lose0.5V).
- **SN74LVC1G07DCKR**, powered from SYS_3V3 with100nF local bypass: pin1NC,
  pin2A=INPUT_FAULT_N, pin3GND, pin4Y=INPUT_FAULT_N_MCU, pin5VCC=SYS_3V3.
  This is a noninverting open-drain buffer with5.5V-tolerant input and Ioff.
- Pull INPUT_FAULT_N_MCU up to SYS_3V3 through2.2k1% and down to ground through
 15k1%, with25ppm/°C resistors and100°C allowance. At SYS_3V3=0 and Ioff=10µA,
  the pulldown bounds the node to151.9mV,
  below the300mV MCU limit. At a valid rail, the worst divider high is about
 0.870×VDDS before leakage, above0.8×VDDS; the low sink demand is under1.7mA
  versus a specified0.3V VOL at8mA/VCC=2.3V. Allowing an additional10µA sink
  still leaves over0.20V high margin at3.2V. System input leakage and power ramps
  must be verified; below the translator's1.65V minimum, the logic value is
  unspecified and must not grant programming permission.

The cached SN74LVC1G125 was also considered. Its partial-power-down behavior is
useful, but an open-drain output pulled solely from the MCU rail makes the voltage
translation/default contract easier to bound. The current exported sheet retains
the original100k AON pullup and **no MCU connection**; the above is a proposed
integration change, not an ERC-verified added circuit. Interface numbers in X_MCU
remain unchanged. Astra's SERVICE=DIO4/pin9 and ROM strap=DIO3/pin8 are distinct;
those actual package assignments live in `../mcu-radio/`, not this boundary symbol.

Parent verified ANSI E1.37-4–2026 publication/May20 approval on the
[ESTA published standards index](https://tsp.esta.org/tsp/documents/published_docs.php).
Its File Transfer Control is the intended protocol basis. Full clause/PID and
buffer conformance are deferred; neither ROM support nor manufacturer-specific
file transfer is assumed. For the single female fixture-output connector, service
requires disconnecting the fixture and a male-male straight-through adapter to a
bidirectional RDM controller. Never connect two active DMX controllers. Parent
owns the canonical service workflow and protocol decisions.

## Pin/source provenance

Sources were read from manufacturer datasheets. Printed page numbers are used.
The modern embedded symbols and independent verifier encode these physical pins;
`component-ledger.csv` is derived from the real KiCad netlist. MCU interface pin
numbers denote only the drawn boundary connector, **not CC1352 package GPIOs**.

| Part/source | Revision and physical-pin evidence |
|---|---|
| [TPS2553](https://www.ti.com/lit/ds/symlink/tps2553.pdf) | SLVS841F Aug2016 p4: DBV1IN/2GND/3EN/4FAULT/5ILIM/6OUT; p7 RON; pp18–20 limit equations/corners |
| [TPS2116](https://www.ti.com/lit/ds/symlink/tps2116.pdf) | Existing cached SLVSFG1A May2021 p3: DRL1GND/2VOUT/3VIN1/4PR1/5MODE/6VIN2/7VOUT/8ST; pp5–6 resistance/leakage/RCB; pp10–12 priority, startup and reverse behavior. Selected TPS2116DRLR replaces D_MAIN; finite reverse response remains a qualification gate. |
| [TPS3700](https://www.ti.com/lit/ds/symlink/tps3700.pdf) | New local cache SBVS187G Feb2019 p4: DDC1OUTA/2GND/3INA+/4INB−/5VDD/6OUTB; p6 separate396–404mV rising/387–400mV falling thresholds and25nA bias; p7 typical propagation. Selected TPS3700DDCR replaces U10. |
| [TPS61094](https://www.ti.com/lit/ds/symlink/tps61094.pdf) | SLVSFH6C Dec2021 p3 pins1OSEL/2MODE/3EN/4VIN/5SW/6SUP/7PGND/8AGND/9–10VOUT/11ICHG/12VCHG; mechanical EP13; pp6,11–12,16,23,30 tolerances/codes/modes/inductor/layout |
| [TPS62132](https://www.ti.com/lit/ds/symlink/tps62130.pdf) | SLVSAG7F Nov2021 p3 fixed3.3V variant:1–3SW/4PG/5FB/6AGND/7FSW/8DEF/9SS/10AVIN/11–12PVIN/13EN/14VOS/15–16PGND/EP17; pp14–17 passives |
| [TPS7A02](https://www.ti.com/lit/ds/symlink/tps7a02.pdf) | SBVS277C Sep2022 p3 DBV1IN/2GND/3EN/4NC/5OUT; pp6–7 accuracy/dropout; selected TPS7A0225PDBVR |
| [TLV3012B](https://www.ti.com/lit/ds/symlink/tlv3012.pdf) | SBOS300C Apr2023 pin diagram and §6.9: DCK1OUT/2V−/3IN+/4IN−/5REF/6V+; **TLV3012BIDCKR**, not a fabricated no-I order code |
| [TPS3839/TPS3831](https://www.ti.com/lit/ds/symlink/tps3839.pdf) | SBVS193D Jul2015 pp4–7: G25DBZ1GND/2RESET/3VDD; K33DQN1RESET/2MR/3GND/4VDD, local EP5; thresholds and reset delay |
| [SN74LVC1G74](https://www.ti.com/lit/ds/symlink/sn74lvc1g74.pdf) | SCES794G Sep2021 p4 DCU1CLK/2D/**3Q_N**/4GND/**5Q**/6CLR_N/7PRE_N/8VCC |
| [SN74LVC2G08](https://www.ti.com/lit/ds/symlink/sn74lvc2g08.pdf) | SCES198N Dec2015 p3 DCU1,2→7 AND;5,6→3 AND;4GND/8VCC |
| [SN74LVC2G32](https://www.ti.com/lit/ds/symlink/sn74lvc2g32.pdf) | SCES201N Sep2015 p3 same DCU pin positions, OR function |
| [SN74LVC1G04](https://www.ti.com/lit/ds/symlink/sn74lvc1g04.pdf) | SCES214AF Oct2025 p3 DCK1NC/2A/3GND/4Y/5VCC |
| [AT25SF161B](https://www.renesas.com/document/dst/at25sf161b-datasheet) | DS-AT25SF161B-188 RevH Sep19,2024 pp7–8:1CS/2SO/3WP/4GND/5SI/6SCK/7HOLD/8VCC; p56 MHB-T ordering; p59 max5.10×6.10×0.60, EP not electrically connected and recommended grounded |
| [PMEG2010ER](https://assets.nexperia.com/documents/data-sheet/PMEG2010ER.pdf), [BAT54H](https://assets.nexperia.com/documents/data-sheet/BAT54H.pdf) | Jul1,2023 / Oct8,2024; pin1 cathode/pin2 anode, SOD123W/F; reverse leakage remains nonzero |
| [Coilcraft XFL4020](https://www.coilcraft.com/en-us/products/power/shielded-inductors/molded-inductor/xfl/xfl4020/), [XGL4020](https://www.coilcraft.com/en-us/products/power/shielded-inductors/molded-inductor/xgl/xgl4020/) | 2.2µH,20%,4×4×2.1 allocations; XGL recommended in TPS61094 Table8-2, XFL in TPS62132 table; C reel suffix |
| [CC1352R](https://www.ti.com/lit/ds/symlink/cc1352r.pdf) | SWRS196I Feb2021 pp1–3:352KB internal flash, cJTAG, UART/SSI and7×7 RGZ; pp11,45 digital pin voltage and VIH; MCU pinout not newly assigned here |
| [SN74LVC1G07](https://www.ti.com/lit/ds/symlink/sn74lvc1g07.pdf) | New local cache SCES296AG Oct2025 pp3,5–6: proposed DCK pinout,5.5V-tolerant input,2V VIH at3–3.6V, ±5µA input leakage,10µA Ioff at VCC=0 and low-drive limits. Proposed only, not in exported sheet. |
| [TI serial bootloader note](https://www.ti.com/lit/an/swra466e/swra466e.pdf) | Parent-verified SWRA466E UART/SPI ROM bootloader basis; this pass's direct web retrieval failed; no ROM RDM claim |

The power flags on AON_RAW, CAP_POS and SYS_3V3 describe implemented
passive-derived rails through diodes/inductors/storage. NORMAL_IN is now driven
by U19; its former power flag is removed. The remaining flags do not supply an
unimplemented control. Duplicate internally common output contacts are modeled
with one power-output pin and passive duplicates to avoid false driver conflicts;
IC controls retain input/output/open-drain types. No ERC exclusions are used.

## Physical result and release gates

The sidecar stays**98×34×24mm**. D06 is now the actual selected flash's maximum
5.10×6.10×0.60 envelope atx52,y40,z11; the former bridge envelope is removed.
The flash body occupies31.11mm² rather than the bridge's nominal9mm², so bridge
removal alone is not a defensible shrink. WLCSP was investigated, but its
manufacturing/land-pattern integration was not closed; the sourced DFN is retained.

The28.4mm capacitor length/13.5mm diameter,18×30 antenna keepout, intact NC5FRX,
MCU/RF allocation and isolation package remain major constraints. The25×6 power
reservation is explicitly **not proof that the complete capture fits**. Individual
IC/inductor/passive footprints, underside placement, capacitor cradle and routing
must be solved before shrinking. No speculative smaller STEP is supplied.

The parent's barrel stop passage, window position, B19 sleeve and lowered USB
board/connector remain unchanged. New CAD checks still assess only modeled
solids/allocations, not a routed PCB or complete manufacturing fit.

Remaining gates: physical load/current/inrush and cold-start characterization;
charger accuracy off TI's test conditions; cutoff/POR/asynchronous transient tests;
converter stability/dropout/EMI and effective capacitance; complete MCU/RF/TVS/
termination capture; actual PCB footprints/routing and DRC; source/USB/ESD and
thermal qualification; service button mechanics; factory CCFG/pin-mux and loader
protection/security/rollback implementation; cross-manufacturer fixture fit;
barrel mains assembly and dynamic-wire qualification. No firmware implementation,
programming, hardware access, manufacturing release or certification occurred.
