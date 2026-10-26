# Pre-U40-fix history

These copies preserve the reviewed state before correction of U40 MODE=GND. The original receipt SHA256 is a89c9a7da09171b4c17dfa4a873900383490bff1fcea075453fd1f93a8645e53. Its successful logical checks did not detect the wrong TPS2116 operating mode and do not establish working AON. Current artifacts and receipt are in the parent directory. The immutable `.tools/reviews/qualified15-20261023` snapshot is untouched.

The historical board and netlist are regression inputs. Only U40.5 may differ in the current board/netlist; the saved placement is never repacked by current validation. `pre-u40-fix-file-hashes.json` captures all 97 files present in this candidate before the correction, including the old receipt and SHA256SUMS. The old SHA256SUMS covers 96 entries and the old receipt's artifact array covers 95; those differing inventory conventions are retained verbatim, not represented as current hashes.
