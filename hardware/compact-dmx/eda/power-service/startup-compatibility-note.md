# Separated power architecture: is 1.5 A essential?

**No architectural requirement for 1.5 A was established.** Separating USB main
power, a charger branch and a cap-fed boost removes TPS61094 precharge from USB
startup at either source rating. My earlier proposal coupled that architecture
to a larger source and 100 mA charging unnecessarily. **1.5 A was an engineering
margin/faster-charge preference; a guaranteed 500 mA implementation is unresolved.**
The parent's source-contract decision remains pending. Neither source contract
nor any circuit is selected or changed here; no legacy-support requirement is
inferred. This note supplements the preserved proposal and receipts.

A 500 mA version can retain passive Rd and omit TUSB320LAI, CC_3V3 LDO and the
CC-specific POR/decode. It still needs raw-source-powered AON, independent
converter/buck/charger enables, USB-side voltage qualification, cap-arm/UVLO and
actual boost readiness. Empty-cap startup must power the future loader directly
from USB with charging disabled. After buck PG, enabling charging must not cause
an input collapse that resets AON or repeatedly restarts the application. Neither
buck PG alone nor a startup delay proves this. Source/commit status stays real;
cap rebound alone cannot rearm the backup latch.

The approximately 325 mA estimate included TPS61094 switch-mode charging. For a
separate **linear** BQ25173 at nominal 25 mA, use a new sum, not that estimate plus
a second full charger. With the existing **assumptions** (1.1 W main load, 85%
buck efficiency and 2 mA other demand), 12.0 kΩ ISET gives 22.42–27.60 mA from
KISET/resistor corners. Adding the tabulated 0.6 mA enabled IQ and 0.14 mA branch
switch allowance gives these illustrative main-input totals:

| Case | At allocated 4.305 V buck input | At old 3.913 V qualified-floor allocation |
|---|---:|---:|
| Healthy nominal-25 mA charger | 330.96 mA | 361.10 mA |
| Main limiter minimum | 389.80 mA | 389.80 mA |
| Remaining healthy margin | 58.84 mA | 28.70 mA |
| TPS2553 branch at 100 mA DC limit, including branch IQ | 402.76 mA | 432.90 mA |
| TPS22946 branch at conditional 60 mA DC limit, including branch IQ | 362.63 mA | 392.77 mA |

These are arithmetic allocations, **not measured load maxima or guaranteed
startup currents**. Existing voltage allocations must be recalculated for a new
capture. BQ25173 KISET/IQ test conditions do not establish all limits at a
0–2.65 V cap; below 50 mA it also recommends extra ISET RC filtering. Its internal
OUT OCP can reach 1.1 A before shutdown, so the programmed 25 mA is not the
independent branch-fault bound. See the cached [BQ25173](startup-source-cache/bq25173.pdf),
printed pp. 6–7, 12 and 14. Ideal 15 F/2.6 V charging at 25 mA takes 26 minutes,
before CV tail, temperature and low-output-current accuracy qualification.

Only these two existing-cache branch-limit approaches were checked:

1. **TPS2553, ILIM tied to IN:** the explicitly supported low setting is
   **50–100 mA**, not the previous 210 kΩ branch's roughly 109–152 mA. Its minimum
   accommodates a healthy 25 mA charger, but its maximum exceeds the remaining
   main-current budget by **13.0–43.1 mA** in the examples. With these assumptions,
   carrying the full branch fault without charge shedding would require about
   **4.499 V at the buck**, already above the assumed 4.4 V receptacle corner.
   A separately bounded priority-disconnect/foldback implementation would therefore
   be needed; a new comparator, ordinary fault flag or buck-PG enable is not by
   itself a timing proof. DC limits and the typical 2 µs short response do not
   bound hot-plug peaks. Do not extrapolate resistor equations beyond their
   specified range to invent a tighter limit. Source: [TPS2553](../source-cache/tps2553.pdf),
   pp. 7, 13–16. This is a credible lower-current building block, **not a proven
   standalone 500 mA solution**.
2. **TPS22946, CL floating:** nominal 30 mA mode has **28–60 mA** DC limits at
   its 3.3 V test point. The upper DC case fits the full-source example, but
   exceeds the old qualified-floor budget by **3.0 mA**. Conditionally, a buck
   input above about **3.948 V** would fit that DC case with zero reserve; this
   is a qualification-threshold tradeoff, not a selected circuit. More seriously,
   startup deliberately raises the limit: **375–685 mA** at the specified
   3.3 V/2.3 V test point, during a nominal 8 ms window with no tabulated maximum
   duration. Turn-on times are typical only. Holding charger CE disabled prevents
   charging but does not bound precharge of its IN capacitor or a shorted branch.
   A voltage-ready output also does not prove that the elevated-limit window has
   ended. Moreover, 27.60 mA charging plus 0.6 mA IQ marginally exceeds the 28 mA
   minimum; the full DC range at USB-side 4.4–5.5 V is not tabulated. Limits need
   confirmation, extra startup-current control or a lower charge setting before
   capture. Auto-retry may cycle the branch; it must never cycle main/AON power.
   This part adds a −40 to 85°C ambient constraint. Source:
   [TPS22946](../source-cache/tps22946.pdf), pp. 5–6, 12–16. **Not a drop-in repair.**

Area favors investigating 500 mA rather than assuming CC detection is free.
Removing TUSB320LAI and TPS709 saves **7.20 mm² of IC body area**, plus CC-specific
POR/decode/passives and routing, while retaining the receptacle's two Rd resistors.
The separated architecture with the TPS2553 branch would nominally add **4.56 mm²**
net IC body area over removal of TPS61094; substituting TPS22946 gives **1.18 mm²**.
These exclude required startup/priority controls, ISET RC, boost-ready/cap-start
logic, magnetics, capacitors, courtyards and DSBGA escape/assembly constraints.
They are not PCB-area, housing-fit or manufacturing claims. Shared AON/POR and
backup-control functions cannot be deleted merely because CC detection is omitted.

For either source rating, the **unclosed boot gates** remain main-path reservoir
precharge, TPS2116 softstart/collapse behavior, buck startup and actual MCU/radio/
DMX/flash boot peaks. The 1.1 W/85% figures are operating allocations, not boot
maxima. TPS62132 supports prebiased startup and its SS equation supports a slower
ramp, but neither a typical mux softstart nor a computed output-cap ramp bounds
instantaneous system input current. A 1.5 A source makes these budgets easier;
it does not prove them. Raw-side AON loads must be bounded separately: the
existing main-switch maximum plus its 0.14 mA allowance leaves only **11.65 mA**
outside that switch within 500 mA. Backup low-input current/PFM voltage, cap ESR,
thermal and conditional 10–30 s runtime gates remain unchanged.

**Disposition:** separation alone does not justify imposing ≥1.5 A or adding CC
area. The healthy 500 mA arithmetic is credible; the two checked branch switches
do not yet provide the complete fault/startup guarantee. Keep source selection
pending on that distinction. No circuit capture, ERC rerun, firmware, hardware,
installation, children or publication was performed. Arithmetic and preservation
checks are in [startup-compatibility-check.json](startup-compatibility-check.json):
all 27 baseline files, the nine prior startup artifacts and the startup receipt
retain their recorded hashes. Source hashes are included; original caches were read.
