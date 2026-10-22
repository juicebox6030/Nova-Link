# DMX transceiver and USB-C power barrel — preliminary hardware design A

Date: 2026-10-22. Owner scope: **hardware only**, native NOVA-LINK with
extensions/plugins as needed, and **10–30 seconds** of internal backup.
This is a component-backed architecture and schematic brief. It is not a
released electrical schematic, PCB, mechanical CAD assembly, or fabrication package.

Open [the illustrated design](dmx-hardware-concept.html) for product views,
connector variants, the circuit architecture, and an adjustable runtime estimate.
The [candidate BOM](dmx-hardware-bom.csv) identifies selected functions and parts
that still need final package, procurement, and schematic checks.

## Current brief and acceptance

Original request:

> Please design me a small Transceiver that plugs into a DMX light, has A TI chip, a DMX circut, and is powered VIA USB C with a small internal power buffer(small battery or cap). In addition, I want you to design a power barrel that has USBC outout in the middle of it. The design should include both powecon and tru1 connectors, as well as standard 5-15.

Owner clarification, 2026-10-22:

> NOVA-Link with whatever extensions and plugins needed. Hardware only please, I dont need a software eval or programming yet. Feel free to make notes on what the software limits are based on the hardware.

> 10-30 seconds.

Acceptance for this design pass:

- [x] Describe a fixture-plugging TI radio/DMX transceiver, USB-C input, isolation,
  buffer sizing, candidate components, and plausible mechanical packaging.
- [x] Describe a separate inline mains adapter with a central USB-C outlet and
  powerCON, TRUE1, and NEMA 5-15 variants, including connector direction.
- [x] Distinguish calculations and packaging targets from measured performance;
  record the hardware-imposed software constraints without implementing software.
- [x] Provide a visual design, source references, candidate BOM, and hardware
  verification requirements for a later schematic/prototype phase.

Scope: this repository, `main`, starting revision `ebfb7c3`; documentation/design
assets only. No software changes, firmware evaluation, purchasing, new services,
hardware access, or mains construction. Publication follows the repository's
commit/push rules; no deployment. Work is inline, with no delegated tasks.
The bounded deliverable is this preliminary design; schematic capture, board
layout, CAD fit, certification, and prototype measurements are a subsequent phase.

## 1. Product arrangement

Two electrically separate products share a short USB-C cable:

```text
AC feed ── power barrel ── existing AC lead ── fixture AC input
                │
         central USB-C OUT
                │  short C-to-C cable, nominal 150–300 mm
         USB-C IN on dongle
                │
      TI radio + host + buffer
                │ isolated DMX
      female 5-pin XLR ── fixture male DMX IN
```

The capacitor keeps the **dongle and its DMX interface** operating when USB power
is interrupted. It does not supply the fixture or the barrel's mains output.
During a mains outage the fixture can go dark while the dongle retains its link.

Recommended first assembly: 5-pin female dongle and TRUE1 TOP barrel. Build
the other power variants around the same isolated USB supply assembly, with
connector-specific end fittings and reviewed wiring. One box containing all
three mains inputs is unnecessary and would introduce source-selection hazards.

### Packaging targets, not dimensioned CAD

| Item | Preliminary external envelope | Construction |
|---|---|---|
| Dongle body | 85 × 34 × 28 mm, plus approximately 25 mm XLR nose; roughly 110 mm overall | Insulating shell, metal XLR front, nonmetallic antenna tail, recessed side USB-C, retention eye |
| Dongle PCB | Approximately 70 × 24 mm, four layers | Isolation slot/keepout near XLR; RF at opposite end; capacitor above board in a supported cradle |
| Power barrel center body | Approximately 125 × 60 × 50 mm, excluding protruding connectors/cords | Rounded rectangular inline pod, connector end caps, central side-facing USB-C outlet |
| NEMA cord option | Same center body plus short molded pigtails | Reduces leverage on outlets; length selected during mechanical design |

