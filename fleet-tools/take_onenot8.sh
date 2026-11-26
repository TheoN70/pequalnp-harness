#!/usr/bin/env bash
# Lane helper for a "one NOT gate saves nothing" negation on 8 vertices, handed over by Master.
# usage: take_onenot8.sh <worktree> <step id> <lease json> : installs the lease, beats, shows the twin's desk state,
# then the exact AND/OR size (liveg) and the signed lower bound (livegpx, enriched universe).
set -u
W="$1"; ID="$2"; J="$3"; cd "$W" || exit 1
cp "$J" ".pnp/$ID.json"
E=$(python3 -I -c '
import json,sys,re
d=json.load(open(sys.argv[1]));g=d["gap"]
open(g["file"],"w").write("import Mathlib\n"+"".join("import %s\n"%m for m in g["imports"])+"\ntheorem %s : (%s) := by\n  sorry\n"%(g["module"],g["statement"]))
f=[int(v) for v in re.search(r"\[([0-9, ]+)\] : List", g["statement"]).group(1).split(",")]
print(",".join("%d-%d"%(a,b) for a,b in zip(f[0::2],f[1::2])))' ".pnp/$ID.json")
tools/pnp.sh beat "$ID"
(while tools/pnp.sh beat "$ID" >/dev/null 2>&1; do sleep 300; done) >/dev/null 2>&1 &
N=${ID#L-meta-}; echo "edges $E ; twin L-meta-$((N-1)):"
curl -sS -m 10 -G https://pequalnp.com/desk/step --data-urlencode "gap=L-meta-$((N-1))" | grep -E '"state"|"holders"|^\s+[0-9]+'
cd "$(dirname "$0")"
timeout 250 ./liveg 8 "$E" 0 0 7 16 27 2>&1 | grep -E "^N=" | tail -2
PTS=0,1,2,4,8,16,32,64,128,254,253,251,247,239,223,191,127 timeout 400 ./livegpx 8 "$E" 1 0 2 8 13 28 2>&1 | grep -E "^N=|too large" | tail -3 | cut -c1-90
