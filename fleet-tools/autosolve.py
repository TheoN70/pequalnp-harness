"""Find a circuit for a leased circuit unit, with no LLM: the desk's sketch if it already fits, else circsat (SAT).
Families: two-lit (`∃ C, FanInTwo C ∧ C.size ≤ k ∧ ∀ i j : Fin n, ...testBit`), `HasCircuitSize n (fun x => ...) k`
(the function is `x i` with && || ! or `Nat.testBit (A) (∑ i : Fin n, if x i then 2 ^ (i : ℕ) else 0)`), and
`RepSizeAtMost (fun (u : Fin n) (v : Fin m) => (mask : ℕ).testBit (m * u.val + v.val)) s` (AND/OR only).

RepSizeAtMost first tries `lsr` (local search, LSR_S seconds, default 30): exact SAT took > 10 min on a 4x6 at 11 gates
(merged L_meta_23657, edisonhello's `upper_mono : Monotone2 upperC` family), lsr finds such circuits in seconds.

Usage: sat-venv/bin/python -I autosolve.py <lease.json> <circuit.json>
Exit 0: circuit written (pequalnp numbering, for circuit2lean.py); 2: no circuit of <= k gates (UNSAT); 3: family not
recognised. The caller bounds the time (timeout) and the memory (capmem); the Lean check stays circuit2lean + pnp.sh.
"""
import fcntl, json, os, re, subprocess, sys, time
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
        return n, k, table, rows, False, sk, None
    m = c2l.rep_parts(st)
    if m:
        n, mm, body, k = m
        mk = c2l.REP_MASK.fullmatch(body.strip())
        if not mk or int(mk[2]) != mm:
            return None
        pts = c2l.one_a_side(n, mm, int(mk[1]))
        return n + mm, k, sum(1 << r for r, v in pts if v), [r for r, _ in pts], True, None, (n, mm, int(mk[1]))
    m = c2l.mono_parts(st)
    if m and m[0] <= 6:  # live's 64-bit tables
        return m[0], m[2], m[1], None, True, None, None
    m = HCS.fullmatch(st)
    if m:
        n, k = int(m[1]), int(m[3])
        f = bool_fun(n, m[2])
        if f is None or n > 14:  # ponytail: n <= 14 is circuit2lean's ceiling
            return None
        return n, k, sum(1 << r for r in range(2 ** n) if f([bool(r >> i & 1) for i in range(n)])), None, False, None, None
    return None


def lsr(n, m, mask, k, secs):
    """fleet-tools/lsr with k gates: wires 0..n-1 left, n..n+m-1 right, gate i = wire i, output = last gate; None if none.
    One seed on our core, plus one per extra free core `slots` grants (up to LSR_PAR - 1 = 3); the first FOUND wins."""
    here = os.path.dirname(os.path.abspath(__file__))
    a = "".join("1" if mask >> (m * u + v) & 1 else "0" for u in range(n) for v in range(m))
    extra = []
    for want in range(int(os.environ.get("LSR_PAR", 4)) - 1, 0, -1):
        r = subprocess.run([os.path.join(here, "slots"), str(want)], capture_output=True, text=True)
        if r.returncode == 0:
            extra = [c for part in r.stdout.strip().split(",") for c in
                     (range(int(part.split("-")[0]), int(part.split("-")[-1]) + 1))]
            break
    cmd = [os.path.join(here, "lsr"), str(k), "", str(secs), str(n), str(m), a]
    ps = [subprocess.Popen((["taskset", "-c", str(c)] if c is not None else []) + cmd[:2] + [str(seed)] + cmd[3:],
                           stdout=subprocess.PIPE, text=True) for seed, c in enumerate([None] + extra, 1)]
    out = ""
    try:
        deadline = time.time() + secs + 30
        while time.time() < deadline and not out:
            for p in ps:
                if p.poll() is not None:
                    o = p.stdout.read()
                    if "FOUND" in o:
                        out = o; break
            if all(p.poll() is not None for p in ps):
                break
            time.sleep(0.5)
    finally:
        for p in ps:
            p.kill()
    gates = [[op.lower(), [int(x), int(y)]] for op, x, y in re.findall(r"w\d+ = (AND|OR)\(w(\d+),w(\d+)\)", out)]
    return {"n": n + m, "gates": gates, "output": n + m + len(gates) - 1} if "FOUND" in out and gates else None


