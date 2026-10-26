#!/usr/bin/env bash
set -euo pipefail
candidate_dir="$(cd -- "$(dirname -- "$0")" && pwd)"
python3 "$candidate_dir/validate.py"
python3 "$candidate_dir/make_receipt.py"
(cd "$candidate_dir" && sha256sum --quiet -c SHA256SUMS)
