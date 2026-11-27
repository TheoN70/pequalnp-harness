#!/usr/bin/env bash
# Write the Lean negation of a unit autosolve showed false (rc 4, circsat UNSAT), when a generator covers it; not compiled.
#   refutable.sh <lease.json> <out.lean>      exit 0 written, 1 no generator covers it (or it failed / took > 2 min)
# RepSizeAtMost 5x5, 4x5, 3x5 with k <= |R|+1: rep_lower_gen.py (text substitution, < 1 s). HasCircuitSize n <= 4:
# lrat/lower.sh in the shared clone (Lean dumps the CNF, CaDiCaL LRAT; theorem `lower` on the unit's table), 120 s at
# most on one `slots` core under capmem. Called by grab.sh after AUTO-FAIL rc=4, logged REFUTABLE (Orchestrator
# 2026-11-27: measure how many of our false units Lean can refute; the release is not delayed).
set -u
T=$(dirname "$(readlink -f "$0")"); PENP=$(dirname "$(dirname "$T")")
lease=${1:?usage: refutable.sh <lease.json> <out.lean>}; out=${2:?}
python3 -I "$T/rep_lower_gen.py" "$lease" -o "$out" >/dev/null 2>&1 && exit 0
read -r n k tab mod < <("$T/sat-venv/bin/python" -I -c '
import json, sys; sys.path.insert(0, sys.argv[2]); import autosolve
g = json.load(open(sys.argv[1]))["gap"]; p = autosolve.problem(g)
if not p or p[3] is not None or p[4] or p[0] > 4: sys.exit(1)   # HasCircuitSize only: all rows, NOT allowed
print(p[0], p[1], p[2], g["id"].replace("-", "_") + "_refute")' "$lease" "$T" 2>/dev/null) || exit 1
core=$(SLOTS_RANGE=${SLOTS_RANGE:-0-13} "$T/slots" 1 2>/dev/null) || exit 1
timeout 120 taskset -c "$core" "$T/capmem" -m 4G "$T/lrat/lower.sh" "$PENP/pequalnp-proofs" "$n" "$k" "$tab" "$out" "$mod" >/dev/null 2>&1