def live(n, k, table, secs):
    """fleet-tools/live mode 0 (exact AND/OR size, all 2^n rows, n <= 6), sizes 1..k: a circuit, False (none of <= k
    gates: exact) or None (time out). Its steps print operand tables; each maps back to a wire by its table."""
    exe = os.path.join(os.path.dirname(os.path.abspath(__file__)), "live")
    t64 = sum(1 << r for r in range(64) if table >> (r % 2 ** n) & 1)  # inputs >= n ignored
    try:
        out = subprocess.run([exe, f"{t64:016x}", hex(2 ** n - 1), "0", "0", "1", str(k), "26"],
                             capture_output=True, text=True, timeout=secs).stdout
    except (OSError, subprocess.TimeoutExpired):
        return None
    if "FOUND" not in out:
        return False if f"N={k} none" in out else None
    wire = {sum(1 << r for r in range(64) if r >> i & 1): i for i in range(n)}
    gates = []
    for op, a, b, z in re.findall(r"^\s+(and|or) ([0-9a-f]{16}) ([0-9a-f]{16}) -> ([0-9a-f]{16})", out, re.M):
        gates.append([op, [wire[int(a, 16)], wire[int(b, 16)]]])
        wire.setdefault(int(z, 16), n + len(gates) - 1)
    return {"n": n, "gates": gates, "output": n + len(gates) - 1}


def shown_false(lease):
    """rep_lower_gen.py --is-false (3x5, 4x5, 5x5: counting, read-once trees, or its Lean proof compiles, ~40 s on its own
    `slots` core under capmem 6G): True only when shown false. L-meta-21050 (4x5 <= 9): lsr stuck at error 1 for 240 s."""
    here = os.path.dirname(os.path.abspath(__file__))
    try:
        return subprocess.run([sys.executable, "-I", os.path.join(here, "rep_lower_gen.py"), "--is-false", lease],
                              capture_output=True, timeout=int(os.environ.get("REFUTE_S", 60))).returncode == 0
    except subprocess.TimeoutExpired:
        return False


def sat_slot():
    """Hold one of SAT_PAR (3) lock files while circsat runs: heavy searches stay few across parallel runs (memory).
    Waits for a slot; the caller's timeout bounds the wait."""
    penp = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    while True:
        for i in range(int(os.environ.get("SAT_PAR", 3))):
            h = open(os.path.join(penp, f"pequalnp-sat{i}.lock"), "w")
            try:
                fcntl.flock(h, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return h  # kept open until the process ends
            except OSError:
                h.close()
        time.sleep(1)


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
    n, k, table, rows, no_not, sk, rep = p
    if rep and not sk and shown_false(lease):
        print("UNSAT (rep_lower_gen --is-false): false at this bound", file=sys.stderr); sys.exit(2)
    if rep and not sk:
        sk = lsr(*rep, k, int(os.environ.get("LSR_S", 60)))
    if no_not and rows is None:  # the monotone truth-table family: live is exact both ways, in < 1 s on 5 inputs
        sk = live(n, k, table, int(os.environ.get("LIVE_S", 60)))
        if sk is False:
            print(f"UNSAT (live): no AND/OR circuit of <= {k} gates", file=sys.stderr); sys.exit(2)
    if sk and fits(sk, n, table, rows, no_not):
        c, how = sk, "sketch" if not no_not else "lsr" if rep else "live"
    else:
        slot = sat_slot()
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
    n, k, t, rows, nn, c, _ = problem({"statement": st, "sketch": sk})
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
    assert p and p[0] == 4 and p[4] and len(p[3]) == 4 and p[6] == (2, 2, 9)
    assert circsat.solve(*p[:5]) is not None and circsat.solve(p[0], 2, *p[2:5]) is None
    c = lsr(2, 2, 9, 3, 5)
    assert c and fits(c, *p[0:1], p[2], p[3], True), c
    # monotone truth-table family (L-meta-16081, 0xeae8e880): live none at 9, a 10-gate circuit at 10
    mono = ("∃ C : PEqualNP.CircuitLowerBounds.Circuit, PEqualNP.MetaComplexity.Monotone2 C ∧ C.size ≤ {} ∧ ∀ x : Fin 5 → Bool, "
            "C.eval (List.ofFn x) = Nat.testBit 0xeae8e880 (∑ i : Fin 5, if x i then 2 ^ (i : ℕ) else 0)")
    p = problem({"statement": mono.format(10)})
    assert p and p[:2] == (5, 10) and p[4] and p[3] is None
    assert live(5, 9, p[2], 30) is False
    c = live(5, 10, p[2], 30)
    assert c and fits(c, 5, p[2], None, True), c
    # RepSizeAtMost with `fun u v : Fin n` binders (L-meta-20213, 8x8)
    p = problem({"statement": "PEqualNP.Represents.RepSizeAtMost (fun u v : Fin 8 => (9891717104032518705 : ℕ).testBit (8 * u.val + v.val)) 24"})
    assert p and p[0] == 16 and p[6] == (8, 8, 9891717104032518705)
    print("demo ok")


if __name__ == "__main__":
    demo() if sys.argv[1:] == ["--demo"] else main(*sys.argv[1:3]) if len(sys.argv) == 3 else sys.exit(__doc__)
