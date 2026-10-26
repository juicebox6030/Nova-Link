#!/usr/bin/env bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
set -x
candidate_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
python3 "$candidate_dir/preservation.py"
python3 "$candidate_dir/generate.py"
flatpak run --command=kicad-cli org.kicad.KiCad version
flatpak run --command=kicad-cli org.kicad.KiCad sch export netlist --format kicadxml -o "$candidate_dir/regulated-source.net" "$candidate_dir/regulated-source.kicad_sch"
flatpak run --command=kicad-cli org.kicad.KiCad sch erc --format json --severity-all --exit-code-violations -o "$candidate_dir/erc.json" "$candidate_dir/regulated-source.kicad_sch"
python3 "$candidate_dir/verify.py"
flatpak run --command=python3 org.kicad.KiCad "$candidate_dir/build.py"
flatpak run --command=python3 org.kicad.KiCad "$candidate_dir/route.py"
flatpak run --command=kicad-cli org.kicad.KiCad pcb drc --format json --all-track-errors --severity-all --refill-zones --save-board -o "$candidate_dir/drc.json" "$candidate_dir/source-axial.kicad_pcb"
flatpak run --command=python3 org.kicad.KiCad "$candidate_dir/verify-routing.py"
flatpak run --command=python3 org.kicad.KiCad "$candidate_dir/verify-lands.py"
flatpak run --command=kicad-cli org.kicad.KiCad sch export pdf -o "$candidate_dir/regulated-source.pdf" "$candidate_dir/regulated-source.kicad_sch"
flatpak run --command=kicad-cli org.kicad.KiCad pcb export pdf --mode-multipage --layers F.Cu,In1.Cu,In2.Cu,B.Cu --scale 4 -o "$candidate_dir/copper.pdf" "$candidate_dir/source-axial.kicad_pcb"
flatpak run --command=kicad-cli org.kicad.KiCad pcb export pdf --mode-single --layers F.Fab,F.CrtYd,Edge.Cuts --scale 4 -o "$candidate_dir/assembly.pdf" "$candidate_dir/source-axial.kicad_pcb"
mkdir -p "$candidate_dir/svg"
flatpak run --command=kicad-cli org.kicad.KiCad pcb export svg --mode-multi --layers F.Cu,In1.Cu,In2.Cu,B.Cu,F.Fab,F.CrtYd --common-layers Edge.Cuts --page-size-mode 2 --exclude-drawing-sheet -o "$candidate_dir/svg" "$candidate_dir/source-axial.kicad_pcb"
pdftoppm -f 1 -l 1 -singlefile -scale-to 2200 -png "$candidate_dir/regulated-source.pdf" "$candidate_dir/schematic-overview"
pdftoppm -f 1 -l 1 -singlefile -scale-to 1800 -png "$candidate_dir/assembly.pdf" "$candidate_dir/assembly-overview"
pdftoppm -f 1 -l 1 -singlefile -scale-to 1800 -png "$candidate_dir/copper.pdf" "$candidate_dir/copper-overview"
QT_QPA_PLATFORM=offscreen /home/juicebox/.local/bin/freecadcmd "$candidate_dir/envelopes.py"
QT_QPA_PLATFORM=offscreen /home/juicebox/.local/bin/freecadcmd "$candidate_dir/verify-envelopes.py"
python3 "$candidate_dir/preservation.py"
