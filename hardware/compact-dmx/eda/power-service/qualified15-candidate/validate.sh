#!/usr/bin/env bash
set -euo pipefail
set -x
candidate_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
python3 "$candidate_dir/lands.py"
python3 "$candidate_dir/generate.py"
flatpak run --command=kicad-cli org.kicad.KiCad version
flatpak run --command=kicad-cli org.kicad.KiCad sch export netlist --format kicadxml -o "$candidate_dir/qualified15.net" "$candidate_dir/qualified15.kicad_sch"
flatpak run --command=kicad-cli org.kicad.KiCad sch erc --format json --severity-all --exit-code-violations -o "$candidate_dir/erc.json" "$candidate_dir/qualified15.kicad_sch"
python3 "$candidate_dir/verify.py"
python3 "$candidate_dir/corner-proof.py"
python3 "$candidate_dir/fault-budget.py"
python3 "$candidate_dir/refresh-u40-placement.py"
flatpak run --command=kicad-cli org.kicad.KiCad pcb drc --format json --severity-all -o "$candidate_dir/drc.json" "$candidate_dir/qualified15-placement.kicad_pcb"
flatpak run --command=python3 org.kicad.KiCad "$candidate_dir/verify-placement.py"
flatpak run --command=kicad-cli org.kicad.KiCad sch export pdf -o "$candidate_dir/qualified15.pdf" "$candidate_dir/qualified15.kicad_sch"
flatpak run --command=kicad-cli org.kicad.KiCad pcb export svg --mode-single --layers F.Cu,F.Fab,F.CrtYd,Edge.Cuts,Dwgs.User --page-size-mode 2 --exclude-drawing-sheet -o "$candidate_dir/placement-top.svg" "$candidate_dir/qualified15-placement.kicad_pcb"
flatpak run --command=kicad-cli org.kicad.KiCad pcb export svg --mode-single --layers B.Cu,B.Fab,B.CrtYd,Edge.Cuts,Dwgs.User --page-size-mode 2 --exclude-drawing-sheet -o "$candidate_dir/placement-bottom.svg" "$candidate_dir/qualified15-placement.kicad_pcb"
flatpak run --command=kicad-cli org.kicad.KiCad pcb export pdf --mode-single --layers F.Cu,F.Fab,F.CrtYd,Edge.Cuts,Dwgs.User --scale 3 -o "$candidate_dir/placement-top.pdf" "$candidate_dir/qualified15-placement.kicad_pcb"
flatpak run --command=kicad-cli org.kicad.KiCad pcb export pdf --mode-single --layers B.Cu,B.Fab,B.CrtYd,Edge.Cuts,Dwgs.User --scale 3 -o "$candidate_dir/placement-bottom.pdf" "$candidate_dir/qualified15-placement.kicad_pcb"
pdftoppm -f 1 -l 1 -scale-to 1800 -singlefile -png "$candidate_dir/qualified15.pdf" "$candidate_dir/schematic-overview"
pdftoppm -f 2 -l 2 -scale-to 1800 -singlefile -png "$candidate_dir/qualified15.pdf" "$candidate_dir/control-overview"
pdftoppm -f 1 -l 1 -scale-to 1800 -singlefile -png "$candidate_dir/placement-top.pdf" "$candidate_dir/placement-top"
pdftoppm -f 1 -l 1 -scale-to 1800 -singlefile -png "$candidate_dir/placement-bottom.pdf" "$candidate_dir/placement-bottom"
