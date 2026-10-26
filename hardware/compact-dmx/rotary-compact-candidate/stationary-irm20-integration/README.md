# STATIONARY-R1 — conditional IRM20 packing prototype

[Dimensioned drawing](stationary-integration.pdf), [editable native assembly](stationary-integration.FCStd), [STEP](stationary-integration.step), [design and limitations](DESIGN.md), [independent checks](checks.json), [receipt / exact hashes](receipt.json).

The original V_PLUS maximum-lead/trunk intersection is removed without altering the core, trunk or endcap blanks. Carrier bottom becomes Z−11.00; nominal module bottom−9.00. Actual four pins, conservative min/max lead solids, apertures/lands, dielectric sled/film, adjustable retention, finite R9 insulated secondary wires, split sleeve and strain-clamp envelopes are captured. The preserved Ø4 feedthrough remains X92,Y0. External wire endpoints are X91.5,Y±.8,Z27.5, tangent+Z.

This is **partial manufacturing integration**. Minimum bounded gaps are .15mm lead/deck, .075mm film/trunk and .465mm body/nominal bore; the sampled wire/sleeve screen gives .0112mm under tight proposed fixture allocations. None is a certified insulation or fabrication clearance. The conservative apertures still require a validated solder/PTH process; source pins are not falsely modeled as connected to their copper rings. Primary harness/fuse/connectors, sleeve material/edge retention, whole-sled grip, tool/forming sequence, endcaps and sealed thermal/safety qualification remain UNMET. A preformed wire loop cannot slide through the intact core: in-core forming is a separate physical gate. Generic MEAN WELL installation clearances are not qualified by this model.

All422 scoped protected inputs are unchanged. No parent/CAD/BOM/other-candidate file was written. No architecture or module-family change, new mains rating, new core hole, moving mains/PE, tool installation, hardware/firmware or git publication.

```sh
bash hardware/compact-dmx/rotary-compact-candidate/stationary-irm20-integration/validate.sh
```

`build.py` is the editable construction source. `verify.py` independently reads the actual saved CAD and original baseline geometry; it does not import the builder. `project.py` reads saved edges for `draw.py`; no illustrated body-only fit substitutes for the pin, copper, leadout and retention checks. The min/max source document is deliberately separate from the nominal assembled document.
