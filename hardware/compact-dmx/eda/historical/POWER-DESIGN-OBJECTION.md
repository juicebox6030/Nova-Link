# Power capture: design objection and recovery candidate, 2026-10-22

**The requested complete power/UVLO/recovery capture is NOT accepted or finished.**
The existing real-KiCad DMX sheet is preserved. The new `recovery-candidate/`
contains an editable, electrically typed **USB recovery candidate only**, actual
CLI exports and a separate connection verifier. It is not a replacement product
schematic. No omitted normal-power control is represented by a power flag or a
fictional completed control block. No PCB, firmware, hardware test or programming
was performed. Parent owns canonical design/BOM/CAD integration.

## Demonstrated objections to the previous proposed parts

1. **TUSB320LAI cannot establish the required continuously valid, hardware-only
   high-current permission.** TI SLLSEQ8D, section 7.2.1.2, printed p10 says the
   current report occurs once in Attached.SNK. Do not retain its indication across
   a possible source-current downgrade and treat it as fresh permission.
   Concrete replacement candidate: STUSB4500LQTR, standalone 5V sink, separate
   active-low RP_1A5/RP_3A outputs and VBUS_EN_SNK. DS13102 Rev6 p4 establishes
   those physical outputs. Dynamic downgrade timing, reset/output defaults,
   discharge network and total current must be closed from the full application
   documentation before releasing that replacement. It is **not captured here**.
2. **TPS2553 with ILIM shorted to IN does not impose a 100mA whole-device ceiling.**
   SLVS841F Table2 p20 permits 100mA at OUT before adding its own input current,
   CC/controller and other raw-VBUS loads. The old setting therefore fails a
   worst-case pre-enumeration budget even before considering startup.
3. **TPS22950 is not an ideal blocking diode while enabled.** SLVSFJ2B §9.3.4 p14
   describes a roughly 900mA reverse-current threshold followed by a response
   delay. It must not be the sole isolation between buffered power and VBUS.
   Its 19.2k setting is 34–66mA, not a guaranteed 50mA available supply. Only the
   original WCSP TPS22950 supports this setting; C/L substitutions are invalid.
4. **A guaranteed pre-enumeration MCU+bridge boot budget is not established.**
   CP2102N Rev1.5 Table3.2 p10 supplies typical active/suspend currents, not maximum
   active/suspend bounds. A low input limiter bounds draw but does not establish
   successful ROM boot or enumeration. Neither typical current nor the absence
   of ERC errors proves operation. This candidate instead powers the bridge first
   and gates a separate recovery branch after USB configuration.

## Captured alternative and safe default

U101 TPS22950YBHR (19.2k, 0.1%) feeds only the bridge domain. U102 TPS70933DBVR
regulates that branch to 3.3V; CP2102N VDD and VREGIN are both connected to this
external 3.3V supply, as allowed by Rev1.5 Table3.6 note1 p12. This avoids exposing
its 5.25V recommended VREGIN maximum to a nominal 5V source reaching 5.5V.
Its VBUS sense is the bus-derived BRIDGE_3V3, not a direct 5V input. Detach decay,
USB data/ESD, rail discharge and USB compliance still require qualification.

U103 pin11 SUSPENDb is USB_ACTIVE. A 10k pulldown implements the manufacturer's
reset recommendation (Rev1.5 §4.1 p17). U106 implements:

`REC_EN = USB_ACTIVE AND REC_REQUEST AND CONFIG_VERIFIED`

S101 is the physical request switch. **S102 is an OPEN/DNP factory qualification
link**, with R109 holding CONFIG_VERIFIED low. As captured, the MCU recovery rail
cannot turn on. The link must remain open until a bus-powered 500mA descriptor,
BOOT/reset sequencing and the pending integration checks below are qualified.
Merely enumerating a factory-default 100mA bridge must never enable this branch.
Descriptor configuration is a manufacturing requirement, not programming done here.

U104 TPS2553DBVR, R102=88.7k 1%, imposes a 262.1–342.3mA current-limit range.
U105 TPS70933DBVR supplies REC_3V3. This is a protection limit, not a 300mA LDO
load rating: TPS709 is a 150mA regulator; intended ROM recovery load allocation
is **at most 50mA**, subject to measurement. Its 650mV maximum dropout at 50mA
requires adequate input voltage after U104, including cable/transient losses.
Do not join REC_3V3 directly to buffered MCU power. TPS709 §7.3.4 explicitly
allows reverse current under some sub-1.8V output conditions; it alone does not
close the all-voltage backfeed requirement. A separately qualified dual-input
reverse-blocking merger (TPS2116 is a candidate) remains necessary.

