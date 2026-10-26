# CME-R1 — Neutrik installed-mating envelope hold

This bounded pass does **not** establish a unique installed rigid transform for any of the four selected pairs. Installed front extent, locked transverse envelope, mating plane, latch stroke and complete terminal rear depth remain unknown. No paired CAD/STEP or continuous insertion/rotation acceptance is issued. The 24 mm axial blanks remain unsupported: the bare chassis rear depths already exceed 24 mm, before insulated terminals, wiring and access.

| Chassis / specified mate | Panel reference in original mm CAD | Bare rear, drawing nominal | Mate standalone length | Installed extent |
|---|---|---:|---:|---|
| NAC3MPXXA / NAC3FXXA-W-S | +Z, Face460 at Z=0 | 30.4 mm | 79–82.5 mm | HOLD |
| NAC3MPXXB / NAC3FXXB-W-S | +Z, Face680 at Z=0 | 30.4 mm | 79–82.5 mm | HOLD |
| NAC3MPX-TOP / NAC3FX-W-TOP | +Y, Face178 at Y=0 | 31.2 mm | 77–80 mm | HOLD |
| NAC3FPX-TOP / NAC3MX-W-TOP | +Z, Face105 at Z=0 | 32.8 mm | 77–80 mm | HOLD |

The panel shoulders are mounting references, **not contact mating planes**. Bare rear dimensions come from the frozen manufacturer drawings, not maximum STEP bounding boxes. They retain drawing tolerances; no smaller allocation is justified by a shorter nominal CAD model. The cable-connector lengths are variable standalone dimensions, not projections from a mounted chassis. General drawing tolerances remain applicable. None is a completed installed maximum envelope.

## What was checked

Eight exact manufacturer STEP models and their page associations were reused from immutable CI-R1. All declare millimetres. `inspect-datums.py` records named planar faces, oriented normals, coaxial cylinder axes and two meridian sections per model. `sources/unplaced-references.FCStd` retains eight separate, identity-placed supplier shapes with original hashes. These unrelated source coordinate systems are deliberately **UNPLACED**, not an assembly. Original vendor STEP files remain in the ignored CI-R1 cache. No vendor STEP, FCStd or traced contour is added to a public tracked directory; `sources/` is ignored here as well. Neutrik copyright/title blocks and file provenance are retained in the private cache. No redistribution license is inferred.

`check-saved-references.py` independently reopens the saved document and frozen CI-R1 document, checks source hashes, STEP units, identity placements, topology, area/volume/bounds and named face planes. It records eight isolated plane probes. It does not heal models or assert an assembly Boolean pass. The two TRUE1 chassis whole-shapes remain invalid; both TRUE1 cable models remain open, zero-solid surface references. The four powerCON XX shapes are valid single solids. This validity classification does not establish electrical engagement or a mating pose.

Coaxial body surfaces establish candidate body axes but leave axial translation and rotation about that axis free. The cable body's outward direction is +Z for FXXA/B, +Y for FX-W-TOP and −X for MX-W-TOP. Aligning the latter with the outlet +Z would require an axis-only orientation change; it still supplies neither locked clocking nor seating depth.

For a concrete rejected shortcut, MPXXA Face466 lies at Z=7.05 and FXXA Face247 at Z=8.7. Translating that isolated annular plane by −1.65 mm yields zero radial overlap at the source clocking. The mate annulus has 12.8/13.05 mm circular boundaries. Other isolated planes produce positive overlap at quite different translations: Face337/Face2435 gives −2.15 mm and 50.69984 mm²; Face560/Face2435 gives +20.35 mm and 95.57412 mm². These are algebraic probes, **not competing valid poses**. Neither proves the actual stop, key path, contact overlap or latch engagement. No allowed play or finite insertion-depth interval follows from these tests. The other pairs' named probes and residual plane-normal alignment are recorded in `saved-reference-check.json`; they likewise do not establish stops.

The bounded pass inspected the existing maker pages, eight models, four chassis drawings, assembly/mount/safety manuals and guide, and fetched only four exact mate drawings. It did not establish a matched set of key, contact, stop and latch surfaces sufficient to remove these ambiguities. This is a data/constraint hold, not proof that a more extensive manufacturer-defined assembly is impossible.

