Current RF passive selection: [source-backed replacements](../footprints/REPLACEMENT-PASS.md). Nominal values/topology unchanged; original reference MPNs below are historical, not current procurement selections.

# CC1352R1 support and dual-band frontend — prototype capture

2026-10-22. Owner correction: **“2.4 GHz plus US 915 MHz”**. The previous allocation-only receipt remains unchanged as historical evidence. Current source is CC1352R1F3RGZR, not P/R7. The support and RF frontend are now captured; a dual-feed antenna prototype is captured; final tuning, PCB routing and hardware qualification remain incomplete. No power-service or CAD source is changed by this follow-up.

## Retrieved primary evidence and revision limits

The original SWRC345A/SWRC361 downloads remain55571-byte loginHTML, notZIP. A new public route succeeded:

- [TI employee attachment, CC1352R1 LaunchPad RevB](https://e2e.ti.com/support/wireless-connectivity/sub-1-ghz-group/sub-1-ghz/f/sub-1-ghz-forum/770822/launchxl-cc1352r1-launchpad-design-files): real ZIP contains a17,165,788-byte Allegro ASCII `.brd.alg`. It establishes an available exact-R1 layout source, not a substitute schematic. Not converted/routed here.
- [TI SWRC354 archive](https://www.ti.com/lit/zip/swrc354): real ZIP containing CC1352EM-IPC **Rev1.1.0, March15 2018**, schematicPDF, BOM/PnPxlsx, Cadence expanded netlist, layout/stackupPDF and Gerbers. U1 is explicitlyCC1352R1F3RGZ. This is an older reference, not a newly released product design.
- [TI SWRA629A, June2019](https://www.ti.com/lit/an/swra629a/swra629a.pdf), §2 and Figures3/5/8/9: R1 integrated-balun architecture and layout requirements.
- [Johanson0900PC15A0036001E Rev2.0](https://www.johansontechnology.com/docs/800/0900PC15A0036001E_J3eS4Zu.pdf), pp1/3/4: current production part number, pinout and CC1352R schematic. This replaces the archive's **IPC1352_EXPERIMENTAL** placeholder, not its underlying pin topology. Manufacturer drawing checked visually.
- [TI SWRS196I, February2021](https://www.ti.com/lit/ds/symlink/cc1352r.pdf), §7/8.24.3/9/10: exact RGZ pins, crystal constraints, shared radio and reference-design requirements.
- [TI SWRU525E](https://www.ti.com/lit/ml/swru525e/swru525e.pdf) retrieved and inspected: quick-start guide, no support schematic appendix. SWRA640H Figure3-2 is CC1312R1; it was not used as exact R1 provenance.

Hashes and archive member provenance are in `dualband-source-evidence.json`. Large manufacturer files remain ignored cache, not redistributable product CAD. `reference-contract.json` was independently transcribed/extracted from the TI expanded netlist and BOM; the product generator does not generate that contract.

## Captured support circuit

FL101=BLM18HE152SN1D connectsSYS_3V3 toMCU_VDDS. U1 pins13/22/34/44 use that rail. C104/105/106/107 are individual100nF GRM155R71E104KE14D at those respective supply pins; C101=22µF GRM188R60J226MEA0D is the pin34 reservoir. L101=MLZ2012N6R8LT000,6.8µH connectsDCDC_SW33 toMCU_VDDR, which supplies45/48. C102=22µF and C108/C109=100nF decouple that rail. C103=1µF GRM155R61C105KA12D decouplesDCOUPL23 only. EGP localpad49 isGND_USB; no internal rail powers external loads. Two power flags identify implemented passive-derived rails after the bead/inductor; no missing support boundary remains.

Y101=Epson FC-13532.7680KA-AG0 connects6/7, with C110/C111=12pF GRM1555C1H120JA01D toground. Y102=NDK NX2016SA48MHz EXS00A-CS05517 connects47/46 through crystalpins1/3; casepins2/4ground. These are **exact referenceBOM choices**, not asserted current stock or qualified clock tolerance. The older schematic's X24M pin names are legacy labels: Y2 explicitly48MHz and current SWRS196I names46/47X48M_N/P. Do not substitute a24MHz crystal.

Reference R351100k/C351100nF resetRC is deliberately omitted: the existing power supervisor already drivesRESET_OK into MCU RESET_N35, and physical/factory reset operates the supervisor'sMR input. Adding a large capacitive load or directly shorting the push-pull reset output would not reproduce the intended power architecture. ReferenceC1/R352 wereDNM and remain absent. Future configuration must enable the intended internal DC-DC mode and meet crystal startup/calibration constraints. The reference48MHz crystal is a custom suffix with a broad tolerance description; supplier motional-inductance/ESR/load data, actual temperature tolerance, CCFG capacitance settings, errata applicability and chosen PHY frequency-error budget must be checked before release. No PHY is selected here.

## Dual-band signal path

TR101=Johanson0900PC15A0036001E (legacy0900PC15A0036) supports862–928MHz and2400–2500MHz and is configured for **external LNA bias in both bands**. Pin9→U1.1,8→U1.2,7→U1.3,6→U1.4,5→RX_TX/U1.5; grounds2/3/10→GND_USB. Pin1 is the2.4GHz50Ω port; pin4 is the sub-GHz output. C112100pF blocks the sub-GHz output into RF_915_50; C113100pF shuntsRX_TX toground per the actual reference and current manufacturer schematic. Do not confuse the shunt bias capacitor with a second series2.4GHz capacitor; the IPC already contains its2.4GHz blocking network.

A101=Johanson0900AD47A2450001E replaces the preliminary SPDT/common-feed candidate. Pin1 is the 2.4GHz feed and pin4 the 900MHz feed. Pins2/3/5/6/7/8 must be soldered to isolated lands, not grounded or electrically joined. DIO30/package43 is now NC. U101, R101 and common-feed C114 are removed. The old snapshot is in `historical-switched/`, outside current acceptance.

The antenna Rev3.1 p3 layout is the source for the starting match: L102=2.7nH series from RF_2G4_50 to ANT_2G4, C115=1.0pF shunt at ANT_2G4. At RF_915_50, L103=5.1nH and C116=8.2pF are **parallel shunts to ground**, followed by series L104=12nH to ANT_915. These are not two series inductors. Exact recommended Johanson MPNs are in the exported component ledger. Preserve tuning positions; these values are not qualified for this board.

This is **one time-shared radio**, not simultaneous independent915MHz and2.4GHz radios (SWRS196I §9). Scheduling/arbitration is future firmware work. Hardware connectivity does not establish latency, channel/PHY, transmit power, legal operation or interoperability.

## Direct dual-feed prototype and physical reservation

[Johanson production product](https://www.johansontechnology.com/products/antennas/rf-antennas/0900ad47a2450001e/) and [Rev3.1/2026 datasheet](https://www.johansontechnology.com/docs/4912/Antenna-0900AD47A2450001E_4RGCp0j.pdf), pp1–4, support this prototype choice. TI SWRA629A §2 describes independent 50Ω ports and switch/diplexer options; a switch is not intrinsic to the IPC. Retain external LNA bias in both bands and the existing sub-GHz series DC block. Do not add a DC path around the IPC or assume simultaneous radio operation.

The antenna's p4 typical 50Ω two-port measurements show S21 −15.927/−14.992/−16.553dB at868/896/928MHz, and −44.254/−43.149/−42.394dB at2400/2440/2480MHz. At the MCU's advertised ceilings (not selected operating/legal powers), a screening calculation gives14−14.992=−0.992dBm at the other antenna port, versus MCU2.4GHz absolute input maximum+5dBm; reverse screening gives5−42.394=−37.394dBm versus sub-GHz+10dBm. These apparent5.992/47.394dB differences are **not guaranteed safety margins**: the antenna data is typical and sampled, not worst-case; inactive-port impedance, mismatch, enclosure detuning and IPC out-of-band transfer are not bounded. No IPC attenuation is credited. Direct-feed prototype assembly is contingent on verifying powered/unpowered inactive-port stress and active-port match before RF operation. If that fails, retain separate antennas or select a current qualified RF isolation switch; do not restore the obsolete candidate by assumption.

Body maximum10.2×3.4×1.7mm is not the keepout. The p3 reference board is50×30mm overall:40mm grounded length plus10mm end clearance. Our90×28mm board has a longer ground but is2mm narrower (6.67%); neither change is RF-equivalent. Page9 illustrates a20mm-wide layout but does not qualify our28mm implementation or supply its tuned performance. The older single-feed80+10×60mm reference is not selected.

**Proposal for parent modelling, not verified placement:** use the existing18mm board-end reservation across the actual28mm PCB width; local x=0 at the outer end, increasing inward. Reserve x0..10mm all-layer metal clearance except the manufacturer's antenna lands/feed geometry, and x10..18mm for the two match networks and ground-via transition. Antenna orientation/isolated solder lands must reproduce p2/p3, including the manufacturer's irregular clearance outline; a plain rectangular chip footprint is insufficient. The five0402 match components require real courtyards and two controlled-impedance feeds.18×28 is a candidate working region, not a proven packed footprint or an18×30 PCB. No external-metal distance is guaranteed by the source. Keep the antenna at the outboard polymer end; parent must model the fixture, XLR shell, fasteners, capacitor and cable throughout assembly positions, then measure detuning across those distances. No universally flush fit or shrink is asserted.

TR101 max2.10×1.35×1.00mm; reproduce SWRA629A's1.26mm reference spacing/0.25mm tracks using its actual drawing. Its four-layer175µm top-ground stackup is a reference, not automatic impedance on our stackup. MCU support and crystals still need placement. The25×6mm power allocation remains independently unresolved. Removing a tiny switch saves control/lifecycle complexity; it does not establish a smaller housing.

## Cross-sheet and service contract

`pin-allocation.csv` lists actual package contacts. DIO4/pin9SERVICE differs from DIO3/pin8ROM. DIO18/pin28 staysNC, reserved for INPUT_FAULT_N only after the power owner provides a power-off-safe interface; the existing always-on pullup cannot simply feed an unpowered MCU. cJTAG24/25 retained. MCU RESET_N35 takesRESET_OK; J_FACTORY.5 operatesU16.MR. SPI flash usesDIO8–11, package14–17; proposed DMX UART usesDIO12/13,18/19. No factory UART signal is reassigned to externalSSI. ROM is not anRDMloader. Resident-loader CCFG/backdoor, flash write/erase protection and authentication remain future configuration work; externalflashWP does not protect MCU flash.

The verifier freshly exports power/DMX into **our** `integration-inputs/` without mutating their owners' files. It records source hashes and rejects a source changing during export. It verifies actual endpoint connections, safe gate paths, R4seriesEN path, grounds, and aliasesMCU_DMX_TX→DMX_TX,MCU_DMX_RX→DMX_RX,MCU_RE_N→DMX_RE_N. These separate projects are not falsely labelled a single full-product ERC. Whole assembly/PCB qualification remains absent.

## Prototype protection and termination update

The current minimal ESD/protection basis and captured manual120ohm termination are in [footprint-stage design](../footprints/DESIGN.md). No externalSM712 or ADM2795 redesign is selected. Full system ESD/surge immunity is not claimed. MCU and antenna source lands are now assigned; IPC/support lands are now source-backed; five tuning lands are explicitly provisional pending MPN-specific applicability approval.

## Acceptance limits

Real KiCad10.0.7 export:26 components (25 physical, one power interface),57 nets including NC; zero ERC violations/exclusions. Independent checks cover49 MCU contacts,46 retained TI reference connections,12 antenna/match connections, MPNs, removed switch/control and actual cross-sheet endpoints. `antenna_prototype_capture=true`, `matching_values_qualified=false`, `full_product_acceptance=false`. See `dualfeed-implementation-receipt.json`. No power budgets or CAD geometry changed.
