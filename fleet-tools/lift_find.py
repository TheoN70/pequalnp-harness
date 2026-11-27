# For an 8-vertex graph, list the vertices v with M(G - v) = M(G) - 1 (liveg) and the merged 7-vertex ForestCore
# files (def coding : Fin 7, theorem wholeBound) whose graph is isomorphic to G - v: candidates for onenot_lift8_gen.py.
# usage: python3 -I lift_find.py <worktree> <edges a-b,c-d,...> <M(G)>
import sys, re, subprocess, glob, itertools, os
wt, es, M = sys.argv[1], sys.argv[2], int(sys.argv[3])
E = [tuple(map(int, e.split("-"))) for e in es.split(",")]
here = os.path.dirname(os.path.abspath(__file__))
def msize(n, edges):
    o = subprocess.run([here + "/liveg", str(n), ",".join("%d-%d" % e for e in edges), "0", "0", "3", str(M), "27"], capture_output=True, text=True).stdout
    for l in o.splitlines():
        if l.startswith("N=") and "FOUND" in l: return int(l.split()[0][2:])
def inv(n, edges):
    d = [0] * n
    for a, b in edges: d[a] += 1; d[b] += 1
    return (len(edges), tuple(sorted(d)))
lib = {}
for f in glob.glob(wt + "/lean/PEqualNP/Outside/L_meta_*.lean"):
    s = open(f, encoding="utf-8").read()
    if "def coding : Fin 7" not in s or "theorem wholeBound" not in s: continue
    m = re.search(r"\[([0-9, ]+)\] : List ℕ", s[s.rindex("\ntheorem PEqualNP.Outside."):])
    if not m: continue
    fl = [int(x) for x in m.group(1).split(",")]
    if max(fl) >= 7: continue  # ponytail: skip non 7-vertex lists (8-vertex files that also define coding : Fin 7)
    ed = list(zip(fl[0::2], fl[1::2]))
    lib.setdefault(inv(7, ed), []).append((f, frozenset(frozenset(e) for e in ed)))
print("merged ForestCore 7-vertex files:", sum(map(len, lib.values())))
for v in range(8):
    rest = [u for u in range(8) if u != v]; idx = {u: i for i, u in enumerate(rest)}
    sub = [(idx[a], idx[b]) for a, b in E if a != v and b != v]
    used = sorted({x for e in sub for x in e})
    if len(used) < 7: print("v=%d leaves an isolated vertex" % v); continue
    mv = msize(7, sub); hit = []
    if mv == M - 1:
        for f, es7 in lib.get(inv(7, sub), []):
            for p in itertools.permutations(range(7)):
                if frozenset(frozenset((p[a], p[b])) for a, b in sub) == es7: hit.append(os.path.basename(f)); break
    print("v=%d M(G-v)=%s %s" % (v, mv, " ".join(hit[:4])))
