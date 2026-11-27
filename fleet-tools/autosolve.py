"""Find a circuit for a leased circuit unit, with no LLM: the desk's sketch if it already fits, else circsat (SAT).
Families: two-lit (`∃ C, FanInTwo C ∧ C.size ≤ k ∧ ∀ i j : Fin n, ...testBit`), `HasCircuitSize n (fun x => ...) k`
(the function is `x i` with && || ! or `Nat.testBit (A) (∑ i : Fin n, if x i then 2 ^ (i : ℕ) else 0)`), and
`RepSizeAtMost (fun (u : Fin n) (v : Fin m) => (mask : ℕ).testBit (m * u.val + v.val)) s` (AND/OR only).

Usage: sat-venv/bin/python -I autosolve.py <lease.json> <circuit.json>
Exit 0: circuit written (pequalnp numbering, for circuit2lean.py); 2: no circuit of <= k gates (UNSAT); 3: family not
recognised. The caller bounds the time (timeout) and the memory (capmem); the Lean check stays circuit2lean + pnp.sh.
"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import circsat, circuit2lean as c2l

HCS = re.compile(r"PEqualNP\.MetaComplexity\.HasCircuitSize (\d+) \(fun x : Fin \1 → Bool => (.*)\) (\d+)", re.S)
TB = re.compile(r"Nat\.testBit \(([\d\s*+^]+)\) \(∑ i : Fin (\d+), if x i then 2 \^ \(i : ℕ\) else 0\)")
TOK = re.compile(r"\s*(x \d+|&&|\|\||!|\(|\)|true|false)")


def bool_fun(n, body):
    """Python predicate on the input bits for the two function forms above; None if the body is anything else."""
    m = TB.fullmatch(body.strip())
    if m and int(m[2]) == n:
        if not re.fullmatch(r"[\d\s*+^]+", m[1]):
            return None
        a = eval(m[1].replace("^", "**"), {"__builtins__": {}})  # digits, spaces, * + ** only (checked above)
        return lambda x: bool(a >> sum(1 << i for i in range(n) if x[i]) & 1)
    out, pos = [], 0
    while pos < len(body):
        t = TOK.match(body, pos)
        if not t:
            return None if body[pos:].strip() else (lambda x: eval(" ".join(out), {"__builtins__": {}}, {"x": x}))
        tok, pos = t[1], t.end()
        if tok.startswith("x "):
            if int(tok[2:]) >= n:
                return None
            tok = f"x[{tok[2:]}]"
        out.append({"&&": "and", "||": "or", "!": "not", "true": "True", "false": "False"}.get(tok, tok))
    return lambda x: eval(" ".join(out), {"__builtins__": {}}, {"x": x})  # whitelisted tokens only


def problem(gap):
    """(n, k, table, rows or None, no_not, sketch circuit or None), or None for an unknown family."""
    st = gap["statement"].strip()
    m = c2l.TWO.fullmatch(st)
    if m:
        k, n, M = int(m[1]), int(m[2]), int(m[3])
        if int(m[4]) != n:
            return None
        rows = sorted({1 << i | 1 << j for i in range(n) for j in range(i, n)})
        table = sum(1 << (1 << i | 1 << j) for i in range(n) for j in range(i, n) if M >> (n * i + j) & 1)
        sk = None
        gates = [[op.lower(), [int(a) for a in args.split(",") if a.strip()]]
                 for op, args in re.findall(r"\b(AND|OR|NOT)\s*\(([^)]*)\)", gap.get("sketch") or "")]
        if 0 < len(gates) <= k:
            sk = {"n": n, "gates": gates, "output": n + len(gates) - 1}
        return n, k, table, rows, False, sk
    m = c2l.REP.fullmatch(st)
    if m:
        n, mm, k = int(m[1]), int(m[2]), int(m[4])
        mk = c2l.REP_MASK.fullmatch(m[3].strip())
        if not mk or int(mk[2]) != mm:
            return None
        pts = c2l.one_a_side(n, mm, int(mk[1]))
        return n + mm, k, sum(1 << r for r, v in pts if v), [r for r, _ in pts], True, None
    m = HCS.fullmatch(st)
    if m:
        n, k = int(m[1]), int(m[3])
        f = bool_fun(n, m[2])
        if f is None or n > 14:  # ponytail: n <= 14 is circuit2lean's ceiling
            return None
        return n, k, sum(1 << r for r in range(2 ** n) if f([bool(r >> i & 1) for i in range(n)])), None, False, None
    return None


def fits(c, n, table, rows, no_not):
    if no_not and any(op == "not" for op, _ in c["gates"]):
        return False
    try:
        return all(c2l.evaluate(c, [bool(r >> i & 1) for i in range(n)]) == bool(table >> r & 1)
                   for r in (range(2 ** n) if rows is None else rows))
    except Exception:  # a sketch reading a wire it should not
        return False


def main(lease, out):
    gap = json.load(open(lease))["gap"]
    p = problem(gap)
    if p is None:
        print("family not recognised", file=sys.stderr); sys.exit(3)
    n, k, table, rows, no_not, sk = p
    if sk and fits(sk, n, table, rows, no_not):
        c, how = sk, "sketch"
    else:
        c, how = circsat.solve(n, k, table, rows, no_not), "circsat"
        if c is None:
            print(f"UNSAT: no circuit of <= {k} gates", file=sys.stderr); sys.exit(2)
    json.dump(c, open(out, "w"))
    print(f"{out}: {len(c['gates'])} gates ({how})", file=sys.stderr)


def demo():
    # L_meta_25350 (merged): two-lit, n = 6, mask 2197163, <= 10 gates; the merged circuit is a valid sketch
    st = ("∃ C : PEqualNP.CircuitLowerBounds.Circuit, PEqualNP.MetaComplexity.FanInTwo C ∧ C.size ≤ 10 ∧ ∀ i j : Fin 6, "
          "C.eval (List.ofFn fun k : Fin 6 => decide (k = i ∨ k = j)) = (2197163 : ℕ).testBit (6 * min i.val j.val + max i.val j.val)")
    sk = "OR(3,4), OR(1,2), AND(6,7), NOT(4), NOT(2), NOT(5), OR(0,11), AND(9,12), AND(10,13), OR(8,14)"
    n, k, t, rows, nn, c = problem({"statement": st, "sketch": sk})
    assert (n, k, len(rows)) == (6, 10, 21) and c and fits(c, n, t, rows, nn)
    assert not fits({**c, "gates": c["gates"][:-1] + [["and", [8, 14]]]}, n, t, rows, nn)
    s = circsat.solve(n, k, t, rows)
    assert s is not None and fits(s, n, t, rows, nn)
    # HasCircuitSize: maj3 in both forms; 0xE8 = rows 3, 5, 6, 7
    for body in ("(x 0 && x 1) || (x 0 && x 2) || (x 1 && x 2)",
                 "Nat.testBit (232) (∑ i : Fin 3, if x i then 2 ^ (i : ℕ) else 0)"):
        p = problem({"statement": f"PEqualNP.MetaComplexity.HasCircuitSize 3 (fun x : Fin 3 → Bool => {body}) 4"})
        assert p and p[2] == 0xE8, (body, p)
    assert problem({"statement": "PEqualNP.MetaComplexity.HasCircuitSize 3 (fun x : Fin 3 → Bool => x 0 ^^ __import__) 4"}) is None
    assert problem({"statement": "PEqualNP.MetaComplexity.HasCircuitSize 3 (fun x : Fin 3 → Bool => x 5) 4"}) is None
    # RepSizeAtMost 2x2 identity: AND/OR only, 4 promise rows
    p = problem({"statement": "PEqualNP.Represents.RepSizeAtMost (fun (u : Fin 2) (v : Fin 2) => (9 : ℕ).testBit (2 * u.val + v.val)) 3"})
    assert p and p[0] == 4 and p[4] and len(p[3]) == 4
    assert circsat.solve(*p[:5]) is not None and circsat.solve(p[0], 2, *p[2:5]) is None
    print("demo ok")


if __name__ == "__main__":
    demo() if sys.argv[1:] == ["--demo"] else main(*sys.argv[1:3]) if len(sys.argv) == 3 else sys.exit(__doc__)