The capacitor's approximately 16.5 mm diameter and 28.4 mm length dominate dongle
thickness. The barrel contains a 45.7 × 25.4 × 21.5 mm AC/DC module before terminals,
isolation, strain relief, USB parts, and enclosure walls are allocated. These
dimensions make an XLR-cable-plug-sized complete assembly an unreasonable starting
promise. Use connector manufacturer STEP/cutout drawings to resolve the envelopes.
[Eaton capacitor](https://www.eaton.com/us/en-us/skuPage.HV1625-2R7256-R.html),
[MEAN WELL module](https://www.meanwell.com/Upload/PDF/IRM-10/IRM-10-SPEC.PDF).

## 2. Dongle electrical architecture

### 2.1 Radio and host

Use **TI CC1352R1**, provisionally `CC1352R1F3RGZ`, for the NOVA-LINK radio.
Retain an **ESP32-S3-MINI-1U** host to match the repository's ESP32-S3/TI split.
The host provides UART DMX framing and application/plugin processing; host-to-radio
SPI, ready/interrupt, reset, and debug signals are reserved by function.
Physical GPIO assignments are deliberately unassigned until schematic review.

Base RF population is **2.4 GHz**, with a matched antenna in the plastic tail.
The exact native PHY, RF settings, matching parts, and antenna geometry remain
engineering selections. Follow TI reference layouts for the exact silicon and
band; provide a conducted RF test connection or a switchable antenna test point.
CC1352 supports sub-GHz too, but an effective sub-GHz antenna is a separate
mechanical/RF design. Do not promise dual-band operation from the compact base
antenna. One CC1352 RF chain changes bands; it cannot receive two bands
simultaneously. Simultaneous reception requires another independent radio chain.
[TI radio](https://www.ti.com/product/CC1352R).

The ESP module is the external-antenna version. Base operation uses no ESP Wi-Fi
or Bluetooth transmission and leaves that RF connector unpopulated. If host RF is
later required, add and validate a suitable antenna and coexistence strategy;
the TI antenna is not shared with it. Keep its power/peak-current consequences
within the measured backup budget.
[Espressif module datasheet](https://www.espressif.com/sites/default/files/documentation/esp32-s3-mini-1_mini-1u_datasheet_en.pdf).

### 2.2 DMX circuit

Use **TI ISOW1412**, 500 kb/s, with integrated isolated DC/DC power. Configure
3.3 V input and 3.3 V isolated output, with `MODE` tied to isolated ground.
Join `VISOOUT` to `VISOIN` and keep the isolated and logic grounds separate.
This is a full-duplex IC used on a half-duplex bus: join driver `Y` to receiver
`A`, and driver `Z` to receiver `B`. TI's schematic and truth tables establish
the polarity below; do not rely on A/B naming across manufacturers.
[TI ISOW1412 datasheet, pin functions and functional modes](https://www.ti.com/lit/ds/symlink/isow1412.pdf).

| Net/function | Schematic intent |
|---|---|
| `DMX_TX` | Host UART TX → ISOW1412 `D` |
| `DMX_RX` | ISOW1412 `R` → host UART RX |
| `DMX_DE` | Host-controlled driver enable; external 10 kΩ pulldown; gate low during reset, power fault, or undervoltage |
| `DMX_RE_N` | Independent receiver enable; default disabled with 10 kΩ pullup; permits echo monitoring and future RDM |
| `DMX_P` | `Y` + `A` → protection → XLR pin 3, Data 1+ |
| `DMX_N` | `Z` + `B` → protection → XLR pin 2, Data 1− |
| `DMX_COM` | Isolated ground → XLR pin 1, data common; never hard-strap to USB ground |
| XLR pins 4, 5 | No connection; no accessory power |
| Termination | 120 Ω, 1%, across `DMX_P`/`DMX_N`, through a recessed manual switch |
| Protection | RS-485-compatible TVS array referenced to `DMX_COM`, close to XLR; provision matched low-value series parts and an optional common-mode choke for EMC tuning |

The receiver-mode dongle has a **female 5-pin output** that plugs into the
fixture's usual male DMX input. A three-pin female mechanical variant uses
pins 1/2/3 identically for existing three-pin fixtures; it is a compatibility
variant, not the standard five-pin connector. A wired-input transmitter version
uses a male XLR end assembly and the same bidirectional electronics. Direction
must be explicitly selected; do not enable two drivers on the same bus.

Termination is OFF when supplying DMX to a fixture chain; terminate the last
fixture. Turn it ON when this unit is the terminating receiving end of a wired
DMX line. Retain RDM electrical capability through independently controlled
driver/receiver enables, but no RDM implementation or certification is claimed.
Final port protection, output levels, connector wiring, and timing must be
checked against ANSI E1.11 and, if RDM is implemented later, E1.20. ESTA's
[published standards index](https://tsp.esta.org/tsp/documents/published_docs.php)
lists E1.11-2024; its full normative text was not retrieved for this design pass.

### 2.3 USB-C input and power buffer

```text
USB-C VBUS ── OVP/current limit/reverse block ── TPS61094 VIN
       │                                           │
       └─ bias LDO ─ CC sink controller       SYS_RAW output
                    CC1, CC2                       │
                                             TPS62132
                                              3.3 V
                              ┌────────────────────┼──────────────┐
                         ESP32-S3              CC1352R1      ISOW1412
                                                              ║ isolation
TPS61094 SUP ── 25 F / 2.7 V capacitor                         DMX
                charged to 2.6 V
```

Power input is **5 V USB-C**, requiring a source advertising at least **1.5 A**.
USB-PD negotiation is unnecessary. Specify a power-only receptacle: D+/D− and
SBU are unconnected; provide separate programming/test pads on the PCB.
Use a TUSB320-family CC controller in fixed sink/GPIO mode, including its
documented unpowered attachment behavior. Do not parallel independent Rd
resistors with an IC's active/internal CC terminations without its prescribed
application circuit. A small always-on bias LDO powers the CC logic from VBUS,
independent of the buffered 3.3 V rail. Decode valid attachment/current mode in
hardware before accepting USB power and enabling capacitor charging. This gates
the USB path, not the buffered system rail; loss of USB must leave backup running.
The original TUSB320 GPIO current indication is sampled on attachment, so it is
not sufficient for a source that later lowers its advertisement. Include a
continuous CC current-level monitor in the hardware logic, or replace the sink
controller with a verified continuously updating part during schematic capture.
The bundled barrel advertises a fixed 1.5 A, but other sources still need this
check. Default-current sources and A-to-C cables are outside the base input specification.
[TI TUSB320](https://www.ti.com/lit/ds/symlink/tusb320.pdf).

Use a **TPS25947-family eFuse**, with the exact cutoff/retry variant selected
during capture. Set an approximately 1.2 A operating limit whose worst-case
upper bound stays below the advertised 1.5 A. Add input OVP, controlled inrush,
CC/VBUS ESD protection, and true reverse blocking so capacitor power cannot
appear on an unplugged USB receptacle. Target nominal OVP near 5.3 V; verify
threshold tolerance and transient overshoot keep TPS61094 within its 5.5 V
operating ceiling. The eFuse and CC decoder are design functions, not a claim
of completed USB compliance.
[TI eFuse](https://www.ti.com/product/TPS25947).

Use **TPS61094** in its **supercapacitor backup application**, with VIN and SUP
separate. In normal operation SYS_RAW follows protected USB; during backup
the converter regulates SYS_RAW at **3.6 V**. This separation allows a later
3.3 V buck to work from both USB and the capacitor. A 5 V boost target directly
behind a nominal 5 V USB source would leave inadequate mode-transition headroom.

Initial configuration from the TI tables:

| Setting | Initial value |
|---|---|
| OSEL resistor | 17.4 kΩ, 1% → 3.6 V backup output |
| VCHG resistor | 9.53 kΩ, 1% → 2.6 V cap charge target |
| ICHG resistor | 274 kΩ, 1% → 500 mA cap charging current |
| Inductor | Start with a 2.2 µH shielded part; select saturation/DCR from worst-case low-cap peak current and TI's application guidance |
| Bypass and reservoir capacitors | Start from TI's backup reference; recalculate effective MLCC capacitance, ESR and required transient energy before fixing values |

The 500 mA setting is **capacitor current**, not USB current. At 2.6 V it is
1.3 W before charge conversion loss. Exact startup behavior, minimum cap voltage,
inductor ripple, switch limit, dropout and USB reattachment transitions require
schematic calculations and load-step tests.
[TI TPS61094 datasheet, Tables 7-1 through 7-3 and backup application](https://www.ti.com/lit/ds/symlink/tps61094.pdf).

**TPS62132**, the fixed **3.3 V** family member, supplies all nonisolated
electronics. It accepts the normal USB-derived rail and the 3.6 V backup rail;
its 100% duty-cycle behavior must be checked at worst-case rail droop and load.
Use its reference inductor/soft-start/decoupling circuit as the starting point.
This is not the fixed-5 V TPS62133.
[TI TPS6213x datasheet](https://www.ti.com/lit/ds/symlink/tps62130.pdf).

Add hardware cap-voltage monitoring with **approximately 1.6 V under-load cutoff**,
a shutdown latch that rearms on valid USB return, and a power-good/reset chain.
It must drop `DMX_DE` before the rail fails and avoid repeated restart chatter.
Do not rely on application firmware to enforce the cutoff. Exact supervisor,
latch, divider values, tolerances, and startup truth table remain schematic work.
Expose USB-present, cap-voltage, buffer-ready, 3.3 V power-good and fault signals
for later software and test equipment. A buffer-ready indicator should mean
at least 2.55 V cap charge, not simply USB-present.

### 2.4 Capacitor and runtime calculation

Candidate: **Eaton HV1625-2R7256-R**, 25 F, 2.7 V, approximately 27 mΩ initial
ESR. Charge at 2.6 V to allow margin below the cell rating. A single cell avoids
series balancing. Secure its body mechanically, insulate its leads, and include
a protected service discharge method; do not short it to discharge it.
The candidate's +65 °C maximum and aging characteristics constrain the enclosure
near a hot fixture. Preliminary ambient target is 0–40 °C, subject to internal
temperature measurements. Use a higher-temperature cell or change the enclosure
if the internal thermal limit cannot be met.
[Eaton specifications](https://www.eaton.com/us/en-us/skuPage.HV1625-2R7256-R.html).

For average useful load power `P` on the 3.3 V rail:

```text
usable capacitor energy = 0.5 × C × (Vstart² − Vcutoff²)
estimated hold-up seconds = usable energy × conversion efficiency / P

Nominal: C = 25 F, Vstart = 2.60 V, Vcutoff = 1.60 V,
         efficiency = 0.75, P = 1.50 W
         energy = 52.50 J; hold-up = 26.25 s

Illustrative aged/tolerance case:
         C = 25 × 0.90 × 0.70 = 15.75 F, Vstart = 2.55 V
         same cutoff, efficiency and load
         energy = 31.0472 J; hold-up = 15.52 s
```

The 0.90 capacitance tolerance factor must be confirmed in the final approved
cell datasheet. Eaton lists a 70% end-of-life capacitance rating and doubled
end-of-life ESR; account for ESR voltage drop and cold/aged behavior separately.
The 75% efficiency is a planning assumption for boost plus buck, not a measured
efficiency or a guaranteed worst case. At 1.5 W useful load and a 1.6 V cell,
the approximate capacitor current is `1.5 / (0.75 × 1.6) = 1.25 A`.
At 54 mΩ aged ESR the drop is approximately 68 mV, so under-load cutoff must be
defined at the converter terminals. Enforce at least 10 seconds on the actual
prototype under the chosen worst-case conditions. Thirty seconds is the upper
target, not an enforced shutdown time; a lighter load can run longer.

The deliberate 1.5 W average load allocation is:

| Function | Planning allowance on the 3.3 V rail |
|---|---:|
| ESP32-S3 host, host RF inactive | 0.60 W |
| CC1352R1 radio and processing | 0.12 W |
| ISOW1412 including its isolated supply and loaded DMX bus | 0.45 W |
| Indication, supervisors and other small loads | 0.08 W |
| Contingency | 0.25 W |
| **Total** | **1.50 W** |

These are allocations, not device maximum ratings. The 3 A downstream buck does
not make the upstream backup chain a 3 A supply. Size the whole path for measured
peaks, including cold capacitor startup and loaded DMX, and adjust the envelope
or buffer if it exceeds the TPS61094's usable low-voltage output capability.
Adding sustained Wi-Fi operation or a high-power RF amplifier requires a new budget.

Ideal constant-current recharge is roughly **130 seconds from empty** and
**50 seconds from 1.6 to 2.6 V**, at 500 mA. Real time is longer due to charging
limits and transitions. The dongle runs immediately from USB while charging,
but the full hold-up target applies only after adequate charging.

## 3. Power barrel

### 3.1 Shared electrical design

```text
AC IN L ── rated splice/wire ───────────────────────── AC OUT L
               │
          branch fuse ── thermal/surge protection ──┐
AC IN N ── rated splice/wire ──────────────────┐    │
               └─────────────────────────────┼─ isolated AC/DC
                                             │    │  5 V / 2 A
                                             │    └─ OVP/current switch ── USB-C VBUS
                                             │          ▲
                                             │     source CC/attach logic
                                             └────────────────── AC OUT N
AC IN PE ── dedicated protective-earth path ─────────────── AC OUT PE
```

Use **MEAN WELL IRM-10-5**, a candidate 5 V / 2 A isolated AC/DC module, rather
than a custom offline converter. The USB output is **5 V / 1.5 A, 7.5 W** so the
10 W module has nominal headroom; verify enclosure/ambient and input-voltage
derating. Add secondary OVP: the module's own protection is not sufficient
evidence that every downstream USB component stays inside its absolute limits.
Keep USB ground on the isolated secondary. The module's component approvals
do not certify the complete adapter.
[MEAN WELL datasheet](https://www.meanwell.com/Upload/PDF/IRM-10/IRM-10-SPEC.PDF).

Use **TI TPS25810**, a fixed-source Type-C controller with integrated port switch
and discharge, hardware-strapped to advertise **1.5 A** on CC and use its
corresponding nominal 1.7 A current-limit mode. Verify its upper current-limit
tolerance, VCONN allowance and module thermal derating together. An upstream
secondary OVP/reverse-blocking stage protects the controller and the USB port;
TPS25810 handles attachment-gated VBUS and detach discharge. Add port ESD and
fault indication. Unlike TUSB320's source-current setting, this part's current
selection does not require an I²C software initialization. No USB data or PD
output is offered.
[TI TPS25810 datasheet](https://www.ti.com/lit/ds/symlink/tps25810.pdf).
A USB-C receptacle cannot be implemented as an always-powered socket with only
VBUS/GND and a generic resistor pair.

Full fixture current travels through rated wiring/splices, not the USB PCB.
PE is continuous, unswitched and unfused. Bond exposed conductive enclosure
parts where required; do not use a USB shield or PCB trace as the PE conductor.
Use insulated, flame-rated body material, proper connector anchoring, and
strain relief. Any surge suppression is selected for the variant's actual
input voltage and coordinated with the PSU branch fuse and thermal protection.
Fuse value, breaking capacity and the overall pass-through protection scheme
are unresolved until an assembly/product-safety review; no final mains wiring
or fuse schedule is released here.

The proposed overall pass-through ceiling is **15 A total**, including the USB
supply input, or lower if any part or thermal test requires it. This is a design
target, not an evaluated assembly rating. With a 15 A upstream feed, the fixture
and USB branch share that budget. The barrel requires continuous, undimmed mains.

### 3.2 Connector-specific assemblies

| Variant | Mains input at barrel | Mains output at barrel | Proposed input voltage scope |
|---|---|---|---|
| PC | Neutrik `NAC3MPXXA`, blue power-in chassis connector | Neutrik `NAC3MPXXB`, gray power-out chassis connector | 100–240 V AC nominal, 50/60 Hz; assembly review pending |
| T1 | Neutrik `NAC3MPX-TOP` inlet | Neutrik `NAC3FPX-TOP` outlet | 100–240 V AC nominal, 50/60 Hz; assembly review pending |
| US | NEMA 5-15P input, preferably molded pigtail | NEMA 5-15R output, preferably molded pigtail | 120 V AC nominal, 125 V connector ceiling; never label 240 V |

Use one input and one output per assembly. Maintain keyed polarity and the
manufacturer's L/N/PE markings. There is no connector-to-connector interchangeability
between powerCON and TRUE1. PC outputs require the correct gray-to-blue powerCON
jumper to the fixture; TRUE1 uses the correct male/female cord arrangement.
Cable connector suffix and strain-relief size depend on the actual cord OD.
For a manufacturer example of the 5-15 voltage/current class, see Leviton's
[15 A / 125 V NEMA 5-15R specification](https://leviton.com/products/515cv-lit).
The proposed molded cord assemblies still require their own approved selection.

For powerCON, select current **XX/FXX components** and verify each complete
mated pair. `NAC3MPA-1` is discontinued; its successor is `NAC3MPXXA`.
Legacy original powerCON lacks breaking capacity, while current XX/FXX pairs
can have breaking capacity when correctly mated. Therefore treat PC assemblies
used with legacy venue cabling as **de-energize before mating/unmating**.
Do not transfer a new connector's rating to an unidentified legacy mate.
[Legacy inlet](https://www.neutrik.com/en/product/NAC3MPA-1.pdf),
[XX inlet](https://www.neutrik.com/en/product/nac3mpxxa.pdf),
[XX outlet](https://www.neutrik.com/en/product/nac3mpxxb.pdf),
[FXX cable connector conditions](https://www.neutrik.com/en/product/nac3fxxa-w-l.pdf).

TRUE1 TOP supports breaking capacity with its specified mating components.
TOP connector ingress ratings do not make this USB-equipped adapter weatherproof.
Base design is **indoor/dry use**; a sealed connector/cap and enclosure validation
would be a separate environmental design.
[TRUE1 inlet](https://www.neutrik.co.uk/product/nac3mpx-top),
[TRUE1 cable connector](https://www.neutrik.co.uk/product/nac3fx-w-top).

The USB receptacle is on a recessed **side face at the barrel's longitudinal
center**, clear of locking collars, connector latches and cord bend zones. Provide
a replaceable short cable and a retention loop. Keep the secondary port board in
a partitioned compartment with no user-accessible path to mains terminals. Final
creepage/clearance, insulating barriers, wire gauges, protection and touch access
depend on the applicable product category, materials and assessed assembly;
component voltage ratings alone cannot establish them.

## 4. Layout and mechanical implementation notes

- Partition the dongle from XLR toward antenna: connector/protection → isolated
  DMX interface → host/power/capacitor → TI radio/matching → antenna keepout.
  Keep all ground copper, screws, shields, the capacitor and USB cable outside
  the chosen antenna's specified keepout. Prototype RF detuning next to a metal fixture.
- Maintain a real isolation barrier on all PCB layers; no planes or test headers
  bridge USB ground to DMX common. Apply ISOW1412 layout/decoupling and emissions
  recommendations; reserve ferrite positions. Its component isolation rating
  does not by itself describe the finished dongle's isolation rating.
- Seat the cap alongside/above the central board with a mechanical cradle;
  do not cantilever its mass from its two leads. Keep it away from hot power parts.
- Anchor XLR mechanically into the shell and add a small tether point. The
  fixture latch and USB cable should not carry the entire assembly's bending load.
- Provide separate TI debug and ESP programming pads, USB/buffer/system rail
  test points, isolation test access and conducted RF measurement access.
- Reserve one pairing/function button, RX/TX identification, USB/buffer status
  and link indication. No claim is made that those behaviors are implemented.
- Freeze exact board stackup, copper weights, connector part numbers, the RF
  network, supervisor logic and all footprints before attempting placement/routing.

## 5. Hardware limits relevant to later software

No firmware is changed or evaluated in this task. Later implementation must respect:

1. One TI RF chain cannot provide simultaneous sub-GHz/2.4 GHz reception.
   Native NOVA-LINK PHY and host/radio physical wiring remain unresolved in the
   existing [protocol decisions](../Protocol_Decisions.md) and
   [hardware preparation](../Hardware_Preparation.md).
2. The wired port is half duplex. A physical bidirectional transceiver enables
   TX, RX and potential RDM electrical turnaround; it does not implement RDM
   proxying, discovery, transport timing, or any proprietary wireless protocol.
3. Plan 250 kbit/s, 8N2 for DMX. A full start code plus 512 slots takes
   22.572 ms before break/mark spacing. For an illustrative 176 µs break plus
   16 µs mark-after-break, the minimum frame duration is 22.764 ms. A 40 Hz
   full-universe target is plausible on the wired side; RF throughput and
   end-to-end latency still require their own budget and measurement.
4. The existing native payload maximum is 100 bytes. A full universe requires
   at least six payload fragments before application metadata overhead, and
   the application must define atomic frame identity, completeness and stale-frame
   handling. This does not adopt a new wire format.
5. Capacitor capacity is finite. Host Wi-Fi/BLE, higher RF duty cycle or extra
   accessories must fit the accepted power budget. Hardware exposes power state
   and enforces the low-cap cutoff independently of software.
6. On a depleted cap or fault, the driver must be high impedance. The desired
   fixture look after link loss is a later product/software decision; holding
   electronics power alone does not establish a safe loss-of-link policy.

## 6. Verification required before fabrication/release

This is a hardware acceptance plan, **not a record of tests performed**.

| Gate | Required evidence |
|---|---|
| Schematic completeness | Approved exact parts/pins/values; ERC; power-startup truth table; USB CC decoding; cutoff/rearm; no isolation bridges |
| Mechanical fit | Actual connector STEP models and cap/module dimensions in CAD; antenna and barrier keepouts; cable/latch/retention clearance |
| USB-C | Both cable orientations; valid and invalid current advertisement; depleted-cap attach; detach discharge; no backfeed; inrush; shorts and OVP |
| Buffer | From ≥2.55 V charge, at least 10 s of powered radio/host plus loaded DMX at agreed load/temperature/aged-cap equivalents; capture rails, cap current and DE on scope |
| Power chain | Low-cap peak current, boost limit and inductor saturation; 3.6→3.3 V dropout/transients; 500 mA charging during maximum normal load |
| DMX electrical | Polarity, output swing and common-mode limits, termination switch, loaded cable behavior, tristate at startup/fault, protection and ground isolation |
| RF hardware | Antenna match and conducted/radiated behavior in enclosure and beside fixture; coexistence if later populated; market-specific compliance |
| Barrel mains | Qualified product-safety assessment of pass-through wiring/rating, PE continuity, touch access, strain relief, dielectric/leakage, fuse/surge coordination and fault containment |
| Barrel thermal/EMC | Simultaneous pass-through target load and 7.5 W USB output in enclosure at rated ambient; component derating, emissions and immunity |

## 7. Current checkpoint and remaining engineering

Settled by owner: native NOVA-LINK; hardware-only work; 10–30 seconds buffer.
Proposed by this design: a single 25 F supercapacitor, isolated 3.3 V DMX
interface, 5 V/1.5 A USB-C, 2.4 GHz base population, and three separate barrel
assemblies. These are preliminary selections, not owner-approved production parts.

Evidence for this pass: primary TI/Eaton/Neutrik/MEAN WELL/Espressif documentation
was consulted; buffer and DMX frame arithmetic was recomputed locally. The MEAN
WELL 2025-08-08 mechanical and derating drawings were visually inspected because
their PDF text extraction was corrupted. The illustrated design passed T3 HTML
preview at widths 360, 728 and 760 pixels, including light/dark appearances,
with no reported console errors or horizontal overflow. All three connector
buttons, the load warning and the efficiency slider passed presentation checks;
the CSV parsed as 37 rows, local document file links resolved, and
`git diff --check` passed. Repository changes are documentation only;
no software tests or hardware operations are represented as validation.

Remaining: final component/pin selection, supervisor/CC logic design, normative
standards review, complete EDA schematics, PCB layout, enclosure CAD and prototype
measurements. No purchase or mains build has been authorized or performed.
Next hardware phase: capture and review the dongle power/DMX schematic first,
then the separate barrel supply/protection assembly, using the gates above.
