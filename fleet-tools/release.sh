#!/usr/bin/env bash
# Usage (from a lane worktree): release.sh <id> <reason> [blocker ids...]
# Releases the step with tools/pnp.sh, then records the verdict in master/verdicts.txt so grab.sh hands
# back any re-offered copy at once, without a lane re-triaging it.
# missing_lemma: name the open steps it waits on (e.g. release.sh L-meta-612 missing_lemma L-meta-1900);
# grab.sh then lets the step through again once every blocker is merged.
# exhausted / rechecked: the extra argument is the sha256 pnp.sh expects, not a blocker.
set -euo pipefail
id=${1:?step id}; reason=${2:?reason}; shift 2
V="$(dirname "$(readlink -f "$0")")/../master/verdicts.txt"
case "$reason" in
  exhausted|rechecked) tools/pnp.sh release "$id" "$reason" "$@"; exit;;   # re-check steps: no verdict to keep
esac
tools/pnp.sh release "$id" "$reason"; echo
# the verdict is the lane's judgment, kept even if the desk refused the release (grab.sh uses it only on re-offers)
# a newer verdict for the same id replaces the old one; the lock keeps concurrent lanes and Master from losing lines
( flock 7
  grep -v "^$id " "$V" > "$V.tmp" || true
  echo "$id $reason${*:+ $*}" >> "$V.tmp" && mv "$V.tmp" "$V"
) 7>"$V.lock"
echo "verdict recorded: $id $reason${*:+ $*}"
