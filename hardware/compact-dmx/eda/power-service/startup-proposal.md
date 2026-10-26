# D-B startup decision — two bounded hardware candidates

**Proposal, not a new captured circuit or a manufacturing release.** The previous
power review receipt and active 25mA capture are unchanged. No guaranteed 500mA
fix was established in this bounded pass. Recommend evaluating **path 2's separated
power architecture**, subject to the parent's explicit source-compatibility
selection and the gates below. Merely changing R_ILIM is not a D-B solution.

The owner's requirements are USB-C **power only**, a 5V/1.5A barrel source,
CC1352R shared 2.4GHz/US915MHz radio, isolated DMX/RDM and a 15F cell targeting
10–30s ride-through. **500mA/default-current compatibility was our engineering
choice, not an explicit owner requirement.** No 1.5A-only constraint is selected
by this proposal. CC current detection needs no USB data, enumeration, PD policy,
MCU firmware, ESP or USB communications function.

Evidence is the original cached TI PDFs plus the three new official PDFs in
`startup-source-cache/`; hashes and supporting pages are in
`startup-source-manifest.json`. `startup-analysis.py` computes the numbers and
tests the proposed state invariants. It does not simulate or prove a circuit.

## 1. Retain 500mA and TPS61094: external precharge plus separate enables

This is a concrete **candidate requiring source clarification**, not a qualified
drop-in repair. A fixed time that ignores VBUS sag cannot solve D-B. Nor can
raising the current limit to 1.5A prove an unspecified ISS maximum.

Proposed power and control changes:

- Keep U6/TPS2553 at 60.4k and U19's present low-loss barrier. Their main-current
  limit remains 389.80–488.21mA. Keep the 15F cell and 25mA charge setting.
- Add a **TPS2553DBVR** precharge branch from NORMAL_IN to BACKUP_RAW with
  **210k 0.1%,25ppm/°C R_ILIM**. Its equations give about 109–152mA DC limits.
  Precharge only the output reservoirs while U3 is in true shutdown and U4 is
  disabled. The 15F cell is not on this precharge output node.
- Add a **TPS259474LRPWR** reverse-blocking switched bypass from NORMAL_IN to
  BACKUP_RAW. This supplies the main rail after precharge; its PG must confirm
  completed gate turn-on before the buck can start. Its circuit-breaker/current
  setting is **not** a replacement for U6's 500mA bound. Choose ILM above normal
  demand, coordinate its fault action with U6, and define PGTH/ITIMER/OVLO before
  capture. Avoid relying on typical dVdt as a guaranteed slope.
- A **TPS3808G01DBVR** voltage-qualified precharge supervisor, CT open, provides
  a specified 12–28ms release interval **after** BACKUP_RAW reaches its selected
  threshold. It only sequences internal power switches; it must not blank,
  delay-falsify or force the external-power/commit indication good.
- Move the USB source of AON_RAW upstream to **VBUS_RAW**, retaining a physical
  reverse barrier and the BACKUP_RAW AON input. Account for every upstream load
  separately from U6. Startup control must not lose its supply when LIMITED_5V
  sags, and U3 enable must not simply be cleared by that same sag. The existing
  488.21mA main maximum plus0.14mA switch current leaves only11.65mA for all
  raw-side loads within500mA; that sum, including a failed start, must be bounded.
- Split `CONVERTER_EN`, `BUCK_EN`, `PRECHARGE_EN`, `MAIN_BYPASS_EN` and the
  existing source/cap status. Keep CAP_UVLO and its non-rearming latch active.
  The existing MCU/DMX boundary nets would remain unchanged.

Candidate sequence: POR holds both converters and main bypass off; valid external
power starts the bounded precharge branch; measured BACKUP_RAW voltage plus the
supervisor release enables the reverse-blocking main bypass; bypass PG enables
the buck and allows U3's externally prebiased startup; source/cap status remains
real throughout. On external-source loss, remove both external precharge/bypass
paths; only a previously armed, valid cap may sustain the domain. Cap rebound
alone cannot rearm it. A failed precharge never grants commit status.

The 55µF upper effective-capacitance **allocation** charges to 5.5V in about 2.8ms
at the precharge switch's minimum current, after subtracting 2mA load. Adding
TPS2553's 3ms turn-on maximum is below the supervisor's 12ms minimum. This is a
useful scale check, **not a full ramp bound**: the final tail depends on switch
resistance, cap leakage, effective C and the selected threshold. The bypass's
own PG, rather than an assumed turn-on time, must qualify the load handoff.

