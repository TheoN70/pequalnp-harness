"""Exact circuit-size SAT encoding of pequalnp's model (fan-in-2 AND/OR, NOT, every gate counted): "f has a circuit
of at most s gates" as CNF, and decoding of a model into a circuit.

The clauses are LinkN.enc2 n s g rows of PEqualNP.Library.LRAT.LinkN2 (pequalnp-proofs), ported clause for clause
(same variable numbering, same symmetry breaking), so an UNSAT certificate on this CNF is the one the Lean library
replays. Port by the L-meta-17389 SAT agent (2026-11-26), validated there; shared here with a CLI and a self-check.

Usage (run with fleet-tools/sat-venv/bin/python for `solve`):
  circsat.py cnf    <n> <s> <table> [-o f.cnf] [--rows 0,5,...] [--no-not]
  circsat.py solve  <n> <s> <table> [-o circuit.json] [--rows ...] [--no-not]   (CaDiCaL 1.9.5 via python-sat)
  circsat.py decode <n> <s> <solver output with "v" lines> [--table T] [-o circuit.json]
  circsat.py --demo  (self-check against brute force on all 2- and 3-input functions)
<table>: pequalnp table, hex (0x..) or decimal: bit r is f on row r, and input i is bit i of r (tableIndex).
--rows: only these rows (CEGAR: UNSAT on a subset is already a lower bound for f). --no-not: AND/OR only, by unit
  clauses on top (search only: it is not Defs.LratEncoding.enc2, so its certificates do not replay in Lean).
Output JSON is circuit2lean's format: {"n", "gates": [[op, [wires]]], "output"}, unused padding gates dropped.
"""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))  # circuit2lean, next to this file (python -I drops it)
from circuit2lean import check_table, evaluate


# ---- verbatim port of LinkN.enc2 (work/L-meta-17389/sat/gen.py) ------------------------------------------------
def enc2(n, s, g, rows):
    wd = 2**n + n + s + 2
    ix = lambda kd, j, a: (kd*(s+1)+j)*wd + a
    P = lambda v: v+1
    Q = lambda v: -(v+1)
    L = lambda v, b: P(v) if b else Q(v)
    tb = lambda r, k: (r >> k) & 1 == 1
    F = []
    for j in range(s): F.append([P(ix(0,j,t)) for t in range(4)])
    for e in (1,2):
        for j in range(s): F.append([P(ix(e,j,k)) for k in range(n+j+1)])
    for e in (1,2):
        for j in range(s):
            for r in rows:
                for k in range(n+j+1):
                    if k < n: F.append([Q(ix(e,j,k)), L(ix(e+3,j,r), tb(r,k))])
                    elif k < n+j:
                        F.append([Q(ix(e,j,k)), Q(ix(e+3,j,r)), P(ix(3,k-n,r))])
                        F.append([Q(ix(e,j,k)), P(ix(e+3,j,r)), Q(ix(3,k-n,r))])
                    else: F.append([Q(ix(e,j,k)), Q(ix(e+3,j,r))])
    for j in range(s):
        for r in rows:
            o=lambda t: Q(ix(0,j,t)); w=ix(3,j,r); a=ix(4,j,r); b=ix(5,j,r)
            F += [[o(0),Q(w),P(a)],[o(0),Q(w),P(b)],[o(0),P(w),Q(a),Q(b)],
                  [o(1),P(w),Q(a)],[o(1),P(w),Q(b)],[o(1),Q(w),P(a),P(b)],
                  [o(2),P(w)],[o(3),P(w),P(a)],[o(3),Q(w),Q(a)]]
    F.append([P(ix(6,0,k)) for k in range(n+s+1)])
    for r in rows:
        for k in range(n+s+1):
            if k < n:
                if tb(r,k) != g(r): F.append([Q(ix(6,0,k))])
            elif k < n+s: F.append([Q(ix(6,0,k)), L(ix(3,k-n,r), g(r))])
            elif g(r): F.append([Q(ix(6,0,k))])
    if s: F.append([P(ix(6,0,n+s-1)), P(ix(7,s-1,0))])
    for j in range(s):
        F += [[Q(ix(7,j,0)),P(ix(0,j,2))],[Q(ix(7,j,0)),P(ix(1,j,n+j))],[Q(ix(7,j,0)),P(ix(2,j,n+j))],
              [P(ix(7,j,0)),Q(ix(0,j,2))],[P(ix(7,j,0)),Q(ix(1,j,n+j))],[P(ix(7,j,0)),Q(ix(2,j,n+j))]]
    for j in range(s-1): F.append([Q(ix(7,j+1,0)), P(ix(7,j,0))])
    for j in range(s):
        for i in range(j):
            F += [[Q(ix(7,i,0)),Q(ix(1,j,n+i))],[Q(ix(7,i,0)),Q(ix(2,j,n+i))]]
    for j in range(s):
        for k in range(n+j+1):
            for l in range(k+1):
                F.append([Q(ix(1,j,k)),Q(ix(2,j,l)),P(ix(7,j,0))] + ([P(ix(0,j,3))] if l==k else []))
    for j in range(s-1):
        F.append([P(ix(1,j+1+t,n+j)) for t in range(s-1-j)] + [P(ix(2,j+1+t,n+j)) for t in range(s-1-j)] + [P(ix(7,j,0))])
    for j in range(s):
        for k in range(n+j+1): F.append([Q(ix(0,j,3)),Q(ix(1,j,k)),P(ix(2,j,k))])
    for j in range(s):
        for i in range(j): F.append([Q(ix(0,j,3)),Q(ix(0,i,3)),Q(ix(1,j,n+i))])
    # fLex
    for j in range(s-1):
        base = [P(ix(7,j,0)), P(ix(1,j+1,n+j)), P(ix(2,j+1,n+j))]
        for a in range(n+j+1):
            for b in range(a): F.append([Q(ix(1,j,a)),Q(ix(1,j+1,b))]+base)
            for c in range(n+j+1):
                for d in range(c):
                    F.append([Q(ix(1,j,a)),Q(ix(1,j+1,a)),Q(ix(2,j,c)),Q(ix(2,j+1,d))]+base)
                F.append([Q(ix(1,j,a)),Q(ix(1,j+1,a)),Q(ix(2,j,c)),Q(ix(2,j+1,c)),Q(ix(0,j,1))]+base)
                F.append([Q(ix(1,j,a)),Q(ix(1,j+1,a)),Q(ix(2,j,c)),Q(ix(2,j+1,c)),Q(ix(0,j+1,0))]+base)
    return F, wd


