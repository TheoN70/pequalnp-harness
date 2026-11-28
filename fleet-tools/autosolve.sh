#!/usr/bin/env bash
# Solve, check and submit one leased circuit unit with no LLM: two-lit, HasCircuitSize (upper/search), true RepSizeAtMost.
#   autosolve.sh <lease.json> [worktree] [--dry]
# lease.json: Master's leases/<id>.json (the lease Master holds). worktree: default the first free of
# $PENP/pequalnp-auto1..AUTO_PAR (default 7, one run per worktree), made like a lane's. At most SAT_PAR (3) circsat
# searches at once across runs (autosolve.py, lock files $PENP/pequalnp-sat<i>.lock); sketch and lsr need no slot.
# Steps: install the lease (take_lease.py); the desk's sketch if it fits in k, else circsat on 1 `slots` core, under
# capmem, at most AUTOSOLVE_S seconds (120; past it the lane takes over); circuit2lean.py; tools/pnp.sh check; tools/pnp.sh submit (PNP_MODEL set).
# --dry: compile the file with `lake build <module>` instead of check + submit, then restore the worktree (for tests).
# Exit 0 submitted (or compiled, --dry); 1 Lean check or submit failed; 2 no circuit found (time out, no free core or
# worktree); 3 family not recognised; 4 circsat UNSAT: no circuit within the bound (statement false); 5 unit already on main.
# ponytail: a named worktree waits for its lock (30 min); the default pool takes a free one or exits 2 when all are busy.
set -u
T=$(dirname "$(readlink -f "$0")"); PENP=$(dirname "$(dirname "$T")")
lease=${1:?usage: autosolve.sh <lease.json> [worktree] [--dry]}; wt=${2:-}; dry=${3:-}
[ "$wt" = --dry ] && { wt=; dry=--dry; }
export PNP_MODEL=${PNP_MODEL:-claude-sonnet-5-5}
export SLOTS_RANGE=${SLOTS_RANGE:-0-13}   # Orchestrator 2026-11-27: all 14 cores while no Research runs (0-7 when one holds 8-13)
if [ -n "$wt" ]; then exec 7>"$wt.lock"; flock -w 1800 7 || { echo "worktree busy for 30 min" >&2; exit 2; }
else
  for i in $(seq 1 "${AUTO_PAR:-7}"); do wt=$PENP/pequalnp-auto$i; exec 7>"$wt.lock"; flock -n 7 && break; wt=; done
  [ -n "$wt" ] || { echo "all autosolve worktrees busy" >&2; exit 2; }
fi
if [ ! -d "$wt" ]; then
  git -C "$PENP/pequalnp-proofs" worktree add -q --detach "$wt" upstream/main || exit 1
  mkdir -p "$wt/lean/.lake"; ln -s "$PENP/pequalnp-proofs/lean/.lake/packages" "$wt/lean/.lake/packages"
fi
flock "$PENP/pequalnp-fetch.lock" git -C "$wt" fetch -q upstream   # parallel runs share the refs: one fetch at a time
git -C "$wt" checkout -q -f --detach upstream/main || exit 1
git -C "$wt" clean -fdq lean/PEqualNP/Outside   # skeletons left by an earlier failed unit
read -r id file mod < <(python3 -I -c 'import json,sys; g=json.load(open(sys.argv[1]))["gap"]; print(g["id"], g["file"], g["module"])' "$lease") || exit 3
out=$(python3 -I "$T/take_lease.py" "$lease" "$wt") || exit 1
case $out in *"ALREADY EXISTED"*) [ -z "$dry" ] && { echo "$id is already on main" >&2; exit 5; } ;; esac
w=0; until core=$("$T/slots" 1 2>/dev/null); do   # a full machine (Research) gets CORE_WAIT_S (60) s to free a core
  w=$((w + 2)); [ $w -ge "${CORE_WAIT_S:-60}" ] && { echo "no free core in ${CORE_WAIT_S:-60} s" >&2; exit 2; }; sleep 2; done
if grep -q '"title": "Table 2: for the monotone six-input' "$lease"; then   # Sol engine, M = 11 or 12 (sol_fit.py)
  timeout "${SOL_S:-900}" python3 -I "$T/sol_fit.py" "$lease" "$wt/$file"; rc=$?
  [ $rc = 124 ] && exit 2; [ $rc = 3 ] && exit 3; [ $rc = 0 ] || exit 2
  [ -n "$dry" ] && { git -C "$wt" checkout -q -f --detach upstream/main; git -C "$wt" clean -fdq lean/PEqualNP/Outside
    echo "$id: compiles (sol_fit, dry run, not submitted)"; exit 0; }   # sol_fit already compiled this exact file
elif grep -qE '"title": "(On five input bits, three|Three) ordered outputs' "$lease"; then   # Normal5's template (L-meta-49912): exit 4 = unit false
  timeout "${THREE_S:-600}" taskset -c "$core" python3 -I "$T/three_out_gen.py" "$lease" "$wt/$file"; rc=$?
  [ $rc = 124 ] && exit 2; [ $rc = 0 ] || exit $rc
else
timeout "${AUTOSOLVE_S:-120}" taskset -c "$core" "$T/capmem" -m 4G "$T/sat-venv/bin/python" -I "$T/autosolve.py" "$lease" "$wt/.pnp/$id.circuit.json"
rc=$?; [ $rc = 3 ] && exit 3; [ $rc = 2 ] && exit 4; [ $rc = 0 ] || exit 2
python3 -I "$T/circuit2lean.py" "$lease" "$wt/.pnp/$id.circuit.json" -o "$wt/$file" || exit 1
fi
core=$("$T/slots" 1) || core=   # the check runs on a free core if there is one
pin() { if [ -n "$core" ]; then taskset -c "$core" "$@"; else "$@"; fi; }
if [ -n "$dry" ]; then
  (cd "$wt/lean" && pin "$T/capmem" -m 6G lake build "$mod"); rc=$?
  git -C "$wt" checkout -q -f --detach upstream/main; git -C "$wt" clean -fdq lean/PEqualNP/Outside
  [ $rc = 0 ] && echo "$id: compiles (dry run, not submitted)"; exit $(( rc ? 1 : 0 ))
fi
(cd "$wt" && pin "$T/capmem" -m 6G tools/pnp.sh check "$id" && tools/pnp.sh submit "$id") || exit 1
git -C "$wt" checkout -q -f --detach upstream/main