Why this is not implemented:

1. TPS61094 §7.3.2 does **not explicitly guarantee externally prebiased EN/MODE
   handoff**, its input current, or a maximum configuration interval. Table 7-4
   and the forced-bypass description do not supply a guaranteed transition
   waveform. A supported external precharge sequence needs TI confirmation.
2. Its bypass FET resistance is typical only. External bypass supplies the USB
   load independently, but cap charge/backup readiness after the U3 transition
   still needs a supported bound. Do not disguise that uncertainty with a timer.
3. TPS2553's current-limit equations are DC bounds, not peak hot-plug limits.
   Sequencer fault recovery, branch reverse leakage, cap tail, SOA and transient
   current must be closed. Raw-AON current and input inrush need a full sum.

The added IC bodies alone are roughly **13.3 mm²**:4.64 for the secondTPS2553,
4 forTPS259474 and 4.64 forTPS3808, before controls, caps, resistors, courtyards
and routing. This erodes the compactness benefit of retaining the integrated U3.
No claim is made that these parts fit the existing 25×6 power reservation.

## 2. Source-qualified 1.5A alternative: separate charger and cap-only boost

This removes the TPS61094 precharge mechanism from USB startup. It is **not**
the same converter with a larger input limit. The USB main path powers the buck
directly through a source-priority mux; the cap charger is a separately limited
branch; a separate boost converter starts from the 15F cell while USB still powers
the application. An empty or failed cap branch cannot starve the main rail under
the stated current allocations.

Proposed parts and net changes, none yet populated:

- **TUSB320LAIRWBR**,1.6×1.6mm: CC1/pin 1 and CC2/pin 2 go to the receptacle;
  remove the two external 5.1k Rd resistors because this controller supplies Rd.
  PORT/pin 3=GND for sink; ADDR/pin 5=NC for hardware GPIO mode; EN_N/pin 11=GND;
  VBUS_DET/pin 4 connects to VBUS_RAW through the specified-range 887k 0.1% resistor;
  OUT1/pin 7, OUT2/pin 8 and OUT3/pin 6 get pullups to its own supply; ID/pin 9=NC,
  GND/pin 10=ground and VDD/pin 12=CC_3V3. EP/footprint grounding follows the
  manufacturer's package drawing, not an invented signal pin.
- **TPS70933DBVR**,2.9×1.6mm, supplies CC_3V3 from VBUS_RAW, with its required
  capacitors. The detector's recommended VDD maximum is 5V; direct connection to
  a possibly 5.5V VBUS is not justified. Existing AON_2V5 is below its 2.7V minimum.
  Reject TUSB321AI for this low-source basis: its 4.5V VDD minimum is above the
  assumed 4.4V receptacle corner. Reuse the existing **TPS3831K33DQNR** type for
  an independent CC-supply POR if appropriate; its MR ties to CC_3V3.
  TUSB320LAI is rated only −40 to 85°C ambient and requires VDD to ramp within
  25ms. These are new design constraints to qualify, not inherited 125°C limits.
- Hardware decode of TUSB320 GPIO Table 3: OUT1/OUT2=HH is unattached default;
  HL is attached default; LH is 1.5A; LL is 3A. Thus `NOT OUT1` accepts 1.5A/3A,
  additionally gated by OUT3 high (no audio accessory), CC POR and real raw-VBUS
  UV qualification. All pullups stay on CC_3V3. The main input-switch EN has a
  physical pulldown and remains off during POR/default/unattached states.
- Keep main **TPS2553DBVR** but propose **22.1k 0.1%,25ppm/°C R_ILIM**, giving
  **1.0826–1.2562A** DC limits. An upstream AON/CC/LDO/control **10mA allocation**
  plus 0.14mA switch allowance makes 1.2663A, leaving 233.7mA below 1.5A. The 10mA
  sum and all transient excursions still require qualification.
- Repurpose **U19 TPS2116DRLR** as a true two-source mux: VIN1/pin 3=LIMITED_5V,
  VIN2/pin 6=BOOST_3V6, VOUT/pins 2,7=BACKUP_RAW, GND/pin 1=ground. MODE/pin 5
  is a valid always-on logic rail for manual control; PR1/pin 4 selects USB only
  while it is source-qualified. ST/pin 8 is diagnostic only: it is **not** proof
  of valid output or completed precharge. Qualify actual BACKUP_RAW separately.