U107/U108 SN74LVC1G125DCKR receive power from the **receiving** domain:
MCU TX → U107 (BRIDGE_3V3) → bridge RX; bridge TX → U108 (actual MCU_3V3) → MCU RX.
Their input tolerance and Ioff specification address a powered transmitter with
an unpowered receiver; Ioff is bounded leakage, not mathematically zero current.
No raw MCU TX wire enters the unpowered CP2102N. The local 100k input pulldowns
avoid floating inputs if the sending domain disappears. This does not establish
all other product-domain crossings. The MCU boundary intentionally keeps
MCU_3V3 and REC_3V3 distinct: **no unimplemented merger is hidden in a net label**.

## Budget and state evidence

Run `python3 hardware/compact-dmx/eda/power_budget.py`. Its JSON records every
required state and whether it is actually implemented. It is engineering
arithmetic, not firmware simulation or measured hardware validation.

- Bridge limiter: 34–66mA datasheet range; approximately 33.96–66.07mA after an
  additional 0.1% resistor allowance using the manufacturer's exponent. This
  interpolation is an estimate, not an additional manufacturer guarantee.
- With a provisional 5mA raw CC/logic allowance and 0.3mA switch overhead:
  pre-enumeration allocation ≈71.37mA; post-enumeration allocation ≈413.67mA.
  The CC/logic allowance is **not closed**, and current-limit response/inrush
  still need assessment. These figures do not establish USB compliance.
- USB suspend: U104 and U105 turn off through SUSPENDb. Bridge typical suspend
  current is insufficient to establish a whole-device maximum. Maximum CC,
  regulator, pullup, leakage and bridge consumption remain a release gate.
- Recovery request must disable normal radio/DMX/charging and force ROM-loader
  BOOT before releasing MCU reset. Those product gates are **not implemented**
  by this candidate. Preserve CC1352 cJTAG and physical reset/boot access.

## Corrected buffer settings for the next power capture

TI TPS61094 SLVSFH6C p3 and Tables7-1/2/3 pp11–12 establish:

| Pin | Function | Intended connection/value |
|---|---|---|
| 1 | OSEL | 17.4k to GND → 3.6V boost |
| 2 | MODE | Must remain high for true shutdown when EN=0 |
| 3 | EN | Independent latched cutoff / qualified rearm, not an MCU-only decision |
| 4 | VIN | Reverse-blocked normal 5V path only; never default-PC recovery feed |
| 5 | SW | 2.2µH candidate inductor to cap/SUP node |
| 6 | SUP | 15F positive terminal and inductor |
| 7,8 | PGND, AGND | GND_USB, layout-separated current returns joined per TI |
| 9,10 | VOUT | Backup rail into downstream buck |
| 11 | ICHG | 75.0k to GND → 250mA nominal |
| 12 | VCHG | 9.53k to GND → 2.6V nominal |

EN=0/MODE=0 is **forced bypass**, not shutdown; TI §7.4.1 p16 explicitly warns
that this mode does not protect against output-to-input reverse current.
TI gives ±2% charge voltage and ±20% charge current (p6): 2.548–2.652V and
200–300mA under the stated test conditions. Values outside those conditions
must not inherit an invented guarantee. Specify programming resistors within
TI's required tolerance and qualify ADC bin margins.

TPS62132RGT is the fixed 3.3V variant (SLVSAG7F p3): SW1/2/3→inductor;
PG4 open drain; FB5→AGND; AGND6; FSW7 low for nominal 2.5MHz; DEF8 low;
SS/TR9 requires capacitor; AVIN10/PVIN11/12→backup rail; EN13→hardware gate;
VOS14→regulated output; PGND15/16 and exposed pad→GND. Inductor, effective
output capacitance, soft start, dropout/transients and layout are not released.

For 15F, the existing 0.9 initial-capacitance and 0.7 aging factors give 9.45F.
At assumed 80% conversion efficiency: nominal energy with a 1.5V floor is
27.06J (33.83s at0.8W); aged energy with a 1.6V floor including sag reserve is
15.876J, giving aged runtime 14.43s at1.1W. Including the -2%
charge-voltage corner reduces this to **13.51s**. These remain estimates.
Nominal ideal charge time is156s; with +30% C, +2% target voltage and -20%
current it becomes258.57s **before termination/taper overhead**. The 10–30s
objective is a target, not measured evidence or a required upper shutdown time.

A TLV3012B 20k/100k 0.1% divider is a candidate nominal 1.4904V loaded-cell
comparator. The script includes reference tolerance/drift, offset, hysteresis
and conservative extra error terms; its estimated envelope is approximately
1.42–1.56V. It is **not a captured or verified UVLO circuit**. Its supply must
remain valid through cutoff; cap-rebound must not rearm; USB default current
must not clear the latch into normal operation; power-on must force an off state.
A POR-qualified latch powered from isolated always-on power, rearmed only by
fresh valid ≥1.5A permission, is the proposed next circuit—not an existing fact.

