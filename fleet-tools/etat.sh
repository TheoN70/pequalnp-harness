#!/usr/bin/env bash
# Read-only snapshot of the fleet for /etat: collector, held units, today's PRs and points, outcomes, machine.
# Usage: fleet-tools/etat.sh [YYYY-MM-DD]   (default: today, UTC). Changes nothing, takes no lease.
cd "$(dirname "$(readlink -f "$0")")/.." || exit 1   # harness/, also when called through penp/fleet-tools
L=master/leases
DAY=${1:-$(date -u +%F)}
pts() { python3 -I -c 'import json,sys
try: t=json.load(open(sys.argv[1]))["lease"]["terms"]; print(t.get("points","?"), t.get("level","?"), t.get("kind","?"))
except Exception: print("? ? ?")' "$L/$1.json"; }
title() { python3 -I -c 'import json,sys
try: print(json.load(open(sys.argv[1]))["gap"]["title"][:70])
except Exception: print("")' "$L/$1.json"; }

echo "== $(date -u '+%F %H:%M') UTC"
P=$(pgrep -f 'bash master/grab\.sh' | head -1)
if [ -n "$P" ]; then echo "collector: running (pid $P, since $(ps -o lstart= -p "$P"))"; else echo "collector: STOPPED"; fi
grep -E ' (START|STOP)' $L/events.log | tail -1 | sed 's/^/last start\/stop: /'

echo; echo "== held units (slot unit points level kind leased-at title)"
for f in $L/busy-*; do
  id=$(cat "$f" 2>/dev/null); [ -n "$id" ] || continue
  at=$(grep " LEASED ${f##*/busy-} $id " $L/events.log | tail -1 | cut -d' ' -f1)
  echo "${f##*/busy-} $id $(pts "$id") ${at:-?} $(title "$id")"
done

echo; echo "== PRs by TheoN70 opened on $DAY (number state unit points)"
gh pr list -R open-goat/pequalnp-proofs --author TheoN70 --state all --limit 100 \
  --json number,title,state,createdAt -q ".[]|select(.createdAt>=\"${DAY}T00:00\")|\"\(.number) \(.state) \(.title)\"" 2>/dev/null |
while read -r n s t; do echo "#$n $s $t $(pts "$t" | cut -d' ' -f1)"; done |
awk '{print} $2=="MERGED" && $4~/^[0-9]+$/ {m+=$4} $2=="OPEN" && $4~/^[0-9]+$/ {o+=$4}
     END{printf "points merged: %d, pending in open PRs: %d\n", m, o}'

echo; echo "== outcomes on $DAY (results.tsv)"
awk -F'\t' -v d="$DAY" '$1==d {c[$7" "$8]++} END{for(k in c) print c[k], k}' ../results.tsv | sort -rn | head -12

echo; echo "== machine"
free -g | awk 'NR==2{print "memory: " $7 " GB available of " $2}'
uptime | sed 's/.*load/load/'
fleet-tools/slots 2>/dev/null | tail -3
[ -f master/heavy.lock ] && { flock -n master/heavy.lock true && echo "heavy.lock: free" || echo "heavy.lock: HELD"; }

echo; echo "== research (work/*/STATUS.md changed in the last 6 h)"
find ../work -maxdepth 2 -name STATUS.md -mmin -360 2>/dev/null | while read -r s; do echo "-- $s"; tail -5 "$s"; done
[ -s master/long-true.txt ] && { echo; echo "== long true units kept for after the wave"; cat master/long-true.txt; }

echo; echo "== Orchestrator journal (last lines)"
tail -15 skills/orchestrator-auto/JOURNAL.md
