#!/usr/bin/env bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
set -x
candidate_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
python3 "$candidate_dir/lands.py"
python3 "$candidate_dir/generate.py"
flatpak run --command=kicad-cli org.kicad.KiCad version
flatpak run --command=kicad-cli org.kicad.KiCad sch export netlist --format kicadxml -o "$candidate_dir/source12.net" "$candidate_dir/source12.kicad_sch"
flatpak run --command=kicad-cli org.kicad.KiCad sch erc --format json --severity-all --exit-code-violations -o "$candidate_dir/erc.json" "$candidate_dir/source12.kicad_sch"
python3 "$candidate_dir/verify.py"
flatpak run --command=python3 org.kicad.KiCad "$candidate_dir/build.py"
for zone in rotating stationary; do
 flatpak run --command=kicad-cli org.kicad.KiCad pcb drc --format json --all-track-errors --severity-all -o "$candidate_dir/drc-$zone.json" "$candidate_dir/source12-$zone.kicad_pcb"
 flatpak run --command=kicad-cli org.kicad.KiCad pcb export pdf --mode-single --layers F.Fab,F.CrtYd,Edge.Cuts --scale 4 -o "$candidate_dir/allocation-$zone.pdf" "$candidate_dir/source12-$zone.kicad_pcb"
 pdftoppm -f 1 -l 1 -singlefile -scale-to 1600 -png "$candidate_dir/allocation-$zone.pdf" "$candidate_dir/allocation-$zone"
done
flatpak run --command=python3 org.kicad.KiCad "$candidate_dir/verify-board.py"
flatpak run --command=kicad-cli org.kicad.KiCad sch export pdf -o "$candidate_dir/source12.pdf" "$candidate_dir/source12.kicad_sch"
pdftoppm -f 1 -l 1 -singlefile -scale-to 2600 -png "$candidate_dir/source12.pdf" "$candidate_dir/schematic-overview"
python3 "$candidate_dir/verify.py"