- Remove U3/TPS61094 and its OSEL/ICHG/VCHG programming resistors. Add
  **BQ25173DSGR**,2×2mm: pin 1=CHG_IN, pin 2=ISET via 3.00k 0.1% to ground,
  pin 3=CHARGE_DISABLE (active-high disable, external pullup required), pin 4=GND,
  pin 5=STAT, pin 6=PG, pin 7=FB and pin 8=CAP_POS; thermal pad=ground. Use at least
 1µF at IN and a 2.6V nominal FB divider, initially 22.5k/10k 0.1%,25ppm/°C.
  Final FB/input-bias corners remain a source gate. Neither PG nor STAT is a
  replacement for actual external-source status, CAP_UVLO or full-charge policy.
- Feed CHG_IN through a second **TPS2553DBVR**,210k R_ILIM, enabled only after
  source qualification and actual buck PG. Its approximately 152mA maximum DC
  branch limit bounds empty-cap/charger demand independently of the 100mA charge
  setting. This branch remains disabled during main cold start.
- Add **TPS61023DRLR**,1.2×1.6mm: pin 1=FB, pin 2=CAP_BOOST_EN, pin 3=CAP_POS,
  pin 4=ground, pin 5=boost inductor switching node, pin 6=BOOST_3V6. Use a new
  datasheet-qualified 1µH inductor and local 4.7µF input/10µF output effective
  capacitance; do not silently reuse the present inductor rating. A candidate
  nominal divider 499k/100k with 595mV reference gives 3.564V. Feedback bias,
  PFM upper limit, current limit at low input, magnetics and mux voltage range
  must close before selecting final values.
- USB-AON comes from **VBUS_RAW**, upstream of main current limiting. Backup-AON
  comes from BOOST_3V6. Converter EN is a dedicated cap-arm latch, separate from
  buck EN and source status. U8's loaded-cap UVLO remains independently active.
  An additional cap-start threshold around 2.2V, with tolerance checked above the
  boost's 1.8V start requirement, permits initial boost enable only with a valid
  source. Use the previously unused half of TPS3700 if its polarity and complete
  source qualification permit; otherwise add a sourced comparator. Once armed,
  it stays enabled below 2.2V until loaded-cap cutoff; source-free rebound cannot
  rearm it. BOOST_READY must be an actual voltage comparator, not a 700µs timer.
- Keep TPS62132 and propose 100nF SS instead of 3.3nF. With 80nF minimum and
 2.7µA maximum SS current, the 1.25V ramp equation gives at least 37.0ms. A44µF
  upper output-capacitance **allocation** then represents at most 3.92mA of
  output-cap charging. This is not a guaranteed instantaneous input-current bound.
  Main-path bulk precharge, TPS2116 collapse/softstart behavior and actual MCU
  startup load remain explicit validation gates.

The hardware states must be:

- **No qualified source / never armed:** main input, charger, boost and buck off.
- **Qualified 1.5A source, empty cap:** always-on control is already powered;
  main input starts; actual main-rail voltage enables the buck with its controlled
  soft start. The charger stays disabled until buck PG. The future RDM loader can
  run from USB without waiting for the cell to charge or a boost-start timer.
- **Buck PG, valid source:** enable only the limited charger branch. With the
  current allocations, even its full branch limit leaves about 610mA below the
  main limiter's **minimum**, independent of the charger current loop's startup.
- **Cap-start threshold reached:** set CAP_ARM and start the cap-fed booster;
  keep the mux on USB while the booster starts. Its unspecified precharge current
  is drawn from the 15F cap, **not from the USB main path**. A boost failure must
  leave BOOST_READY false without resetting the USB-powered application.
- **Source loss or advertisement downgrade:** immediately remove SOURCE_ALLOW,
  disable input and charging, clear external commit status, and use the mux's cap
  input only if previously armed, loaded cap valid and BOOST_READY true. Otherwise
  power down. CAP_UVLO clears CAP_ARM; rebound cannot rearm it without a new
  qualified source. Finite comparator/mux/CC delays still require transient tests.

For USB-side UV qualification, propose the existing TPS3700 INA+ with
**89.8k/10k 0.1%,25ppm/°C**, sensing LIMITED_5V before the mux. Do not inherit the
present 93.1k divider after changing topology/current limit. Enumeration gives
rising max about 4.060V and falling min about 3.836V, including resistor allowance,
±25nA bias and specified hysteresis. The allocated 4.155V main floor exceeds the
rising threshold by about 96mV. Subtracting 50mV sag and a full 1.2562A×60mΩ mux
drop from the falling threshold leaves about 3.710V for the buck, above the 3.41V
allocation. These are static calculations, not a load-step or buck dropout
 guarantee. The60mΩ mux limit is specified at200mA and3.3V/5V; applying it at
 the full1.256A limiter corner is an allocation requiring confirmation. Input
 path resistance at low source voltage and full current remains a source gate.
