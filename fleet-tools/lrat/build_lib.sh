#!/usr/bin/env bash
# Builds the oleans of PEqualNP.Library.LRAT.* (and what they import) in the shared clone, so steps and agents can
# `import PEqualNP.Library.LRAT.LinkN2` (and replay an LRAT certificate) instead of porting the library.
#
# usage: fleet-tools/lrat/build_lib.sh [--check] [clone]      default clone: $PENP/pequalnp-proofs
#   --check   only say which modules are missing (lake --no-build), build nothing
# env: CORES (taskset list, default 15: a reserved core, so the Research session's cores 0-13 stay free),
#      MEM (capmem cap, default 6G), NICE (default 19)
#
# Additive: it only adds .olean files under <clone>/lean/.lake/build; sources, git state and packages are untouched.
# It refuses to run while another lake/lean process works in that clone (a check or a submit of a step).
set -euo pipefail
T=$(dirname "$(readlink -f "$0")")
PENP=${PENP:-$(readlink -f "$T/../../..")}
check=; [ "${1:-}" = --check ] && { check=1; shift; }
CLONE=$(readlink -f "${1:-$PENP/pequalnp-proofs}")
cd "$CLONE/lean"
mods=$(ls PEqualNP/Library/LRAT/*.lean | sed 's#/#.#g; s#\.lean$##')

if [ -n "$check" ]; then
  lake build --no-build $mods >/dev/null 2>&1 && { echo "all LRAT oleans up to date"; exit 0; }
  echo "missing or out of date (lake --no-build):"; lake build --no-build $mods 2>&1 | grep -E '^- ' || true
  exit 1
fi

for p in $(pgrep -x lake; pgrep -x lean); do  # someone else building or checking in this clone
  case "$(readlink /proc/$p/cwd 2>/dev/null)" in "$CLONE"*) echo "pid $p ($(cat /proc/$p/comm)) works in $CLONE: try again later" >&2; exit 2;; esac
done
if git -C "$CLONE" status --porcelain -- lean/PEqualNP/Library lean/PEqualNP/Defs lean/PEqualNP/MetaComplexity/Helpers | grep -q .; then
  echo "modified library sources in $CLONE: build from a clean upstream checkout" >&2; exit 2
fi

start=$(date +%s)
nice -n "${NICE:-19}" taskset -c "${CORES:-15}" "$T/../capmem" -m "${MEM:-6G}" -t 3h lake build $mods
for m in $mods; do f=.lake/build/lib/lean/$(echo "$m" | tr . /).olean; [ -f "$f" ] || { echo "MISSING $f" >&2; exit 1; }; done

# smoke test: the library is importable outside lake build
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
printf 'import PEqualNP.Library.LRAT.LinkN2\nimport PEqualNP.Library.LRAT.Link2\n#check @PEqualNP.Library.LRAT.LinkN.enc2\n' > "$tmp/Smoke.lean"
taskset -c "${CORES:-15}" lake env lean "$tmp/Smoke.lean" >/dev/null 2>"$tmp/err" || {
  grep -q "unknown" "$tmp/err" && echo "imports ok (the #check name differs, see $tmp/err)" || { cat "$tmp/err" >&2; exit 1; }; }
echo "LRAT library built: $(echo $mods | wc -w) modules in $(( $(date +%s) - start )) s"
