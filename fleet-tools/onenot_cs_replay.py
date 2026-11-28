# Python port of CoreSearch.replay (merged engine, e.g. L_meta_29638): exact, same pruning.
import itertools, functools, sys
M64 = (1 << 64) - 1; M32 = (1 << 32) - 1
GOAL = 0xFFFFFFFF00000000; NGOAL = 0xFFFFFFFF
def sep(w): return ((w >> 32) ^ w) & M32
def cuts(ws):
    v = 0
    for w in ws: v |= sep(w)
    return v
def ops(x, y): return [x & y, x | y, x & (M64 - y), y & (M64 - x)]
def singles(l):
    if not l: return []
    a, rest = l[0], l[1:]
    return [(a, rest)] + [(b, [a] + bs) for b, bs in singles(rest)]
def pairs(l):
    if not l: return []
    a, rest = l[0], l[1:]
    return [(a, b, bs) for b, bs in singles(rest)] + [(b, c, [a] + bs) for b, c, bs in pairs(rest)]
def dispatch(extra, nxt, a, b, r):
    base = cuts(r)
    for w in ops(a, b):
        v = sep(w) | base
        if v == M32 and nxt(extra, [w] + r): return True
        if extra != 0:
            if (v | sep(a)) == M32 and nxt(extra - 1, [w, a] + r): return True
            if (v | sep(b)) == M32 and nxt(extra - 1, [w, b] + r): return True
        if extra >= 2 and (v | sep(a) | sep(b)) == M32 and nxt(extra - 2, [w, a, b] + r): return True
    return False
@functools.lru_cache(maxsize=None)
def _opt(k, extra, ws):
    ws = list(ws)
    if ws == [GOAL] or ws == [NGOAL]: return True
    if k == 0: return False
    nxt = lambda e, l: _opt(k - 1, e, tuple(l))
    return any(dispatch(extra, nxt, a, b, r) for a, b, r in pairs(ws))
def sublists(l):
    for r in range(len(l) + 1):
        yield from itertools.combinations(l, r)
def replay(n, roots):
    for ws in sublists(roots):
        if len(ws) <= n + 1 and cuts(ws) == M32 and _opt(n, n + 1 - len(ws), tuple(ws)): return True
    return False
def slice_count(roots): return max(len(pairs(list(ws))) for ws in sublists(roots))
if __name__ == '__main__':
    roots = [17946651892367368330, 8572235972916281889, 1287990168975902740, 12586786627471840576]
    for n in range(4, 8): print(n, replay(n, roots), flush=True)
