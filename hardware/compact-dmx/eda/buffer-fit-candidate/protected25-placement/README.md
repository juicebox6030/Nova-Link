# Protected25: one sidecar placement integration attempt

**Conditional geometric candidate, not accepted protection hardware or a manufacturing release.** The real merged power/protection schematic and saved board contain the14 added parts. All178 original footprint positions and673 pad geometries remain unchanged; only three existing pad nets and two resistor values change. The main90×28×1 board, USB tongue, routed cell aperture and external98×34×24 case remain. The copied base needs the explicit local relief below. No baseline, previous candidate, BOM or parent document was edited.

This is the owned checkpoint for the parent's bounded Astra LOW/default task on shared main `b42c0e6284aac734fde851c69146abf73920f337`. No children, installs, vendor contact, hardware, firmware or Git publication. `receipt.json` and `verification.json` are the result records; `frozen-inputs.json` freezes194 source files. `prepare.py` is one-time initialization and refuses to overwrite the freeze.

## Actual electrical integration

`generate.py` executes **copied, frozen generator declarations** in this folder, inserts the source protection parts, and renders real modern KiCad sheets. KiCad10.0.7 exports `protected25.net`; it is not a handwritten netlist. The main/control power sheets have0 actual ERC violations. MCU/RF/DMX remain the original board context and explicit power-sheet interfaces; this is not a newly captured full-product schematic.

| Protection context | Existing board role |
|---|---|
| U104 | U3 BQ25173DSGR |
| R201 / R202 | R20 VCHG_TOP / R21 VCHG_BOTTOM |
| R203 / R204 | R19 ICHG / R18 ICHG_FILTER |
| C201 / C203 | C7 CHGIN / C4 ICHG |

Only U101/U102/U103,F101,R101..105,C101..104,C202 are added. U104/R201..204/C201/C203 are **not duplicated**.

- C23.1 now `CELL_TAB_POS`; C23.2 remainsGND_USB. F101.1 and R101.1 are the only other physical pads on the unfused node. The cell positive conductor reaches the fuse **before** CAP_POS charger/boost/sense branching. R101 independently senses the unfused node.
- F101.2 isCAP_POS. U3.8, existing boost/UVLO/arm branches and newC202 remain onCAP_POS.
- U103 A2/B2 receiveLIMITED_5V; A1/B1 feedCHARGER_IN_PROTECTED. Only U3.1 and its existingC7 input bypass change supply. No main-path switch or second charger is introduced.
- CHARGE_DISABLE remainsU3.3. Actual U101/U102 open-drain outputs shareCHARGER_PERMIT_OD; U103 C2 isCHARGER_SWITCH_ON, with source-captured attenuation/default resistors intact.
- R20 becomesTNPW040222K2BYED22.2k; R21 becomesTNPW040210K0BYED10k, both0.1%10ppm/K. No charging-current, UVLO, MCU, RF or DMX function changes.

`verify.py` compares459 connected exported pins against saved PCB pads,20 independent critical-pin assertions, all original pads/footprint identities/values/layers and the exact outer/aperture edge geometry. Source leading sheet slashes are normalized only for net comparison. The complete prefuse membership is asserted, not inferred from similar names. None of the baseline MCU/RF/DMX or factory-interface nets change.

## One placement and concrete mechanical delta

The deterministic placement tries existing free courtyards with0.15mm proposed separation, avoiding the isolated region, cell/lead reserve, RF/bottom reserve, antenna end, USB region and screw axes. It does not relocate existing parts or search alternative architectures. New parts are all bottom-side; their exact positions/orientations are in `placement.json`. The fuse could not fit the screened top-side free space without changing existing placements. `failed: [F101]` records that initial top-only screen, **not omission of the fuse**: the saved candidate includes F101 on the bottom at(56.5,41),270degrees.

F101's sourced maximum6.30×2.94×2.94 body reachesZ7.06 beneath PCBbottomZ10. Original base topZ7 leaves only0.06mm nominal, insufficient for the explicit0.20mm downward assembly/process clearance allocation. Therefore the copied assembly contains one proposed interior relief:

- X54.6..58.4, Y37.4..44.6, Z6.6..7;3.8×7.2×0.4mm removed.
- External base surfaceZ5 remains; floor thickness1.60mm. No external case growth.
- Vertical gap0.46mm; shortest true3D body/base distance0.434166mm includes pocket edges. A0.20mm downward body screen remains clear; its vertical gap is0.26mm.
- Nominal pocket lateral margins0.43/0.45mm. An additional independent envelope expands the fuse by0.25mm on each X/Y side and shifts it0.20mm downward; it remains clear. The0.20mm allocation can be budgeted as0.10 seat datum +0.05 board bow +0.05 base process, all proposed rather than measured. These are **engineering allowances**, not demonstrated additive/molded capability. Strength, creep, warp, fastener loading and process approval remain open. This relief is a concrete parent-integration proposal, not an active-base edit.