## Sources and pin provenance

All page numbers below are printed PDF page numbers. Datasheets fetched during
this pass are locally cached under ignored `source-cache/`; vendor PDFs are not
included as distributable design sources.

| Manufacturer primary source | Revision / evidence |
|---|---|
| [TI TUSB320LAI](https://www.ti.com/lit/ds/symlink/tusb320lai.pdf) | SLLSEQ8D May2017, p10 §7.2.1.2 current-report limitation |
| [ST STUSB4500L](https://www.st.com.cn/resource/en/datasheet/stusb4500l.pdf) | DS13102 Rev6 Feb2022, pp1,4,5 standalone sink, QFN24 pin map; www.st.com fetch timed out, official .com.cn copy inspected |
| [TI TPS22950](https://www.ti.com/lit/ds/symlink/tps22950.pdf) | SLVSFJ2B Feb2023, p4 WCSP A1 ON/A2 FLT/B1 VIN/B2 VOUT/C1 GND/C2 ILIM; p6 current bounds; p14 reverse-current mechanism |
| [TI TPS2553](https://www.ti.com/lit/ds/symlink/tps2553.pdf) | SLVS841F Aug2016, p4 DBV1 IN/2 GND/3 EN/4 FAULT/5 ILIM/6 OUT; p20 Table2 resistor/current corners |
| [TI TPS709](https://www.ti.com/lit/ds/symlink/tps709.pdf) | SBVS186H Jul2021, p3 **base** DBV pin map (not A/B variants); p5 electrical bounds; §7.3.4 reverse-current caveat |
| [Silicon Labs CP2102N](https://www.silabs.com/documents/public/data-sheets/cp2102n-datasheet.pdf) | Rev1.5, pp10,12,17 current/regulator/suspend; pp31–32 QFN20 pin map including EP ground; EP numbered21 in local symbol |
| [TI SN74LVC1G125](https://www.ti.com/lit/ds/symlink/sn74lvc1g125.pdf) | SCES223U Aug2026, p3 DCK1 OE_N/2 A/3 GND/4 Y/5 VCC; electrical Ioff ±10µA at VCC=0 and5.5V input/output |
| [TI SN74LVC2G08](https://www.ti.com/lit/ds/symlink/sn74lvc2g08.pdf) | SCES198N Dec2015, p3 DCU1/2→7 AND, 5/6→3 AND, 4GND/8VCC |
| [TI TPS61094](https://www.ti.com/lit/ds/symlink/tps61094.pdf) | SLVSFH6C Dec2021, pp3,6,11–12,16,22–23 pin map/tolerances/programming/modes/magnetics |
| [TI TPS62132](https://www.ti.com/lit/ds/symlink/tps62130.pdf) | SLVSAG7F Nov2021, p3 fixed-version selection and complete pin map |
| [TI TLV3012B](https://www.ti.com/lit/ds/symlink/tlv3012.pdf) | SBOS300C Apr2023, §6.9 B-version reference/offset/drift/hysteresis bounds |
| [TI TPS2116](https://www.ti.com/lit/ds/symlink/tps2116.pdf) | SLVSFG1A May2021, p3 candidate dual-input merger pin map; not selected/captured |
| [Eaton HV cells](https://www.eaton.com/content/dam/eaton/products/electronic-components/resources/data-sheet/eaton-hv-supercapacitors-cylindrical-cells-data-sheet.pdf) | Canonical selected HV1325-2R7156-R15F; parent owns cell/BOM/mechanical integration |

## Physical impact and next bounded implementation

No claim that the existing25×6mm power allocation fits. The recovery candidate
alone has8 ICs,9 resistors,10 capacitors and2 switch/link functions, excluding
connector boundaries. TPS709 DBV bodies and courtyards, the CP3×3mm QFN and its
land/decoupling area, routing and isolation of domains need actual placement.
Adding two converters, two inductors, CC controller, latch/comparator/POR and
power merger makes the original allocation unsupported. No new bounding box or
mechanical shrink is invented; parent must allocate and route the complete set.

Next: close standalone CC dynamic behavior, select the all-voltage reverse-
blocking topology, then capture normal-path/charger/latch/POR and BOOT/reset
sequencing together. Integrate the recovery candidate only after that work.
The factory link must remain open until those checks and USB descriptor/current
qualification pass. No full-power ERC pass, physical fit, USB compliance,
recovery success, radio operation or manufacturing release is claimed here.