The raw-VBUS detector threshold and complete startup POR chain remain to select.

External-source status remains `SOURCE_ALLOW AND USB_UV_OK AND BUCK_PG`, gated
with valid AON/reset levels as appropriate. Sense USB_UV on the USB side of the
mux, not only BACKUP_RAW where cap energy could mimic an external source. Do not
blank this signal during startup or faults. It remains insufficient authorization
for a future loader to commit an image without its stability/integrity policy.

Current and recharge tradeoffs:

-100mA nominal BQ charging uses 3.00k; KISET and resistor corners give
 89.69–110.39mA. Ideal 15F/2.6V recharge is 390s (**6.5min**). With+30%C,
 2.65V design ceiling and minimum current it is about 576s (**9.6min**) before
 CV tail, thermal regulation and off-condition accuracy. These are estimates.
- A linear charger dissipates up to roughly **0.607W** at 5.5V/empty cap and
 110.39mA. JEDEC75.2°C/W suggests 45.7°C rise, so an 85°C ambient already reaches
 thermal-regulation territory. The enclosure and copper may be worse. Faster
 recharge is not guaranteed by changing the source label to 1.5A.
- Retain the actual 15F cell and conservative 2.448V runtime start allocation until
 the new charger/boost/UVLO/ESR corners are closed. Do not automatically reclaim
 the old 100mV hysteresis reserve or inherit the old 80% efficiency as measured.
- Added primary IC bodies, net of removing the 6mm² TPS61094 body, are about
 **11.8 mm²** for BQ25173, TPS61023, TUSB320LAI, TPS709 and the branch TPS2553,
 before CC POR, comparators/latches/gates, extra caps, inductor rating changes,
 courtyards and routing. No housing or PCB fit claim follows from body area.

This product selection would reject default-current and legacy USB sources for
normal operation. A3A source would be accepted with the same≤1.5A circuit draw.
The owner-stated 5V/1.5A barrel supply also needs **correct source-side CC current
advertisement and attach behavior**; PSU wattage alone does not advertise 1.5A.
Parent owns barrel circuitry, BOM, CAD, canonical decisions and this compatibility
choice. No barrel changes are made here.

## What closes the proposal

For path 1, obtain TI's supported prebiased TPS61094 sequence and transition bounds
before capture. There is no known source-backed shortcut in the retained circuit.

For path 2, first select the source contract, then complete the new power capture
and independent pin/net/passive verification. Specifically obtain/verify:

1. TPS61023 low-input switch-current capability at 1.7V/3.6V, PFM upper-output
   bound against the mux's 5.5V recommended limit, startup rail sag and actual
   BOOST_READY behavior. Its 2.7A minimum valley limit is tabulated at 3.6V/5V;
   extrapolation is not a guaranteed low-input limit. TPS61099 was rejected as
   a candidate: its 0.8A minimum peak limit does not provide the required margin
   over approximately 0.82A average cap current at 1.7V, before ripple/losses.
2. BQ25173 KISET accuracy from 0 to 2.65V, FB input bias and complete VREG corners.
   Its text explicitly supports 0V charging and sets current limits before enabling
   the linear stage, but tabulated accuracy examples use 3.8V/7.6V. The separate
   branch limit protects the main rail; it does not prove recharge time.
3. Guaranteed main cold-start progression, actual effective capacitors and
   startup load, TPS2116 input-collapse/softstart behavior and switchover. A typical
   soft-start time or eventual convergence is not acceptance. Larger available
   source current alone does not close these gates.
4. CC/POR/gate timing, VDD≤25ms ramp, −40 to 85°C ambient constraint, downgrade/detach, source current including upstream AON,
   input inrush and branch-limit transient response. Include stalled-start and
   shorted charger cases without AON/CC/main-latch starvation.
5. Enclosed thermal tests, charger CV tail, boost/buck stability, cap ESR/aging,
   radio/DMX/flash peaks and measured ride-through. No independent simultaneous
   radio load is invented. Keep the existing conservative load assumptions.

In both paths, INPUT_FAULT_N translation remains the prior **unpopulated
proposal**, DIO18 stays parent/Astra-owned, and existing MCU/DMX boundary mappings
remain unchanged. No firmware, hardware access, installation or new reviews were
performed. No old receipt, package validator, canonical docs, CAD or BOM was edited.