The native/STEP assembly includes the original26 solids plus14 manufacturer-maximum body envelopes. Those are not supplier-detail CAD, solder fillets or measured component models.25 source solids are geometrically unchanged; the base difference is independently confined to the relief. Existing component courtyard-volume screens are conservative allocations, not fabricated supplier bodies. All retained leads, cradle, liners, screws, USB stakes/supports and aperture remain in the checks. Four original bounded screw/pilot thread engagements are the only positive-volume pair exceptions.

`placement-sections.svg/pdf` is dimensioned and explicitly labels differing projection scales. `actual-board-top.svg` and `actual-board-bottom.svg` are direct KiCad plots of actual pads, courtyards and edges. The drawing's simplified allocation plan does not replace those exact plots.

## Routing, access and protection limits

**No routed continuity is claimed.** Actual KiCad DRC is0 violations /485 unconnected items; tracks0. The inherited ignored DRC categories are unchanged from integrated25. Complete37-part MCU/RF/DMX placement is retained through the stronger check on all178 original footprints.

F101.1 is11.733819mm straight-line from the cell's positive PCB land; this is a lower bound on a future unfused route, not a measured trace length or a qualified cell-local protection layout. R101 is placed toward the fuse, so its raw-cell sense connection does not intentionally traverse the entire control region before the limiting resistor. Actual prefuse copper length/width/clearance, mechanical insulation/restraint, fault energy, branch ordering and routing must be approved. No insulated wire or copper route is invented to close this obligation. The cap's formed lead itself remains unprotected and supplier-unqualified.

Several added parts occupy distributed remaining space; local bypass loop length and sensitive sense/control routing are **not established by courtyard fit**. C202-to-U3 and U103-to-U3 paths require actual routing review. This attempt establishes nominal physical allocations, not a tuned or optimized power layout.

Assembly order: solder and inspect bottom SMT parts before seating PCB/cell assembly into the base. The underside is accessible with the board removed; there is no claimed in-case solder-tool access. Fuse rework requires opening/removing the board and safely discharging the cell; it is not an external user-serviceable fuse. Keep the existing preforming, cell solder/liner, vent, USB and factory-access procedures/gates. No new tool-path or strength qualification is claimed. Factory contact locations remain unchanged.

Protection acceptance remains **UNMET**: turnoff maximum/overshoot, fuse clearing under decaying cap faults, healthy10s, lifetime/temperature/ESR, startup, charging arm margin and physical fault tests. The protection source's13.256s hot-fuse runtime is conditional, not recomputed or accepted by placement. Existing switch-land, USB process/cable, radio retuning, fixture-fit and cell-forming qualifications remain open. No barrel-source integration dependency is introduced; sidecar input stays5V USB-C advertisingat least1.5A.

## Provenance and reproduction

No new manufacturer claim or download was needed. `source-ledger.json` hashes the existing primary-source ledgers and exact land data. TI TPS3700/TPS3808/TPS22963C/BQ25173, Littelfuse451, VishayTNPW and Murata dimensions/pins remain those in the frozen cell-protection source PDFs and ledgers. Eaton25F/lead data and engineering forming geometry remain the frozen integrated25 basis. DDC/DBV/R/C lands are source-derived; body-envelope fit does not upgrade supplier/PCB qualification.

From repo root, substitute `P=hardware/compact-dmx/eda/buffer-fit-candidate/protected25-placement`:

```sh
python3 "$P/generate.py"
flatpak run --command=kicad-cli org.kicad.KiCad sch export netlist --format kicadxml -o "$P/protected25.net" "$P/qualified15.kicad_sch"
flatpak run --command=kicad-cli org.kicad.KiCad sch erc --format json -o "$P/erc.json" "$P/qualified15.kicad_sch"
flatpak run --command=python3 org.kicad.KiCad "$P/read_board.py"
flatpak run --command=python3 org.kicad.KiCad "$P/place.py"
flatpak run --command=kicad-cli org.kicad.KiCad pcb drc --format json --severity-all -o "$P/drc.json" "$P/protected25.kicad_pcb"
QT_QPA_PLATFORM=offscreen /home/juicebox/.local/bin/freecadcmd "$P/mechanics.py"
QT_QPA_PLATFORM=offscreen /home/juicebox/.local/bin/freecadcmd "$P/reopen.py"
flatpak run --command=python3 org.kicad.KiCad "$P/verify.py"
python3 "$P/draw.py"
```

`receipt.py` hashes generated artifacts after checks; `verify_receipt.py` checks hashes without regenerating or blindly refreshing them. All operations are local. This is one bounded integration attempt and a parent-reviewable local relief proposal, not release-to-manufacture.
