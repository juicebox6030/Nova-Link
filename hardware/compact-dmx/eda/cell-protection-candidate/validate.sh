#!/usr/bin/env bash
set -euo pipefail
set -x
candidate_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
python3 "$candidate_dir/lands.py"
python3 "$candidate_dir/generate.py"
flatpak run --command=kicad-cli org.kicad.KiCad version
flatpak run --command=kicad-cli org.kicad.KiCad sch export netlist --format kicadxml -o "$candidate_dir/cell-protection.net" "$candidate_dir/cell-protection.kicad_sch"
flatpak run --command=kicad-cli org.kicad.KiCad sch erc --format json --severity-all --exit-code-violations -o "$candidate_dir/erc.json" "$candidate_dir/cell-protection.kicad_sch"
python3 "$candidate_dir/verify.py"
flatpak run --command=python3 org.kicad.KiCad "$candidate_dir/coupon.py"
flatpak run --command=kicad-cli org.kicad.KiCad pcb drc --format json --severity-all -o "$candidate_dir/drc.json" "$candidate_dir/land-coupon.kicad_pcb"
flatpak run --command=kicad-cli org.kicad.KiCad sch export pdf -o "$candidate_dir/cell-protection.pdf" "$candidate_dir/cell-protection.kicad_sch"
flatpak run --command=kicad-cli org.kicad.KiCad pcb export pdf --mode-single --layers F.Cu,F.Fab,F.CrtYd,Edge.Cuts --scale 4 -o "$candidate_dir/land-coupon.pdf" "$candidate_dir/land-coupon.kicad_pcb"
pdftoppm -f 1 -l 1 -singlefile -scale-to 2200 -png "$candidate_dir/cell-protection.pdf" "$candidate_dir/schematic-overview"
pdftoppm -f 1 -l 1 -singlefile -scale-to 1800 -png "$candidate_dir/land-coupon.pdf" "$candidate_dir/land-coupon"
python3 "$candidate_dir/package-check.py"
