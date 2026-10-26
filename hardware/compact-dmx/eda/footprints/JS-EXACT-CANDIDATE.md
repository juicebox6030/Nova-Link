# JS102011SAQN exact-candidate check — no active substitution

Read the parent primary-source receipts and visually inspected `.tools/references/js-official-page4.png`. Verified official PDF SHA256 `0f35cdf47a1f93da71bb7235581f3c77915516488be930d7a3ea4f4942ff0f3b`, revision VL01/14/26, page4. [Official exact product](https://www.littelfuse.com/products/switches/slide-switches/js/js102011saqn) is Active according to the retained parent DOM receipt, dated2026-10-22. The SA variant is side-actuated gullwing SMT, not THT.

Electrical screening passes: maintained SPDT,0.3A6V rating versus the existing approximately50.84mA6V termination corner (about5.9× current margin). Common2, unused1 permits OFF at1–2 and termination at2–3. This does not establish fault-voltage capability or assembled switch endurance.

The land drawing supplies1.2×2.5mm lands at2.5mm pitch, twoØ.9mm holes6.8mm apart, and4mm from the hole row to the far pad edge. It **does not dimension the horizontal offset of the three-terminal row relative to the locator-hole pair**. Expressed without inferred symmetry, choose holes at(0,0),(6.8,0). Pad centres are then(u,−2.75),(u+2.5,−2.75),(u+5,−2.75). Nothing in the labeled layout resolves `u`. Choosing0.9 would assume that the groups share a midpoint.

The body views also give9.0/8.5mm width references and3.6mm depth, but no explicit body-origin-to-locator registration. Side-view3.75mm locates a terminal extent relative to a locator axis; it does not resolve the missing X offset or the complete body origin. The illustrated arrangement is not a substitute for those datums. No pixel measurement or unlabelled symmetry was used. Consequently a complete body/actuator courtyard and its placement relative to the signal pads cannot be claimed source-complete.

Per the bounded task's stop condition, leave active PCM12 circuitry, footprint, BOM and placement untouched. No replacement schematic/export/DRC acceptance is asserted. Current count remains36 source-backed assignments and1 provisional switch. The exact missing evidence is a manufacturer coordinate/native-CAD drawing tying the terminal row and body to the locator axes. No family search, supplier contact, install, CAD change or hardware operation was performed. Even after that evidence, height, underside locator projection, isolated-side packing, polymer access and assembly validation remain required.

Machine-readable evidence and unchanged-active-artifact hashes: `js-exact-candidate-receipt.json`.
