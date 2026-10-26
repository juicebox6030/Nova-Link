"""Correct one saved pad net; never invoke the historical placement search.

Require the entire board to equal the reviewed board except this single net
token. KiCad independently reopens and checks the saved result afterwards.
"""
from pathlib import Path
import hashlib
P=Path(__file__).resolve().parent
prior=(P/'history/pre-u40-fix-qualified15-placement.kicad_pcb').read_text()
anchor=prior.index('(property "Reference" "U40"')
start=prior.index('(pad "5"',anchor)
end=prior.index('(pad "6"',start)
pad=prior[start:end]
assert pad.count('(net "GND_USB")')==1
fixed=prior[:start]+pad.replace('(net "GND_USB")','(net "AON_USB_LIMITED")')+prior[end:]
board=P/'qualified15-placement.kicad_pcb'
assert board.read_text() in [prior,fixed], 'Saved board changed beyond the authorized U40 correction'
board.write_text(fixed)
print('PASS fixed saved U40.5 only; all other board bytes preserved; SHA256',hashlib.sha256(board.read_bytes()).hexdigest())
