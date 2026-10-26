# Cell protection development capture

Objective: one independent OVP charger disconnect plus cell-local short protection for Eaton HV1625-2R7256-R 25F; editable KiCad/netlist/PDF and source-based pin/fault/threshold/runtime/footprint checks. Hardware only, main b42c0e6284aac734fde851c69146abf73920f337. Write only this directory. Parent owns integration; Astra owns integrated25 placement/cell assembly. No sibling changes, children, threads, installations, hardware, firmware or git publication.

Fixed basis:5V USB-C advertisement>=1.5A,25mA nominal charging,2.448V runtime start,1.705917V loaded cutoff,1.11W load/80% electronics efficiency,25F*.9*.7=15.75F and54mohm aged ESR screen. Cell<=65C at2.6V,85C requires2.3V derating. No full85C or cold guarantee.

Bound: one preferred source-backed protection configuration; at most two alternative families if necessary. Capture a concrete partial with precise objections if bounds cannot be qualified. No fit claim without placement and no manufacturing release.

Current checkpoint: captured one TPS3700 + TPS3808 + TPS22963C independent charger-input disconnect with Littelfuse045101.5MRL before all cell power branches.14 added parts,21 total contextual footprints/61 pads,85.765mm² added complete courtyards; no sidecar placement claim. Charger feedback tuned only here to2.576V nominal,25mA retained. Conditional runtime14.564s nominal fuse /13.256s hot-fuse allocation, revised2.439190V start.

Validation: actual0ERC,27IC pins/17two-terminal/32static cases; saved-pad checks,0geometricDRC/45unconnected;10 cached source PDFs and175 protected inputs matched. Full final commands/results are in cli-checks.log, package-check.json and receipt.json.

STOP: bounded concrete prototype complete; protection acceptance remains UNMET. Maximum OVP delay is not specified, and constant3A/5s fuse timing does not prove clearing of the decaying cell fault. Physical OVP/healthy overshoot, fuse interruption/thermal/inrush, actual ramp, leakage/runtime and integrated placement remain gates. Parent/Astra own integration. No publication or further architecture search.
