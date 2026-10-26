# Partial placement candidate — not a manufacturing board

One placement of the current 37 physical MCU/RF/DMX parts on the unchanged 90 × 28 × 1 mm PCB. Coordinates are the CAD coordinates directly: x4–94, y23–51; component side corresponds to CAD z11. Four Ø2.2 NPTH holes are at (7,26), (73,26), (7,48), (73,48). No baseline files were edited.

`candidate.kicad_pcb` embeds the actual editable library footprints. `generate.py` imports the two actual KiCad XML exports, rather than reconstructing nets from prose. `inputs.json` freezes source hashes, positions, assignments and statuses. `verify.py` independently reads the source XML again and checks all 156 numbered pads. DMX_TX/RX/RE_N aliases merge only their corresponding MCU nets. DMX_DE_SAFE and DMX_POWER_EN remain separate from MCU requests: the omitted power gating circuitry must connect them. All 67 imported nets are partial; they are not a complete product netlist.

Actual KiCad 10.0.7 DRC: **zero geometric violations, 89 unconnected items**. There are zero tracks, zero vias and no ground pours. This is not a clean manufacturing DRC result. Default KiCad clearance constraints are merely placement screening, not selected fabrication or isolation rules. Courtyard AABBs additionally pass the independent board-edge/cap/USB reserve check. No exclusions were installed. Four mechanical footprints are additional to the 37 electrical components.

## Mechanical and routing disposition

- U5 is rotated 90° at (18,36). Its isolated pads face the top board edge; logic pads face downward. The drawn x4–26/y34.8–37.2 strip is a reserved routing corridor, **not a claimed creepage rating**. No copper crosses it because no copper is routed. Only the isolator bridges the two sides. Ground pour setbacks, copper/slot geometry, actual creepage and clearance remain PCB design work.
- Propose moving the DMX lead entry from (72,20) to **(10,20)**, with the isolated wire landing approached near (10,24). This keeps the wire on the isolated side instead of crossing the logic/RF region. These are proposed enclosure/entry coordinates, not a captured connector or CAD modification. Strain relief, hole spacing, landing pads and separation from the mounting screw at (7,26) must be designed; no wire landing footprint is claimed.
- S_TERM is at (18,26.6), rotated 180°, with actuator toward the y23 edge. Reserve a polymer tool-access path approximately x16.35–19.65 from y20 to the actuator, separate from the proposed cable entry. Its actual courtyard is checked; enclosure access and travel are not proven.
- **S_TERM remains provisional.** Parent recovered the official active product page and 498359-byte PDF, SHA256 `6a758d151b7eee7f8cd59594bd92cfec4c9b1470e0743094f185f19e7ac2a868`. The manufacturer mechanical-pad inner gap is 1.13 mm; the current footprint has 1.41 mm, a 0.28 mm discrepancy. This placement intentionally does not silently repair the library. NPTH-to-row vertical registration still needs verified correction. Signal pads and Ø0.9 NPTH spacing are not the disputed dimensions. Active lifecycle does not approve these lands.
- Capacitor/body/lead projection x26–61/y23.5–37 is kept free of component courtyards. The actual cap bottom is z12, only 1 mm above the nominal PCB top. No component height or assembly tolerance proof is inferred. USB x36.5–48.9/y45.1–51 is also free. Both rectangles are drawing-layer constraints enforced by the verifier, **not native copper keepout rules**.
- A101 center (91.6,37), −90°, leaves 0.6 mm outer-pad copper-to-board-edge clearance. Its embedded provisional antenna keepout transforms to x83.4–93.4/y23–51. Preserve the additional empty strip to x94. Six NC lands retain distinct nets, with no ground connection. Matching components lie inward of the keepout; no other component is placed there.
- This antenna placement is a prototype interpretation, not the Johanson 30 mm reference board: actual width remains 28 mm. Fixture metal, housing, ground length/width, feed bends, tuning and port coupling require measurement. No claimed impedance or RF performance. Five RF tuning parts now use manufacturer-dimensioned Coilcraft/Murata lands; RF substitution/tuning remains unqualified. See ../footprints/REPLACEMENT-PASS.md.
- MCU and IPC are oriented toward each other but the balanced connections are **not routed** and the TI/Johanson reference geometry has not been reproduced. Direct balanced paths, RF feed crossings, crystal loops, decoupling vias and DC/DC current loops remain placement-refinement gates. Geometric fit does not establish acceptable electrical placement. No invented controlled-impedance stackup is embedded.