## Newly closed standalone facts

The exact FXXA/B drawings give Ø26.5 body, 30.3 total transverse height and 16.9 from axis to top (derived opposite extent 13.4 mm). TRUE1 FX gives Ø26.5, 32 total, 17 to top (opposite 15); MX gives Ø26.5, 35 total, 19.7 to top (opposite 15.3). These as-drawn nominal figures exclude an unknown operated-latch sweep, hand clearance and installed clocking. They cannot be used as certified maximum installed cylinders.

The two new powerCON drawings identify models 30008899/30009234, while the page-linked STEP PRODUCT identifiers are 30010047/30010049. CI-R1 also records the TRUE1 outlet drawing/STEP identity difference; the male cable STEP identifies NAC3MX-W_SW0002. The exact product-page links justify using these files as references; matching every drawing revision/configuration is **not** established. `source-links.json` retains original model headers, URLs, retrieval times and hashes. `new-source-manifest.json` identifies the four added drawings; the versions are summarized in `drawing-identities.json`.

## Mating and finite access contract

Both MPXX chassis have male contacts, with blue A input and gray B output keys. Each takes its specified FXXA or FXXB socket connector; B is not the mate for a blue/A fixture inlet. A downstream cord therefore uses FXXB at the barrel outlet and an appropriate FXXA at an A-key fixture. The selected XX/XX combinations have the maker's stated breaking-capacity conditions; that does not transfer to older legacy fixture couplers or approve this barrel. TRUE1 MPX male inlet mates FX female; FPX female outlet mates MX male. BDA559 requires notch/guide alignment, rotation in the direction illustrated and a fully locked audible indication. It gives no numeric source-coordinate locked angle, axial stop tolerance or latch sweep. A silvery-tab illustration is not a dimensioned motion envelope.

The following are manufacturer assembly facts, **not energized-work instructions or additional clearance grants**. The manuals specify cable OD 6–12 mm subject to their cable type/gauge matrix. Classic preparation is L/N 24, PE 27, stripped 9 mm; TRUE1 is 20/23/8 mm. Classic terminal tooling is T8, 0.7 Nm; the bushing uses 27 mm hex/HTLACA or HTLACB, 2.5 Nm. TRUE1 bushing tooling is 13 mm/HTAC, 2.0 Nm, and terminal torque is 0.7 Nm. Internal preparation lengths do not add a known rear terminal envelope or define cable bend space. Chassis mounting instructions give 50 Ncm for the classic countersunk examples and 40 Ncm for these TRUE1 parts; no tool sweep is dimensioned.

Classic tabs are 4.75×0.51 mm; NLFASTON is maker-listed, but a qualified insulated terminal/sleeve assembly profile and its insertion/tool envelope were not established. TRUE1 tabs are 6.35×0.8 mm, with the exact insulated terminal/sleeve part and envelope likewise open. No arbitrary rear bend radius, hand cylinder or driver clearance is introduced. Manufacturer-required hand clearance and proposed hand clearance are both null in the contracts.

## Concrete remaining data

For each pair, obtain a labeled installed panel-to-cable datum or sectioned paired assembly identifying the actual stop, locked relative key/latch angle and state, allowable play/tolerances, and contact engagement. A defined insertion/rotation path and operated latch envelope are also required. Rear packaging additionally needs an exact qualified insulated terminal/sleeve profile and termination/tool/cable-bend envelope. This pass authorizes no vendor outreach. Until those data exist, retain the four HOLD contracts; do not resize a mating transform to fit a blank. NEMA, all source circuits and Astra's unfinished mechanical outputs were untouched.

The direct 233-file start snapshot includes every CI-R1 file and both frozen S12 candidate directories. CI-R1's inherited 96-file list is checked separately: 95 match and the parent-owned `docs/hardware/DMX_Dongle_and_Power_Barrel.md` differs; both expected/current hashes are retained in `inherited-protection-status.json`. That inherited document baseline is not silently refreshed. No unfinished Astra output was consumed.

Run `./validate.sh` from this directory. `receipt.json`, `verification.json` and `SHA256SUMS` distinguish provenance/check success from unresolved mating/fit acceptance. This is a reference-data contract, not product fit, mains assembly or manufacturing release.
