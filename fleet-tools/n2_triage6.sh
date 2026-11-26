#!/bin/bash
# One-shot triage of a 6-input "each AND/OR/NOT circuit has an AND/OR one no larger" step (written by lane Normal2).
# usage: n2_triage6.sh <worktree> <step id> [lease json] : installs the lease (skeleton, beat, detached beat loop),
# shows the desk state of the step and of its twin, the prime implicants, the exact AND/OR size M and the exact
# search with NOT free up to M-1 on the full 64-input table. Rule: "none" at M-2 means a NOT saves nothing.
T=$(dirname "$(readlink -f "$0")")
W=$1; ID=$2; LJ=${3:-$T/../master/leases/$ID.json}
cd "$W" || exit 1
git fetch -q upstream && git checkout -q --detach upstream/main
date -u +%H:%M:%S
cp "$LJ" .pnp/$ID.json || exit 1
INFO=$(python3 -I -c '
import json,sys,re,itertools
d=json.load(open(sys.argv[1]));g=d["gap"]; st=g["statement"]
open(g["file"],"w").write("import Mathlib\n"+"".join("import %s\n"%m for m in g["imports"])+"\ntheorem %s : (%s) := by\n  sorry\n"%(g["module"],st))
m=re.search(r"Nat\.testBit \((\d+) \* 2 \^ 32 \+ (\d+)\)", st); T=int(m.group(1))*2**32+int(m.group(2))
def sw(T,i,j):
    R=0
    for x in range(64):
        a=(x>>i)&1; b=(x>>j)&1
        y=x & ~(1<<i) & ~(1<<j) | (b<<i) | (a<<j)
        if (T>>y)&1: R|=1<<x
    return R
sym=1 if sw(T,0,1)==T and sw(T,1,2)==T else 0
dep=sum(1<<i for i in range(6) if any(((T>>x)&1)!=((T>>(x^(1<<i)))&1) for x in range(64)))
mins=[x for x in range(64) if (T>>x)&1 and all(not (T>>(x&~(1<<i)))&1 for i in range(6) if (x>>i)&1)]
pi="+".join("".join("x%d"%i for i in range(6) if (x>>i)&1) for x in mins)
print("%016x"%T, sym, hex(dep), "neg" if st.startswith("¬") else "pos", pi, d["lease"]["expires_at"])' .pnp/$ID.json)
set -- $INFO; TB=$1; SYM=$2; VM=$3
echo "table=$TB sym012=$SYM varmask=$VM sense=$4 expires=$6"; echo "f = $5"
tools/pnp.sh beat $ID
(setsid nohup bash -c "while sleep 600; do tools/pnp.sh beat $ID || break; done" > .pnp/beat-$ID.log 2>&1 &)
NUM=${ID#L-meta-}; if [ "$4" = neg ]; then TW=$((NUM-1)); else TW=$((NUM+1)); fi
for g in $ID L-meta-$TW; do curl -sS -m 10 -G https://pequalnp.com/desk/step --data-urlencode gap=$g | python3 -I -c 'import json,sys
d=json.load(sys.stdin); print("desk", d.get("gap"), d.get("state"), "holders", d.get("holders",""), "prs", d.get("prs",""))'; done
cd $T
M=$(timeout 300 $T/capmem ./live $TB $VM 0 $SYM 1 13 27 | grep FOUND | sed 's/N=\([0-9]*\).*/\1/')
echo "AND/OR exact M=$M ; with NOT free (exact on the full table), up to $((M-1)):"
timeout 400 $T/capmem ./live $TB $VM 1 $SYM $((M-3)) $((M-1)) 27 2>&1 | grep -E "^N=|full" | cut -c1-90