def decode(n, s, model):
    wd = 2**n + n + s + 2
    ix = lambda kd, j, a: (kd*(s+1)+j)*wd + a
    t = lambda v: model.get(v+1, False)
    gates=[]
    for j in range(s):
        op=[o for o in range(4) if t(ix(0,j,o))]
        a=[k for k in range(n+j+1) if t(ix(1,j,k))]; b=[k for k in range(n+j+1) if t(ix(2,j,k))]
        gates.append((op[0], a[0], b[0]))
    out=[k for k in range(n+s+1) if t(ix(6,0,k))][0]
    return gates, out
# ---- end of the port -----------------------------------------------------------------------------------------


def encode(n, s, table, rows=None, no_not=False):
    F, wd = enc2(n, s, lambda r: (table >> r) & 1 == 1, list(range(2**n)) if rows is None else rows)
    if no_not:
        F += [[-((0*(s+1)+j)*wd + 3 + 1)] for j in range(s)]  # op 3 (NOT) never chosen
    return F


def to_json(n, s, gates, out):
    """enc2 model -> circuit2lean JSON. op 0 AND, 1 OR, 2 padding (unused gate, read by nobody), 3 NOT(a)."""
    wire, js = {k: k for k in range(n)}, []
    for j, (op, a, b) in enumerate(gates):
        if op == 2:
            continue
        js.append(["not", [wire[a]]] if op == 3 else [["and", "or"][op], [wire[a], wire[b]]])
        wire[n + j] = n + len(js) - 1
    if out == n + s:
        sys.exit("output is enc2's constant false: f is constant 0, no circuit needed")
    if out not in wire:  # enc2 lets the output be a padding gate, which is true on every row
        sys.exit("output is a padding gate (true on every row): f is constant 1, which enc2 sizes wrongly; "
                 "pequalnp has no constant gate, NOT x OR x takes 2")
    return {"n": n, "gates": js, "output": wire[out]}


