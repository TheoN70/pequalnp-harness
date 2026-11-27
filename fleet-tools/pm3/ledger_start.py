# Search a `start` vector for the L_meta_27763 Ledger argument, for a given opening (its 4 read inputs).
# Per side s: s=0 must give matching == p&q, s=1 must give matching == p|q; inputs P (carries p), Q (carries q)
# not read by the opening; every other input constant (off/on) on each side.
import itertools, sys
M = [(0,4,8),(0,5,7),(1,3,8),(1,5,6),(2,3,7),(2,4,6)]
mt = lambda x: any(x[a] and x[b] and x[c] for a,b,c in M)
def side(P, Q, want):
    out = []
    for cP in ('p', 0, 1):
        for cQ in ('q', 0, 1):
            for consts in itertools.product((0,1), repeat=7):
                it = iter(consts); ok = True
                for p in (0,1):
                    for q in (0,1):
                        x = [None]*9; it = iter(consts)
                        for i in range(9):
                            if i == P: x[i] = p if cP == 'p' else cP
                            elif i == Q: x[i] = q if cQ == 'q' else cQ
                            else: x[i] = next(it)
                        if mt(x) != want(p,q): ok = False
                if ok: out.append((cP, cQ, consts))
    return out
reads = {int(v) for v in sys.argv[1].split(',')}
for P in range(9):
    for Q in range(9):
        if P == Q or P in reads or Q in reads: continue
        A = side(P, Q, lambda p,q: p and q); B = side(P, Q, lambda p,q: p or q)
        good = [(a,b) for a in A for b in B if 'p' in (a[0], b[0]) and 'q' in (a[1], b[1])]
        if good: print('P', P, 'Q', Q, len(good), good[0]); break
