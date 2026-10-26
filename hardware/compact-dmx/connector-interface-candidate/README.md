# CI-R1 — stationary connector interface contracts

Six manufacturer chassis interfaces were fetched as actual official STEP files, inspected in FreeCAD, and cross-checked against their manufacturer drawings. **None establishes a complete Ø48 ×24 mm end assembly.** Bare nominal rear depths already exceed 24 mm. The two Neutrik sets remain useful inputs for a longer termination allocation; the examined NEMA flanged set additionally needs Ø63.5 mm flanges. No baseline design, part selection, mains circuit or enclosure has been changed.

This is a source/geometry contract, not an assembly release. The 24 mm blank is an allocation, not an actual panel thickness or an available 24 mm cavity. Module installation, source fault-energy, thermal and collar gates remain independent and unresolved. No unfinished Astra geometry was used.

## Candidate contracts

| Variant | Upstream barrel interface and mate | Downstream barrel interface and fixture jumper | Nominal drawing allocation, excluding wire/terminal access |
|---|---|---|---|
| Classic blue/gray powerCON, current XX chassis | **NAC3MPXXA**, male A/blue inlet; cable **NAC3FXXA-W-S**, socket contacts | **NAC3MPXXB**, male B/gray outlet → **NAC3FXXB-W-S** B cable connector — cord — **NAC3FXXA-W-S** A cable connector → fixture blue/A inlet, e.g. **NAC3MPA-1** legacy or **NAC3MPXXA** current | Each flange 26 ×31; each rear depth **30.4**; flange thickness 4.5; nose 2.55 beyond front flange. Rear-depth excess **6.4 mm** at each end. |
| TRUE1 TOP | **NAC3MPX-TOP**, male inlet; female cable **NAC3FX-W-TOP** | **NAC3FPX-TOP**, female outlet → male cable **NAC3MX-W-TOP** — cord — female **NAC3FX-W-TOP** → fixture **NAC3MPX-TOP** male inlet | Inlet flange 26 ×31, rear **31.2**, total 38.2. Outlet flange 35.4 ×35.4 with rounded corners, rear **32.8**, total 43.0. Rear-depth excess **7.2 /8.8 mm**. |
| NEMA5-15, one flanged comparison set | Leviton **5278-C**, male 5-15P inlet; **5269-C** female 5-15R cable connector | **5279-C**, female 5-15R outlet; **5266-C** male 5-15P at source end of a jumper, **5269-C** female at fixture end; accepts a fixture 5-15P inlet/attached plug | Both flanges **Ø63.5**, fixing pitch 53.6; rear **45.3 /43.6**. Excess over Ø48 **15.5 mm**, rear-depth excess **21.3 /19.6 mm**. Not a drop-in barrel end. |

All arrows above describe compatible **mating interfaces**, not conductor construction instructions. The classic A and B cable connectors both have socket contacts; their functional IEC connector/plug-connector names and keyways differ. Gray B never mates directly with blue A. TRUE1 is a separate geometry and contact-gender system. A downstream jumper is required where the fixture has an inlet; direct fixture support by a barrel or mains connection is not established.

The exact selected mounting interfaces are the six table parts, with the six named cable mates only as external mating references. No second candidate set was screened. The NEMA flanged set is a geometry comparison, **not a silent substitution for the baseline approved molded-pigtail intent**. Exact molded cord PNs, cord approvals, cord exit/retention and fixture-support arrangements remain missing. Field-wireable 5266-C/5269-C parts are not molded cords and are not qualified as custom barrel-mounted contacts.

## Source and rating limits

Current manufacturer product pages link every cached model. `source-manifest.json` records exact URLs, retrieval dates, download version query strings, hashes, content types and available Last-Modified headers. `cad-inspection.json` records STEP FILE_NAME timestamps/schema/units and exact import results; those timestamps identify models, not a promise that their drawings were revised simultaneously. Original files remain in ignored `sources/`, following the hardware source-cache policy. Vendor copyright remains; no redistribution license or public CAD publication is asserted. The editable import-only library is `sources/manufacturer-models.FCStd`; original `.step` files are the STEP deliverable, unmodified. Orthographic SVGs are local evaluation views.

