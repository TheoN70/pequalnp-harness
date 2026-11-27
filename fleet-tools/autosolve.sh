#!/usr/bin/env bash
# Solve, check and submit one leased circuit unit with no LLM: two-lit, HasCircuitSize (upper/search), true RepSizeAtMost.
#   autosolve.sh <lease.json> [worktree] [--dry]
# lease.json: Master's leases/<id>.json (the lease Master holds). worktree: default $PENP/pequalnp-auto, made like a lane's.
# Steps: install the lease (take_lease.py); the desk's sketch if it fits in k, else circsat on 1 `slots` core, under
# capmem, at most AUTOSOLVE_S seconds (600); circuit2lean.py; tools/pnp.sh check; tools/pnp.sh submit (PNP_MODEL set).
# --dry: compile the file with `lake build <module>` instead of check + submit, then restore the worktree (for tests).
# Exit 0 submitted (or compiled, --dry); 1 Lean check or submit failed; 2 no circuit (UNSAT, time out, no free core,
# unit already on main); 3 family not recognised.
# ponytail: one run at a time per worktree (flock, waits up to 30 min); a second worktree if they queue up.
set -u
T=$(dirname "$(readlink -f "$0")"); PENP=$(dirname "$(dirname "$T")")
lease=${1:?usage: autosolve.sh <lease.json> [worktree] [--dry]}; wt=${2:-$PENP/pequalnp-auto}; dry=${3:-}
[ "$wt" = --dry ] && { wt=$PENP/pequalnp-auto; dry=--dry; }
export PNP_MODEL=${PNP_MODEL:-claude-sonnet-5-5}
exec 7>"$wt.lock"; flock -w 1800 7 || { echo "worktree busy for 30 min" >&2; exit 2; }
if [ ! -d "$wt" ]; then
  git -C "$PENP/pequalnp-proofs" worktree add -q --detach "$wt" upstream/main || exit 1
  mkdir -p "$wt/lean/.lake"; ln -s "$PENP/pequalnp-proofs/lean/.lake/packages" "$wt/lean/.lake/packages"
fi
git -C "$wt" fetch -q upstream && git -C "$wt" checkout -q -f --detach upstream/main || exit 1
git -C "$wt" clean -fdq lean/PEqualNP/Outside   # skeletons left by an earlier failed unit
read -r id file mod < <(python3 -I -c 'import json,sys; g=json.load(open(sys.argv[1]))["gap"]; print(g["id"], g["file"], g["module"])' "$lease") || exit 3
out=$(python3 -I "$T/take_lease.py" "$lease" "$wt") || exit 1
case $out in *"ALREADY EXISTED"*) [ -z "$dry" ] && { echo "$id is already on main" >&2; exit 2; } ;; esac
core=$("$T/slots" 1) || { echo "no free core" >&2; exit 2; }
timeout "${AUTOSOLVE_S:-600}" taskset -c "$core" "$T/capmem" -m 4G "$T/sat-venv/bin/python" -I "$T/autosolve.py" "$lease" "$wt/.pnp/$id.circuit.json"
rc=$?; [ $rc = 3 ] && exit 3; [ $rc = 0 ] || exit 2
python3 -I "$T/circuit2lean.py" "$lease" "$wt/.pnp/$id.circuit.json" -o "$wt/$file" || exit 1
core=$("$T/slots" 1) || core=   # the check runs on a free core if there is one
pin() { if [ -n "$core" ]; then taskset -c "$core" "$@"; else "$@"; fi; }
if [ -n "$dry" ]; then
  (cd "$wt/lean" && pin "$T/capmem" -m 6G lake build "$mod"); rc=$?
  git -C "$wt" checkout -q -f --detach upstream/main; git -C "$wt" clean -fdq lean/PEqualNP/Outside
  [ $rc = 0 ] && echo "$id: compiles (dry run, not submitted)"; exit $(( rc ? 1 : 0 ))
fi
(cd "$wt" && pin "$T/capmem" -m 6G tools/pnp.sh check "$id" && tools/pnp.sh submit "$id") || exit 1
git -C "$wt" checkout -q -f --detach upstream/main