def solve(n, s, table, rows=None, no_not=False):
    """None if UNSAT, else the circuit (checked on the rows it was asked for)."""
    try:
        from pysat.solvers import Solver
    except ImportError:
        sys.exit("python-sat missing: run with fleet-tools/sat-venv/bin/python")
    with Solver(name="cadical195", bootstrap_with=encode(n, s, table, rows, no_not)) as S:
        if not S.solve():
            return None
        model = {abs(v): v > 0 for v in S.get_model()}
    c = to_json(n, s, *decode(n, s, model))
    for r in range(2 ** n) if rows is None else rows:
        assert evaluate(c, [bool(r >> i & 1) for i in range(n)]) == bool(table >> r & 1), f"decoded circuit wrong on row {r}"
    return c


def write_cnf(F, path):
    mx = max((abs(l) for c in F for l in c), default=0)
    with open(path, "w") as h:
        h.write(f"p cnf {mx} {len(F)}\n")
        for c in F:
            h.write(" ".join(map(str, c)) + " 0\n")


def main(argv):
    args, opt = [], {}
    it = iter(argv[1:])
    for a in it:
        if a in ("-o", "--rows", "--table"): opt[a] = next(it)
        elif a == "--no-not": opt[a] = True
        else: args.append(a)
    if len(args) != 4 or args[0] not in ("cnf", "solve", "decode"):
        sys.exit(__doc__)
    cmd, n, s = args[0], int(args[1]), int(args[2])
    rows = [int(r) for r in opt["--rows"].split(",")] if "--rows" in opt else None
    out = opt.get("-o")
    if cmd == "decode":
        model = {}
        for line in open(args[3]):
            if line.startswith("v"):
                model.update({abs(int(x)): int(x) > 0 for x in line.split()[1:] if int(x)})
        c = to_json(n, s, *decode(n, s, model))
        if "--table" in opt:
            check_table(c, hex(int(opt["--table"], 0))[2:])
    else:
        table = int(args[3], 0)
        if cmd == "cnf":
            F = encode(n, s, table, rows, "--no-not" in opt)
            write_cnf(F, out or f"f{s}.cnf")
            print(f"{out or f'f{s}.cnf'}: {len(F)} clauses", file=sys.stderr)
            return
        c = solve(n, s, table, rows, "--no-not" in opt)
        if c is None:
            print(f"UNSAT: no circuit of at most {s} gates" + (" on these rows" if rows else ""))
            return
        print(f"SAT: {len(c['gates'])} gates")
    if out:
        json.dump(c, open(out, "w"))
    else:
        print(json.dumps(c))


def brute_min(n, smax):
    """Least gate count of every n-input function up to smax gates, by enumerating all circuits (AND/OR on two
    distinct earlier wires, NOT on one). Size 0: an input, or the constant 0 (enc2's output wire n+s)."""
    full = (1 << 2 ** n) - 1
    xs = [sum(1 << r for r in range(2 ** n) if r >> i & 1) for i in range(n)]
    best = {f: 0 for f in xs + [0]}

    def go(w, k):
        if k == smax:
            return
        m = len(w)
        new = [w[a] & w[b] for a in range(m) for b in range(a + 1, m)] + \
              [w[a] | w[b] for a in range(m) for b in range(a + 1, m)] + [full ^ w[a] for a in range(m)]
        for v in new:
            if best.get(v, 99) > k + 1:
                best[v] = k + 1
            go(w + [v], k + 1)
    go(xs, 0)
    return best


def demo():
    assert solve(3, 3, 0xE8) is None and solve(3, 4, 0xE8) is not None  # maj3 needs exactly 4 gates
    assert solve(3, 4, 0xE8, no_not=True) is not None                    # maj3 is monotone
    assert solve(2, 1, 0b0110) is None                                   # xor2 ...
    assert solve(2, 4, 0b0110, no_not=True) is None and solve(2, 4, 0b0110) is not None  # needs a NOT
    checked = 0
    for n, smax in ((2, 4), (3, 4)):
        best = brute_min(n, smax)
        for f in range(1, (1 << 2 ** n) - 1):  # constants left out: see to_json
            m = best.get(f)
            if m is not None and m > 0:
                assert solve(n, m, f) is not None, (n, f, m)
                assert solve(n, m - 1, f) is None, (n, f, m)
            elif m is None:
                assert solve(n, smax, f) is None, (n, f, "brute force found none")
            checked += 1
    print(f"demo ok: {checked} functions, minimum size equal to brute force up to 4 gates")


if __name__ == "__main__":
    demo() if sys.argv[1:] == ["--demo"] else main(sys.argv)