- **Classic:** [NAC3MPXXA](https://www.neutrik.com/en/product/nac3mpxxa), [NAC3MPXXB](https://www.neutrik.com/en/product/nac3mpxxb), [FXXA mate](https://www.neutrik.com/en/product/nac3fxxa-w-s), [FXXB mate](https://www.neutrik.com/en/product/nac3fxxb-w-s), BDA 639 V4. Chassis pages state EN60320-1 16 A /250 VAC and cUL60320-1 20 A /127 VAC, plus separately listed UL1977 20 A /250 VAC. These are different approval conditions. The page permits live/load mating with FXX-series mates. The [manufacturer compatibility notice](https://www.neutrik.us/en-us/news/neu-powercon-xx-iec-60320-1-konform) explicitly permits FXX mating with older blue/gray receptacles but excludes CBC for those combinations. The current [family page](https://www.neutrik.com/en/neutrik/products/powercon-r/powercon-r-xx-series) marks original MPA/MPB and FCA/FCB parts discontinued and warns FCA/B and FCA/B-1 have no CBC. Treat a legacy fixture combination as de-energized mating; a new cable does not upgrade that fixture.
- **TRUE1:** [inlet](https://www.neutrik.com/en/product/nac3mpx-top), [outlet](https://www.neutrik.com/en/product/nac3fpx-top), BDA 544 V3 /545 V3 supply the mating assignment and backward compatibility with preceding TRUE1. Chassis pages state EN60320-1 16 A /250 VAC and UL498 20 A /250 VAC; cable pages have their own UL60320-1 conditions. CBC is stated. IP65/UL50E type4 is conditional on the specified cap/mated arrangement; neither the barrel nor its USB opening inherits it. BDA 559 V3 (2023-06-28) warns worn/damaged keying can permit incorrect insertion; complete locking and inspection access cannot be designed away.
- **NEMA:** [5278-C](https://leviton.com/products/5278-c), [5279-C](https://leviton.com/products/5279-c), [5269-C](https://leviton.com/products/5269-c), [5266-C](https://leviton.com/products/5266-c). Exact NEMA gender/class matches, 15 A /125 VAC, dry-environment product conditions. The5266/5269 mate selection is an engineering inference from Leviton's declared matching NEMA5-15P/R classes; the retrieved files do not explicitly recommend those PNs as paired sets. Leviton states full-rated-current interrupting capability; this does not establish a locking or weatherproof barrel. A 5-15 connection has no default positive mains lock. The owner's durable locking rotation requirement remains on the separate collar.

No connector rating is a through-feed rating, a product certificate, or permission for energized assembly work. PE and mains remain stationary. Insulation, accessible-part protection, strain relief, pull/torque endurance and complete product conformity need their own design and assessment.

## Geometry datums and finite access

`contracts.json` is the machine-readable contract. Its mounting-plane faces were identified by matching the **drawn flange shoulder** to planar faces, not by taking a bounding-box end as an installed-depth datum. Source coordinates are retained; the mating plug is not placed against a guessed contact plane.

| Part | Vendor axial coordinate / outward direction | Panel shoulder entity, nominal coordinate | Drawing / panel-cutout facts |
|---|---|---|---|
| NAC3MPXXA | Z /+Z | Face460, Z=0 | ST-NAC3MPXXA, 24.10.19; ≥Ø24, fixing pitch 19 ×24 ±0.1, ≥Ø3.2 holes |
| NAC3MPXXB | Z /+Z | Face680, Z=0 | ST-NAC3MPXXB, 22.10.19; same cutout |
| NAC3MPX-TOP | Y /+Y | Face178, Y=0 | ST-NAC3MPX-TOP, 03.05.18; BDA544 V3: ≥Ø23.8, 19 ×24 ±0.1, ≥Ø3.2 |
| NAC3FPX-TOP | Z /+Z | Face105, Z=0 | Drawing20003608 approved02.03.2023: Ø28.7 ±0.1; 24.4 ×24.4 ±0.1, ≥Ø3.2. BDA545 instead states ≥Ø28.7: tolerance/minimum interpretation remains for fabrication review. |
| 5278-C | X /−X | Face4, X=−19.837267... | CATSTD-05278-00C-D01 rev1; flange Ø63.5, slots4 ×5.9 on53.6 pitch. PK-93763 gives panel opening43.66–44.45. |
| 5279-C | X /+X | Face71, X=−4.343512... | CATSTD-05279-00C-M01 rev1; same flange/slot/opening class. The2.4 nose callout is beyond the **front** flange, not the total panel projection. |

Face IDs depend on these exact source hashes and FreeCAD/OCCT import. Manufacturer STEP entity IDs for units and FILE_NAME identity are preserved in the inspection record. Face numbers here are imported FreeCAD geometry entities, not a claimed mapping to original STEP ADVANCED_FACE numbers. These are mounting datums with drawing correspondence; **contact mating planes, insertion overlap, latched combined lengths and hand envelopes remain unknown**. Model outlines alone do not define a release-ready cutout or mating datum.

Bare-part comparisons remain nominal. Neutrik drawings call general ISO2768 tolerances; no maximum enclosure is invented from the nominal CAD. The two classic STEP rear extents are about30.05 /29.95 versus30.4 drawing depth; retain the drawing allocation and resolve the revision discrepancy before machining. Leviton drawings use inch-governing dimensions and rounded metric references: do not silently select the smaller rounded value for toleranced tooling. Neither issue can make a24 mm end acceptable.

The Neutrik flange outlines may be plausible inside Ø48 at nominal geometry; the TRUE1 outlet's rounded corners must be evaluated from its actual outline, not a35.4-square diagonal. This pass does **not** establish wall ligaments, fastener bosses, rear shells, seals or an assembled Ø48 fit. NEMA's actual63.5 flange directly exceeds Ø48.

Manufacturer-stated mechanical access inputs, not assembly instructions:

- Classic chassis:3/16-inch tabs; product accessory NLFASTON is specified for4.75 ×0.51 tabs. No exact insulated crimp-terminal length, sleeve or insertion-tool clearance has been captured. BDA592 V1,2020-09-02, specifies countersunk M3 /4-40 examples and50 Ncm mounting limits for both front/rear assembly. It supplies no permissible24-mm termination cavity.
- TRUE1 chassis:1/4-inch FASTON tabs; BDA545 specifies6.35 ×0.8 and40 Ncm mounting torque; BDA544 also states40 Ncm. Selected no-suffix bodies retain insulation dividers; WOT bodies are different, unselected parts. Connector rear depth does not include female terminals, insulation, wire bend or access to install/remove terminals.
- Classic -S cable mates:6–12 mm cable OD,1.5–2.5 mm² /16–12 AWG, with the BDA639 cable-type/gauge matrix controlling the actual compatible combination. The linked manual labels early pages V4 but its final document footer V3 (2024-05-08); that inconsistency is retained in the source inventory. Its finite preparation lengths are24 mm L/N,27 mm PE and9 mm stripped; T8 terminal access and a27 mm hex tool are stated. These are inside a full cable connector, not a compact bare contact insert. No approved custom panel mounting of these cord parts is inferred.
- TRUE1 cable mates:6–12 mm cable OD; BDA541/542 have their own cable matrix,20 mm L/N,23 mm PE and8 mm strip dimensions. BDA541 shows13 mm wrench access and2.0 Nm bushing torque. Connector grasp/rotation, cap, strain relief and cable bend need external allocation; no universal bend radius is stated.
- NEMA chassis:18–10 AWG terminal accommodation, rear screw access,10–14 in-lb torque on product pages. The installation sheet specifies a14 mm nominal stripped segment and copper/copper-clad restrictions. This is not a14 mm free-space allowance. Terminal screw withdrawal, driver axis, conductor entry, insulation and bend sweep remain unmeasured. The5269-C page contains inconsistent cord ranges in descriptive text versus technical table; no cord OD is selected from that conflict.

## What the CAD does and does not establish

Twelve original STEP files were imported: six chassis candidates and six **specified external mates**, not twelve alternative mounts. Millimetre Neutrik units and Leviton inch conversions were inspected. Leviton's5266-C product page intentionally links a shared`CATSTD-05266-00X-M01` model; exact finish/variant identity beyond the official linkage remains a procurement/CAD gate.

The automatic bounding box can include spline/control-point excess. `sampled_mesh_bbox_mm` is a0.03-mm tessellation screen, **not a certified maximum**. Nominal axial lengths of the separate mates are roughly79.25 mm for each classic FXX,77.6 /77.1 mm TRUE1 F/M,70.104 /71.374 mm NEMA R/P. These do not equal their additional length after mating. No arbitrary cable-bend/tool reserve was added to call an assembly fit.

FreeCAD reports the two TRUE1 chassis imports invalid as whole shapes; 5278-C and several cable mates are surface/shell geometry without a closed solid. Original geometry is preserved; no healing or synthetic solid replaces it. These files still expose actual surfaces/edges for reference measurements. They cannot support reliable solid Boolean collision acceptance. The JSON records every import's actual result and face references. The FCStd is a library of independent vendor-coordinate objects, **not a spatial assembly**. SVGs are editable orthographic projections in those local frames, with no invented installed plug position.

## Missing datums and next integration boundary

All three24 mm allocations remain unqualified. Parent can use these contracts to allocate **longer, separately terminated stationary ends**, or preserve a separately qualified pigtail architecture; neither is implemented here. No collar/enclosure dimension has been changed.

Before an assembly CAD replacement: resolve exact terminal/sleeve/cord/strain-relief parts, rear wire/tool sweeps and bend radii; obtain mated reference planes and installed plug/cap/hand envelopes; settle panel thickness/front-vs-rear mounting, seals/bosses and tolerances; resolve model validity/revision issues; retain continuous independently secured stationary PE and inspectable insulation barriers. NEMA additionally needs a different flanged envelope or an exact approved molded-cord/exit contract, still unresolved. Connector retention, total mains temperature/current limits, touch protection and conformity remain product-level gates. Source fetch is not design release.

## Reproduction

Run from repository root; all writes stay in this candidate:

```sh
QT_QPA_PLATFORM=offscreen /home/juicebox/.local/bin/freecadcmd /home/juicebox/Nova-Link/hardware/compact-dmx/connector-interface-candidate/inspect-cad.py
QT_QPA_PLATFORM=offscreen /home/juicebox/.local/bin/freecadcmd /home/juicebox/Nova-Link/hardware/compact-dmx/connector-interface-candidate/check-saved-cad.py
python3 hardware/compact-dmx/connector-interface-candidate/verify.py
python3 hardware/compact-dmx/connector-interface-candidate/make-views.py
```

`receipt.json` contains actual commands/results, source/protected/artifact counts and explicit remaining gates. `SHA256SUMS` inventories the current deliverable state, excluding itself. This task has no circuit/PCB changes and consequently no new ERC/DRC claim.
