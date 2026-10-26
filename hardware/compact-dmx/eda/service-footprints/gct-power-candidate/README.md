# Proposed GCT power connector + retained NOR placement

Only this directory changes. GCTUSB4125-GF-A is proposed; Hirose is historical for this proposal, not silently replaced in active BOM/circuit/CAD. New >=1.5A source qualification belongs to Sol's separate power candidate and is **not captured/placed here**. Connector current capability does not itself advertise or detect source current.

## Primary evidence

Exact manufacturer product page `https://gct.co/connector/usb4125` lists Active, top mount, six contacts. Browser DOM receipt retained. Direct CLI hit403; existing T3 browser same-origin fetch recovered **Download Drawing57** `https://gct.co/download?name=USB4125.pdf&type=PDFDrawing` (469688bytes) and spec `https://gct.co/download?name=usb4125-spec.pdf&type=PDFSpecification` (395353bytes), both HTTP200. PDFs are locally hashed in sources.json; the initial product.html is failed CLI/Cloudflare evidence, not lifecycle evidence.

DrawingUSB4125, revisionA6 dated20/11/25, sheet1/2: recommended PCB layout tolerance±.05mm; exact blank stake suffix means1mm (not0190). Product specRevA3,20/12/24: collectiveVBUS3A, collectiveGND4.25A, CC pins1.25A; operating−30…85°C. Spec6.1.4 assesses current with maximum30°C connector outside-surface rise under its stated loading. This is component evidence, not a device thermal/USB compliance test. Both VBUS and bothGND lands must connect with suitable copper. No data contacts exist. Contact resistance40mΩ initial/50mΩ after test. Full application derating and selected-board thermal behavior remain untested.

## Exact copper and pin contract

Datum(0,0) is midway between rear shell stakes; +Y toward mating opening. Recommended signal lands all length1.20, centredy−.08 (top−.68). Left-to-right B12(x−2.75,width.80),B9(−1.52,.76),A5(−.50,.70),B5(+.50,.70),A9(+1.52,.76),A12(+2.75,.80). Four plated slots atx±4.32,y0/3.8: drill.60×1.20, copper1.10×1.70. No locator pegs. Six contact identifiers match manufacturer table: A5CC1,B5CC2,A9/B9VBUS,A12/B12GND. Four stakes share localSH, with **GND_USB proposed in this copy only**, following drawing SHELL=GND. Existing active power boundary has no shell terminal; integration still must explicitly adopt this proposal and ESD return layout.

Copper geometry is manufacturer-dimensioned. Solder mask equals copper and SMT paste equals lands as explicit candidate defaults; no manufacturer mask expansion, stencil thickness/aperture or slot paste process was found. Slot paste is omitted pending solder-process choice. These are open DFM gates, not claimed supplier recommendations. Courtyard adds.25mm around maximum copper/body envelope. BodyFab8.94wide×6.8long, y−.4..6.4; dimensioned body length tolerance±.15. Retained NOR is the prior engineering-derived land/stencil footprint, copied byte-for-byte, **not manufacturer recommended lands**.

## Thickness, finite height and required mechanical changes

Primary drawing/spec **do not specify recommended PCB1.00±.10mm**. Do not promote the secondary claim. Default stake lengthS=1.00 +.25/−0 is dimensioned. On nominal1mm PCB, its geometric tip is0…0.25mm below nominal PCB bottom, before seating/solder tolerances. For a proposed (not manufacturer-approved)0.9…1.1mm PCB range, relative projection is−.10…+.35mm. This range needs assembly/retention/process validation. Stake width.80±.10 fits the1.20 slot long axis; stamping thickness/drill tolerance and plating/process must be checked by fabricator.

At CAD PCBtopz11, shell nominal topz14.16 (3.16profile); drawing general two-decimal±.25 gives conservativez14.41 absent a tighter callout. Stake tip reachesz9.75 worst case from the top seating datum; base floorz7 leaves2.75 nominal geometric clearance, before actual mounting/part models. These are coordinate budget checks, not assembly-fit evidence. Current sidecar port x36…50,z9.5…15.5 contains the nominal connector width x38.23…47.17 and above-PCB envelope; thickness/pose/plug clearance remain unqualified.

Placement copy originJ_USB=(42.7,44.6), facing+y. Mating plane y51 exactly at PCB edge; outer case face isy54, leaving **3mm recess**. The drawing mating illustration includes1.85mm shoulder-related spacing; it is not proof that a3mm wall recess accepts a real overmold. Proposal for parent: restore solid PCB in old slotx36.5…48.9/y45.1…51 and revise the local case port/pocket so plug seating clearance is demonstrated with a specified plug model. Do not force the top-mount connector over that void. No CAD mutation or accepted pocket dimension is supplied. Four finite plated slots replace the midmount board notch only in the future mechanical integration.

NOR candidateU2=(32,41.2), courtyardx28.45…35.55/y38.4…44.0, occupies part of legacy unsupported power zone. Power/CC qualification/passives/service pads remain unplaced. It cannot coexist with an asserted complete25×6power allocation without fresh placement. No enclosure shrink or complete board packing claim.

## Actual checks

39 electrical components plus4 mounting holes. Independent verifier compares every original pad position,size,drill,net and component value with the current37-board; six independent antennaNCs, TX/RX/RE semantic joins and DE separation pass. New10connector pads and9NOR pads match proposed contracts and existing selected electrical nets. All existing isolation/cap/hole/RF reservations remain checked. USB reserve may contain only the newly authorized connector; its courtyard projects past the edge by design, while copper-to-edge DRC remains active. Original source36/provisional-switch1 status remains; new NOR land approval is still engineering-derived.

KiCad10.0.7 real DRC: **0 geometric violations,103 unconnected items,0 tracks**. This is not full clean DRC or manufacturing acceptance. Stable date-only fingerprint correction in the original placement directory is preserved untouched. This candidate verifies the original board by raw hash and electrical source by actual pin/net assertions; export timestamps are not a geometry dependency.

Reproduce from repo root:

```
flatpak run --command=python3 org.kicad.KiCad hardware/compact-dmx/eda/service-footprints/gct-power-candidate/generate.py
flatpak run --command=kicad-cli org.kicad.KiCad pcb drc --format json --severity-all -o hardware/compact-dmx/eda/service-footprints/gct-power-candidate/drc.json hardware/compact-dmx/eda/service-footprints/gct-power-candidate/candidate.kicad_pcb
flatpak run --command=python3 org.kicad.KiCad hardware/compact-dmx/eda/service-footprints/gct-power-candidate/verify.py
```

SVG/PDF exports use F.Cu,F.Fab,F.CrtYd,Dwgs.User,Edge.Cuts through `kicad-cli pcb export`; PNG is a cropped rendering of the actual PDF. No ERC claim is made for a new full circuit: no schematic was changed. Outstanding gates include1mm retention/process approval, mask/stencil, shell/ESD integration, qualified1.5A power circuit and layout, switch datum, RF tuning, plug/case accessibility and physical assembly tests.
