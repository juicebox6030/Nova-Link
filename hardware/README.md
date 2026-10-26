# NOVA-LINK hardware development checkpoint

This folder preserves the TI-only dual-band DMX/RDM sidecar and rotating USB-C
power-barrel design work. **Prototype development only; not released for
manufacture.** The 2026-10-25 owner request authorizes committing and pushing this
checkpoint to `main`; it does not change the engineering acceptance status.

- [Canonical requirements, decisions and remaining gates](../docs/hardware/DMX_Dongle_and_Power_Barrel.md)
- [CAD/EDA package index and revision comparisons](compact-dmx/README.md)
- [Latest closure-access CAD, STEP and drawing](compact-dmx/rotary-compact-candidate/closure-access-margin-fix/README.md)
- [25 F sidecar placement and protection candidate](compact-dmx/eda/buffer-fit-candidate/protected25-placement/README.md)
- [Bounded power-source comparison](compact-dmx/rotary-compact-candidate/compact-source-reference-screen/README.md)
- [Fixture reference manifest](../docs/hardware/fixture-reference-manifest.md)
- [Candidate BOM](../docs/hardware/dmx-hardware-bom.csv)

Earlier candidates include failed and superseded designs, retained for comparison.
Passing ERC, geometric checks or calculations does not establish full PCB routing,
RF performance, runtime, fixture fit, mains safety, thermal performance or durable
motion. Use the canonical checkpoint to distinguish current development directions
from historical allocations and unresolved construction.

Editable project files, our generated CAD/STEP/drawings, scripts, original analysis
and source/validation manifests are versioned. Downloaded manufacturer PDFs, CAD,
reference archives, full-page vendor previews, tool caches and automatic backups
remain local and ignored. Exact original URLs and hashes are retained in the
source manifests; third-party redistribution rights are not asserted. A fresh
clone therefore needs the referenced source files before source-dependent checks
can run. Historic absolute workspace paths and frozen-input hashes are provenance
records, not promises of a turnkey build on a new host. Follow the local
reproduction instructions for each candidate; preserve original receipts when
regenerating artifacts.
