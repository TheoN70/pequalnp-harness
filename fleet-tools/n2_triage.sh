#!/bin/bash
# One-shot triage of a "one NOT gate saves nothing" step handed over by Master (written by lane Normal2).
# usage: n2_triage.sh <worktree> <step id> [lease json] : installs the lease (skeleton, beat, detached beat loop),
# shows the desk state of the step and of its twin, the exact AND/OR size M with its circuit (liveg), and the signed
# lower bound up to M-2 (livegpx, enriched universe). Rule: "none" at M-2 means the negation is false.
T=$(dirname "$(readlink -f "$0")")
W=$1; ID=$2; LJ=${3:-$T/../master/leases/$ID.json}
cd "$W" || exit 1
git fetch -q upstream && git checkout -q --detach upstream/main
date -u +%H:%M:%S
cp "$LJ" .pnp/$ID.json || exit 1
INFO=$(python3 -I -c '
import json,sys,re,itertools
d=json.load(open(sys.argv[1]));g=d["gap"]
st=g["statement"]
open(g["file"],"w").write("import Mathlib\n"+"".join("import %s\n"%m for m in g["imports"])+"\ntheorem %s : (%s) := by\n  sorry\n"%(g["module"],st))
f=[int(v) for v in re.search(r"\[([0-9, ]+)\] : List", st).group(1).split(",")]
E=list(zip(f[0::2],f[1::2])); n=int(re.search(r"Fin (\d+) → Bool",st).group(1))
adj={v:set() for v in range(n)}
for a,b in E: adj[a].add(b); adj[b].add(a)
tri=[sum(1<<v for v in t) for t in itertools.combinations(range(n),3) if all(y in adj[x] for x,y in itertools.combinations(t,2))]
k4=[t for t in itertools.combinations(range(n),4) if all(y in adj[x] for x,y in itertools.combinations(t,2))]
pts=[0]+[1<<i for i in range(n)]+[(1<<n)-1-(1<<i) for i in range(n)]+tri[:6]
print(n, ",".join("%d-%d"%e for e in E), ",".join(map(str,pts)), "neg" if st.startswith("¬") else "pos", "K4:%s"%str(k4).replace(" ",""), d["lease"]["expires_at"])' .pnp/$ID.json)
set -- $INFO; N=$1; E=$2; PTS=$3
echo "n=$N edges=$E sense=$4 $5 expires=$6"
tools/pnp.sh beat $ID
(setsid nohup bash -c "while sleep 600; do tools/pnp.sh beat $ID || break; done" > .pnp/beat-$ID.log 2>&1 &)
NUM=${ID#L-meta-}; if [ "$4" = neg ]; then TW=$((NUM-1)); else TW=$((NUM+1)); fi
for g in $ID L-meta-$TW; do curl -sS -m 10 -G https://pequalnp.com/desk/step --data-urlencode gap=$g | python3 -I -c 'import json,sys
d=json.load(sys.stdin); print("desk", d.get("gap"), d.get("state"), "holders", d.get("holders",""), "prs", d.get("prs",""))'; done
cd $T
$T/capmem ./liveg $N $E 0 0 6 14 27 > "$W/.pnp/liveg-$ID.log" 2>&1; grep -E "FOUND|w[0-9]+ =" "$W/.pnp/liveg-$ID.log"
M=$(grep FOUND "$W/.pnp/liveg-$ID.log" | sed 's/N=\([0-9]*\).*/\1/')
echo "AND/OR exact M=$M ; signed search (enriched universe) up to $((M-2)):"
PTS=$PTS timeout 300 $T/capmem ./livegpx $N $E 1 1 2 $((M-3)) $((M-2)) 27 2>&1 | grep -E "^N=|too large" | cut -c1-100
echo "(if the line N=$((M-2)) is missing, the search hit its 300 s limit: rerun it detached with a table of 28)"
