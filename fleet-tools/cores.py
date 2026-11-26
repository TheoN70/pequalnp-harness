# For a graph, list the induced subgraphs S with the largest (AND/OR size of G[S]) - |S|: candidates for the core of a
# "delete a vertex, pay one gate" chain, whose bound is (n - |S|) + size(G[S]). Uses ./liveg (exact AND/OR size).
# usage: python3 -I cores.py <n> <edges 0-4,0-5,...> [max core size]
import subprocess, sys, itertools
n = int(sys.argv[1]); E = [tuple(map(int, e.split("-"))) for e in sys.argv[2].split(",")]
mx = int(sys.argv[3]) if len(sys.argv) > 3 else n
def size(S):
    idx = {v: i for i, v in enumerate(S)}
    es = [(idx[a], idx[b]) for a, b in E if a in idx and b in idx]
    if not es: return 0, 0
    used = sorted(set(v for e in es for v in e))
    out = subprocess.run(["./liveg", str(len(S)), ",".join("%d-%d" % e for e in es), "0", "0", "1", "13", "22"], capture_output=True, text=True).stdout
    for l in out.splitlines():
        if l.startswith("N=") and "FOUND" in l: return int(l.split()[0][2:]), len(used)
    return None, len(used)
res = []
for k in range(3, mx + 1):
    for S in itertools.combinations(range(n), k):
        m, used = size(S)
        if m is None or used < k: continue      # skip subgraphs with an isolated vertex (same as a smaller S)
        res.append((n - k + m, m - k, k, m, S))
res.sort(reverse=True)
print("chain bound = (n - |S|) + size(G[S]); best cores:")
for r in res[:25]: print("bound %d  size-|S| %d  |S| %d  size %d  S %s" % r)
