# Mirror of the Lean `search` of the L_meta_11525 engine (multiset of pending reads), for any core graph on k
# vertices with the universe "singles + pairs". Counts the calls, to size the in-kernel search.
import sys, itertools
sys.setrecursionlimit(10000)
def setup(k, edges):
    pairs = list(itertools.combinations(range(k), 2))
    rows = [(i,) for i in range(k)] + pairs
    R = len(rows); ALL = (1 << R) - 1
    E = set(tuple(sorted(e)) for e in edges)
    T = sum(1 << j for j, r in enumerate(rows) if len(r) == 2 and r in E)
    falses = [j for j in range(R) if not (T >> j) & 1]
    ins = [sum(1 << j for j, r in enumerate(rows) if i in r) for i in range(k)]
    return rows, R, ALL, T, falses, ins
def gM(k, a, b): return (a & b, a | b, a ^ (a & b), b ^ (a & b))[k]
calls = 0
def make(ALL, T, falses):
    def cov(ws):
        acc = 0
        for t in ws: acc |= t
        if acc & T != T: return False
        for p in falses:
            acc = 0
            for t in ws: acc |= (t ^ ALL) if (t >> p) & 1 else t
            if acc & T != T: return False
        return True
    def search(r, ws):
        global calls; calls += 1
        if r == 0: return ws == [T]
        if len(ws) > r + 1 or not cov(ws): return False
        d = sorted(set(ws))
        for a in d:
            for b in d:
                if a < b:
                    for k in range(4):
                        g = gM(k, a, b)
                        if g == 0 or g == a or g == b: continue
                        rest = list(ws); rest.remove(a); rest.remove(b)
                        for u in range(r + 2 - len(ws)):
                            if search(r - 1, [g] * (u + 1) + rest): return True
        return False
    return search
if __name__ == "__main__":
    k = int(sys.argv[1]); edges = [tuple(map(int, e.split("-"))) for e in sys.argv[2].split(",")]; S = int(sys.argv[3])
    sym = sys.argv[4] == "sorted" if len(sys.argv) > 4 else False
    rows, R, ALL, T, falses, ins = setup(k, edges)
    print("rows", R, "target", T, "all", ALL, "false rows", falses, "inputs", ins)
    search = make(ALL, T, falses)
    for s in range(S + 1):
        c0 = calls; found = False; nvec = 0
        for m in itertools.product(range(s + 2), repeat=k):
            if sym and any(m[i] < m[i + 1] for i in range(k - 1)): continue
            if not sym and sum(m) > s + 1 and s > 0: continue
            nvec += 1
            ws = [x for i in range(k) for x in [ins[i]] * m[i]]
            if search(s, ws): found = True
        print("s=%d vectors=%d calls=%d found=%s" % (s, nvec, calls - c0, found), flush=True)
    print("total calls", calls)