Power/buffer circuit, external SPI NOR, USB power connector, service/ROM/reset/cJTAG pads, cable landing pads and their decoupling/controls are **unplaced**. Empty space is not an allocation proof for them. No enclosure shrink, whole-product fit, fixture compatibility, assembly accessibility, RF qualification or release claim follows from this candidate.

## Reproduce locally

Run from the repository root, using the existing Flatpak installation:

```sh
flatpak run --command=python3 org.kicad.KiCad hardware/compact-dmx/eda/placement-candidate/generate.py
flatpak run --command=kicad-cli org.kicad.KiCad pcb drc --format json --severity-all -o hardware/compact-dmx/eda/placement-candidate/drc.json hardware/compact-dmx/eda/placement-candidate/candidate.kicad_pcb
flatpak run --command=python3 org.kicad.KiCad hardware/compact-dmx/eda/placement-candidate/verify.py
flatpak run --command=kicad-cli org.kicad.KiCad pcb export svg --layers F.Cu,F.Fab,F.CrtYd,Edge.Cuts,Dwgs.User --mode-single --page-size-mode 2 -o hardware/compact-dmx/eda/placement-candidate/placement.svg hardware/compact-dmx/eda/placement-candidate/candidate.kicad_pcb
flatpak run --command=kicad-cli org.kicad.KiCad pcb export pdf --layers F.Cu,F.Fab,F.CrtYd,Edge.Cuts,Dwgs.User --mode-single -o hardware/compact-dmx/eda/placement-candidate/placement.pdf hardware/compact-dmx/eda/placement-candidate/candidate.kicad_pcb
```

KiCad DRC without `--exit-code-violations` returns zero even with unconnected items; use the JSON counts, not its exit status, as evidence. `placement.svg` and `placement.pdf` show actual lands/courtyards and dimensioned coordinate annotations. `validation.json` retains measured courtyard bounds and input-mutation checks. The source footprints' manufacturer/reference provenance remains in the parent footprint ledger; no new package dimensions were invented here.

## Corrected candidate connectivity and partition

The initial candidate failed to normalize leading `/` in exported hierarchical labels, so its claimed TX/RX/RE aliases were not actually merged. The corrected generator strips leading slashes before applying the explicit aliases. Independent semantic assertions now require actual board U5.2=U1.19, U5.4=U1.18 and U5.5=U1.12, and retain separation between MCU requests and DE/power gates. Net count is 67; the three newly joined unrouted nets increase KiCad's unconnected count to 89.

The first placement also put termination resistors across/on the logic side of the drawn corridor. R_TERM1 and R_TERM2 are now at (6.5,32.2) and (9.2,32.2), both rotated 90°; C4 moves to (11.8,26.4). The verifier checks every non-U5 courtyard against the corridor and requires every part carrying isolated bus/supply/termination nets to remain wholly within x4–26 and above y34.8. C3, C4, both terminators and S_TERM pass. This is a geometric partition check, not a creepage certification. Source footprints, provisional switch status, omitted hardware and zero routing remain unchanged.

The PNG preview is cropped from the actual PDF at higher resolution with `pdftoppm -scale-to 4000 -x 0 -y 290 -W 1480 -H 540 -singlefile -png`; the SVG/PDF remain editable/vector placement exports.

## Stable export fingerprint correction

`inputs.json` retains raw export SHA256 values for provenance. Acceptance uses an additional parsed-XML fingerprint with **only top-level `design/date` text blanked**. All other parsed fields remain included, including values, MPNs, footprints, electrical pin types, nets and metadata. Source schematic and library footprint files remain raw-SHA checked. XML serialization normalizes parser formatting; it does not discard other XML elements/attributes. The generator establishes these fingerprints when producing the board, not during verification.

The verifier independently compares actual board values/footprint identities with the current exports and assignment contract, in addition to its existing pad/net semantics and spatial checks. In-memory regressions confirm a date change passes while value, footprint, net name, pin, pin type and other metadata mutations fail the fingerprint. No active source is mutated for these negative checks.

After generating this candidate once, both real netlists were exported again with KiCad10.0.7. The unchanged board passed verification with both raw export hashes different and both stable fingerprints equal. Parent subsequently ran the whole-package validator successfully, then verified the unchanged board again without regeneration or blind manifest refresh: both raw export hashes differed, all156 pads passed and no source mutations were reported. Board SHA256 `fe577602e2891b7c78ec8fba5d71f8648076cadccff2774c96e2673c6fb15a2b`; parent evidence `.tools/checks/revd-placement-parent/post-package-stable-receipt.json`. This closes the date-only false mutation failure. The CLI emitted an existing schematic annotation warning during export; exports completed and their electrical fingerprints remained identical. This pass does not claim that warning was repaired.
