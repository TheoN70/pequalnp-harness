# PM 3x3 refute family (L-meta-27406 and siblings): is there a normal-form circuit of <= s gates for
# perm3 = OR of the 6 permutation triples, whose first gates are pinned?  Usage (sat-venv python):
#   pm3.py <s> [op,a,b op,a,b ...]      op in and/or/not; no gate given = no opening pinned (circsat enc2 as is).
# Pinned run: enc2 WITHOUT fLex (fLex can move pinned gates, so it is unsound then). SAT = circuit printed and checked
# against the statement's normal form; the step "¬ ∃ C ..." is then FALSE. UNSAT = no such circuit: the step is TRUE.
import sys, os, inspect, json
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../../fleet-tools')))
import circsat
from pysat.solvers import Solver
n, s = 9, int(sys.argv[1])
pins = [(p.split(',')[0], int(p.split(',')[1]), int(p.split(',')[2]) if p.count(',') > 1 else None) for p in sys.argv[2:]]
f = lambda x: (x[0]&x[4]&x[8])|(x[0]&x[5]&x[7])|(x[1]&x[3]&x[8])|(x[1]&x[5]&x[6])|(x[2]&x[3]&x[7])|(x[2]&x[4]&x[6])
bits = lambda r: [(r >> i) & 1 for i in range(n)]
g = lambda r: bool(f(bits(r)))
if pins:
    ns = {}; exec(inspect.getsource(circsat.enc2).split('    # fLex')[0] + '    return F, wd\n', ns); enc2 = ns['enc2']
else:
    enc2 = circsat.enc2
F, wd = enc2(n, s, g, list(range(512)))
ix = lambda kd, j, a: (kd*(s+1)+j)*wd + a + 1
OP = {'and': 0, 'or': 1, 'not': 3}
for j, (op, a, b) in enumerate(pins):
    F += [[ix(0, j, OP[op])], [ix(1, j, a)]] + ([[ix(2, j, b)]] if b is not None else [])

def wires(gs, r):
    w = bits(r)
    for op, ins in gs:
        v = [w[i] for i in ins]
        w.append(v[0] & v[1] if op == 'and' else v[0] | v[1] if op == 'or' else 1 - v[0])
    return w

def normal_form(c):
    gs = [(op, ins) for op, ins in c['gates']]; m = len(gs); W = [wires(gs, r) for r in range(512)]
    ok = c['output'] == n + m - 1 and m <= s
    ok &= all(W[r][-1] == g(r) for r in range(512))
    for j, (op, ins) in enumerate(gs):
        ok &= (op == 'not' and len(ins) == 1) or (op in ('and', 'or') and len(ins) == 2 and ins[0] < ins[1])
        col = [W[r][n+j] for r in range(512)]
        ok &= len(set(col)) == 2                                                # not constant
        ok &= all(any(W[r][k] != col[r] for r in range(512)) for k in range(n+j))  # differs from every earlier wire
        ok &= j == m-1 or any(n+j in gs[k][1] for k in range(j+1, m))            # read by a later gate
    ok &= all(gs[j][0] == p[0] and gs[j][1] == [p[1]] + ([p[2]] if p[2] is not None else []) for j, p in enumerate(pins))
    return bool(ok)

with Solver(name='cadical195', bootstrap_with=F) as S:
    if S.solve():
        m = {abs(v): v > 0 for v in S.get_model()}
        c = circsat.to_json(n, s, *circsat.decode(n, s, m))
        print('SAT', 'normal_form_ok' if normal_form(c) else 'NORMAL_FORM_FAILS', json.dumps(c))
    else:
        print('UNSAT', s, sys.argv[2:])
