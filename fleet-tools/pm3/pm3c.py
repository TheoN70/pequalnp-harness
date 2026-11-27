# CEGAR wrapper of pm3.py: solve on a growing row subset (UNSAT on a subset = UNSAT on all rows, sound);
# a SAT model is checked on all 512 rows, a wrong row is added. Same args as pm3.py.
import sys, os, inspect, json
here = os.path.dirname(os.path.realpath(__file__))
src = open(os.path.join(here, 'pm3.py')).read().split('with Solver')[0]
src = src.replace("F, wd = enc2(n, s, g, list(range(512)))", "F, wd = [], 2**n + n + s + 2")
exec(src)
from pysat.solvers import Solver
rows = sorted({r for r in range(512) if g(r) and bin(r).count('1') == 3} |                # the 6 minterms
              {511 ^ r for r in range(512) if not g(511 ^ r) and bin(r).count('1') == 3} | {0, 511})
it = 0
while True:
    it += 1
    G, _ = enc2(n, s, g, rows)
    pinF = [cl for cl in F]
    with Solver(name='cadical195', bootstrap_with=G + pinF) as S:
        if not S.solve():
            print('UNSAT', s, sys.argv[2:], 'rows', len(rows), 'iters', it); break
        m = {abs(v): v > 0 for v in S.get_model()}
    c = circsat.to_json(n, s, *circsat.decode(n, s, m))
    gs = [(op, ins) for op, ins in c['gates']]
    bad = [r for r in range(512) if wires(gs, r)[c['output']] != g(r)]
    if not bad:
        print('SAT', 'normal_form_ok' if normal_form(c) else 'NORMAL_FORM_FAILS', json.dumps(c)); break
    rows = sorted(set(rows) | {bad[0]})
    print('iter', it, 'rows', len(rows), flush=True)
