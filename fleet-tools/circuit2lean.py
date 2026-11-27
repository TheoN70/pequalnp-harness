"""Write the Lean proof of a desk step `HasCircuitSize n f k` from a circuit that computes f, of a two-lit step
(`∃ C, FanInTwo C ∧ C.size ≤ k ∧ ∀ i j : Fin n, ...`, circuit also as the desk sketch `OR(2,4), NOT(5), ...`), or of a one-a-side
promise step `RepSizeAtMost (fun (u : Fin n) (v : Fin m) => ...) s` from an AND/OR circuit on n+m wires (left vertex u
= wire u, right v = wire n+v; values checked only on the n*m promise rows; detected from the statement, no flag).

Usage: python3 -I circuit2lean.py <lease-or-gap.json> <circuit> [--reverse-inputs] [--table HEX] [--split K] [-o out.lean]

<circuit> is either
  - JSON: {"n": 3, "gates": [["and", [0, 1]], ["not", [3]], ...], "output": 5}
    wires 0..n-1 are the inputs, gate j makes wire n + j (pequalnp's own numbering, gates in order);
  - a .bench file (Cirbo: `c.into_bench().format_circuit()`): INPUT(..) lines in input order, OUTPUT(..),
    `y = AND(a, b)` / OR / NOT / LNOT / RNOT / IFF / LIFF / RIFF / BUFF. Gates unreachable from the output
    are dropped; identity gates (IFF...) cost nothing.
--reverse-inputs: circuit input k is pequalnp input n-1-k. Needed when the Cirbo truth table was a pequalnp
  table read as is (Cirbo row j puts input 0 on the most significant bit; pequalnp row r has input i = bit i).
  Not needed when the Cirbo table was built from f applied to the input vector, as work/*/cirbo/run.py does.
--table HEX: also check the circuit in Python against the pequalnp table (bit r = f on row r, input i = bit i of r).

--split K: fix the first K inputs; one `decide +kernel` lemma per prefix (2^(n-K) rows each), joined by `match`.
  Default n-8 (leaves of 256 rows). The kernel's memory grows with the rows of ONE check, not with n: measured
  2026-11-26 (one core, `lake env lean`): 1024 rows in one check 5.8 GB (the checker allows ~6.5), 4096 rows > 8 GB;
  with the default, n=10 3.5 GB / 26 s, n=12 4.0 GB / 120 s, n=14 4.6 GB / 506 s. Time still doubles per input
  (~30 ms a row) and the checker replays the kernel twice within 20 min: n = 14 (~17 min) is the ceiling.

The proof (same shape as the merged L_meta_1001): the circuit as a `def`, `FanInTwo` by cases, the size by
`decide`, and the values on all 2^n rows by `decide +kernel`. The Lean checker is the judge: run
`tools/pnp.sh check <id>` (under capmem) on the written file.
"""
import json, re, sys

MAX_BYTES = 512 * 1024
SPLIT_AT = 8  # default --split = n - SPLIT_AT: leaves of 256 rows (measured 2026-11-26, see the docstring)


def parse_bench(text):
    inputs, output, defs = [], None, {}
    for raw in text.splitlines():
        line = raw.split("#")[0].strip()
        if not line:
            continue
        m = re.fullmatch(r"INPUT\((.+)\)", line)
        if m:
            inputs.append(m[1].strip()); continue
        m = re.fullmatch(r"OUTPUT\((.+)\)", line)
        if m:
            if output is not None:
                sys.exit("bench: more than one OUTPUT")
            output = m[1].strip(); continue
        m = re.fullmatch(r"(\S+)\s*=\s*([A-Z_]+)\((.*)\)", line)
        if not m:
            sys.exit(f"bench: cannot read line {raw!r}")
        defs[m[1]] = (m[2], [a.strip() for a in m[3].split(",") if a.strip()])
    if output is None:
        sys.exit("bench: no OUTPUT")
    n = len(inputs)
    wire = {name: i for i, name in enumerate(inputs)}
    gates = []

    def build(name, seen=()):
        if name in wire:
            return wire[name]
        if name not in defs or name in seen:
            sys.exit(f"bench: wire {name} undefined or cyclic")
        op, args = defs[name]
        sub = lambda a: build(a, seen + (name,))
        if op in ("IFF", "LIFF", "BUFF"):
            w = sub(args[0])
        elif op == "RIFF":
            w = sub(args[1])
        elif op in ("NOT", "LNOT", "RNOT"):
            a = sub(args[1] if op == "RNOT" else args[0])
            gates.append(["not", [a]]); w = n + len(gates) - 1
        elif op in ("AND", "OR"):
            if len(args) != 2:
                sys.exit(f"bench: {name} = {op} needs two wires")
            a, b = sub(args[0]), sub(args[1])
            gates.append([op.lower(), [a, b]]); w = n + len(gates) - 1
        else:
            sys.exit(f"bench: gate {op} is not AND/OR/NOT (pequalnp's basis)")
        wire[name] = w
        return w

    out = build(output)
    return {"n": n, "gates": gates, "output": out}


def reverse_inputs(c):
    n = c["n"]
    f = lambda w: n - 1 - w if w < n else w
    return {"n": n, "gates": [[op, [f(a) for a in args]] for op, args in c["gates"]], "output": f(c["output"])}


def check_shape(c, n_stmt, k):
    n, gates = c["n"], c["gates"]
    if n != n_stmt:
        sys.exit(f"circuit has {n} inputs, the statement {n_stmt}")
    for j, (op, args) in enumerate(gates):
        if op not in ("and", "or", "not"):
            sys.exit(f"gate {j}: op {op} not in and/or/not")
        if len(args) > 2 or (op == "not" and len(args) != 1):
            sys.exit(f"gate {j}: {op} with {len(args)} wires")
        if any(not (0 <= a < n + j) for a in args):
            sys.exit(f"gate {j} reads a wire that does not exist yet: {args}")
    if not (0 <= c["output"] < n + len(gates)):
        sys.exit(f"output wire {c['output']} does not exist")
    if len(gates) > k:
        sys.exit(f"{len(gates)} gates > bound {k}")


def evaluate(c, bits):
    w = list(bits)
    for op, args in c["gates"]:
        v = [w[a] for a in args]
        w.append(all(v) if op == "and" else any(v) if op == "or" else not v[0])
    return w[c["output"]]


def check_table(c, hexs):
    n, t = c["n"], int(hexs, 16)
    for r in range(2 ** n):
        if evaluate(c, [bool(r >> i & 1) for i in range(n)]) != bool(t >> r & 1):
            sys.exit(f"circuit differs from the table on row {r}")


def cofactors(n, k):
    """ev0 : ∀ b0..b(n-1), C0.eval [..] = F (..). With k > 0 the first k inputs are fixed: one `decide +kernel` lemma per
    prefix (2^k of them, 2^(n-k) rows each, checked separately), joined by a binary tree of `match` on the Booleans."""
    def stmt(prefix):
        vals = [str(bool(int(b))).lower() for b in prefix] + [f"b{i}" for i in range(len(prefix), n)]
        free = " ".join(f"b{i}" for i in range(len(prefix), n))
        body = f"C0.eval [{', '.join(vals)}] = F (fun i => [{', '.join(vals)}].getD i.val false)"
        return f"∀ {free} : Bool,\n    {body}" if free else body
    name = lambda p: "ev0" if not p else "ev_" + p
    out = []
    for d in range(k, -1, -1):  # leaves first: Lean needs each lemma before its use
        for v in range(2 ** d):
            p = format(v, f"0{d}b") if d else ""
            if d == k:
                out.append(f"theorem {name(p)} : {stmt(p)} := by\n  decide +kernel\n")
            else:
                out.append(f"theorem {name(p)} : {stmt(p)} := fun b{d} =>\n  match b{d} with\n"
                           f"  | false => {name(p + '0')}\n  | true => {name(p + '1')}\n")
    return "\n".join(out)


TWO = re.compile(r"∃ C : PEqualNP\.CircuitLowerBounds\.Circuit, PEqualNP\.MetaComplexity\.FanInTwo C ∧ C\.size ≤ (\d+) ∧ "
                 r"∀ i j : Fin (\d+), C\.eval \(List\.ofFn fun k : Fin \2 => decide \(k = i ∨ k = j\)\) = "
                 r"\((\d+) : ℕ\)\.testBit \((\d+) \* min i\.val j\.val \+ max i\.val j\.val\)")


def parse_sketch(text):
    """The desk's sketch: `OR(2,4), NOT(5), AND(0,6), ...`; gate k makes wire n + k, the output is the last gate (n is
    filled in from the statement)."""
    gates = [[op.lower(), [int(x) for x in args.split(",") if x.strip()]]
             for op, args in re.findall(r"\b(AND|OR|NOT)\s*\(([^)]*)\)", text)]
    if not gates:
        sys.exit("sketch: no AND(a,b) / OR(a,b) / NOT(a) found")
    return {"n": None, "gates": gates, "output": None}


def lean_twolit(gap, c, mt):
    """`∃ C, FanInTwo C ∧ C.size ≤ k ∧ ∀ i j : Fin n, C.eval (inputs i and j on) = M.testBit (n * min + max)` (the
    "two-lit function of the graph H" family): circuit, FanInTwo by cases, size and the n*n values by decide."""
    k, n, M, n2 = int(mt[1]), int(mt[2]), int(mt[3]), int(mt[4])
    if n2 != n:
        sys.exit(f"statement indexes the mask with {n2} * min, not n = {n}")
    if c["n"] is None:  # a sketch: inputs are the n wires, output the last gate
        c = {"n": n, "gates": c["gates"], "output": n + len(c["gates"]) - 1}
    check_shape(c, n, k)
    for i in range(n):
        for j in range(n):
            if evaluate(c, [x in (i, j) for x in range(n)]) != bool(M >> (n * min(i, j) + max(i, j)) & 1):
                sys.exit(f"circuit differs from the statement at i={i}, j={j}")
    mod, g = gap["module"], len(c["gates"])
    gl = ", ".join(f"⟨GateOp.{op}, [{', '.join(map(str, a))}]⟩" for op, a in c["gates"])
    ok = ("  intro g hg\n  simp only [C0, List.mem_cons, List.not_mem_nil, or_false] at hg\n"
          f"  rcases hg with {' | '.join(['rfl'] * g)} <;> simp") if g else "  intro g hg\n  simp [C0] at hg"
    text = f"""{chr(10).join('import ' + i for i in gap.get('imports') or ['PEqualNP.Defs'])}

namespace {mod}

open PEqualNP.CircuitLowerBounds PEqualNP.MetaComplexity

/-- {g} gates; wires 0..{n - 1} are the inputs, gate j makes wire {n} + j. -/
def C0 : Circuit := ⟨[{gl}], {c['output']}⟩

theorem ok0 : FanInTwo C0 := by
{ok}

end {mod}

theorem {mod} : {gap['statement'].strip()} :=
  ⟨{mod}.C0, {mod}.ok0, by decide, by decide +kernel⟩
"""
    if len(text.encode()) > MAX_BYTES:
        sys.exit(f"file is {len(text.encode())} bytes > 512 KiB")
    return text


REP = re.compile(r"PEqualNP\.Represents\.RepSizeAtMost \(fun (?:\(u : Fin (\d+)\) \(v : Fin (\d+)\)|u v : Fin (\d+)) => (.*)\) (\d+)", re.S)
# five-input-style monotone family: `∃ C, Monotone2 C ∧ C.size ≤ k ∧ ∀ x : Fin n → Bool, C.eval (List.ofFn x) = Nat.testBit T (∑ ...)`
MONO = re.compile(r"∃ C : PEqualNP\.CircuitLowerBounds\.Circuit, PEqualNP\.MetaComplexity\.Monotone2 C ∧ C\.size ≤ (\d+) ∧ "
                  r"∀ x : Fin (\d+) → Bool, C\.eval \(List\.ofFn x\) = Nat\.testBit (0x[0-9a-fA-F]+|\d+) "
                  r"\(∑ i : Fin \2, if x i then 2 \^ \(i : ℕ\) else 0\)")


def rep_parts(st):
    """(n, m, graph body, s) of a RepSizeAtMost statement, binders `(u : Fin n) (v : Fin m)` or `u v : Fin n`; or None."""
    mt = REP.fullmatch(st.strip())
    if not mt:
        return None
    n, m = (int(mt[1]), int(mt[2])) if mt[1] else (int(mt[3]), int(mt[3]))
    return n, m, mt[4], int(mt[5])


def mono_parts(st):
    """(n, table, k) of the monotone truth-table statement (MONO), or None."""
    mt = MONO.fullmatch(st.strip())
    return (int(mt[2]), int(mt[3], 0), int(mt[1])) if mt else None
REP_MASK = re.compile(r"\((\d+) : ℕ\)\.testBit \((\d+) \* u\.val \+ v\.val\)")


def one_a_side(n, m, mask):
    """The promise rows of a one-a-side n x m graph: [(row, value)], row = left u on (wire u) + right v on (wire n + v),
    value = bit (m * u + v) of mask, as in `oneEach u v` and the desk's `(mask : ℕ).testBit (m * u.val + v.val)`."""
    return [((1 << u) | (1 << (n + v)), bool(mask >> (m * u + v) & 1)) for u in range(n) for v in range(m)]


def check_rows(c, rows):
    for r, want in rows:
        if evaluate(c, [bool(r >> i & 1) for i in range(c["n"])]) != want:
            sys.exit(f"circuit differs from the graph on promise row {r}")


def lean_rep(gap, c, parts):
    """`RepSizeAtMost A s` (AND/OR only, values asked only on the n*m one-a-side inputs): circuit, `Monotone2` by cases,
    size and `Represents` by decide (n*m rows, no splitting needed)."""
    n, m, body, k = parts
    if any(op == "not" for op, _ in c["gates"]):
        sys.exit("RepSizeAtMost allows AND/OR only: the circuit has a NOT gate")
    check_shape(c, n + m, k)
    mk = REP_MASK.fullmatch(body.strip())
    if mk and int(mk[2]) == m:
        check_rows(c, one_a_side(n, m, int(mk[1])))
    else:
        print("graph is not `(mask : ℕ).testBit (m * u.val + v.val)`: not checked in Python, Lean will judge",
              file=sys.stderr)
    return lean_monotone(gap, c, f"wires 0..{n - 1} are the left vertices, {n}..{n + m - 1} the right ones, gate j makes wire {n + m} + j")


def lean_mono(gap, c, parts):
    """The monotone truth-table statement (MONO): AND/OR circuit checked on all 2^n rows, then as lean_rep (L-meta-16081)."""
    n, table, k = parts
    if any(op == "not" for op, _ in c["gates"]):
        sys.exit("Monotone2 allows AND/OR only: the circuit has a NOT gate")
    check_shape(c, n, k)
    check_rows(c, [(r, bool(table >> r & 1)) for r in range(2 ** n)])
    return lean_monotone(gap, c, f"wires 0..{n - 1} are the inputs, gate j makes wire {n} + j")


def lean_monotone(gap, c, doc):
    """⟨C0, Monotone2 by cases, size by decide, values by decide +kernel⟩."""
    mod, g = gap["module"], len(c["gates"])
    gl = ", ".join(f"⟨GateOp.{op}, [{', '.join(map(str, a))}]⟩" for op, a in c["gates"])
    ok = ("  intro g hg\n  simp only [C0, List.mem_cons, List.not_mem_nil, or_false] at hg\n"
          f"  rcases hg with {' | '.join(['rfl'] * g)} <;> simp") if g else "  intro g hg\n  simp [C0] at hg"
    text = f"""{chr(10).join('import ' + i for i in gap.get('imports') or ['PEqualNP.Defs'])}

namespace {mod}

open PEqualNP.CircuitLowerBounds PEqualNP.MetaComplexity

/-- {g} gates; {doc}. -/
def C0 : Circuit := ⟨[{gl}], {c['output']}⟩

theorem ok0 : Monotone2 C0 := by
{ok}

end {mod}

theorem {mod} : {gap['statement'].strip()} :=
  ⟨{mod}.C0, {mod}.ok0, by decide, by decide +kernel⟩
"""
    if len(text.encode()) > MAX_BYTES:
        sys.exit(f"file is {len(text.encode())} bytes > 512 KiB")
    return text


def lean(gap, c, split=None):
    mt = rep_parts(gap["statement"])
    if mt:
        return lean_rep(gap, c, mt)
    mt = mono_parts(gap["statement"])
    if mt:
        return lean_mono(gap, c, mt)
    mt = TWO.fullmatch(gap["statement"].strip())
    if mt:
        return lean_twolit(gap, c, mt)
    if c["n"] is None:
        sys.exit("the sketch format (OR(a,b), NOT(a)...) is read only for the two-lit statement; give JSON or .bench")
    m = re.fullmatch(r"PEqualNP\.MetaComplexity\.HasCircuitSize (\d+) (\(fun .*\)) (\d+)", gap["statement"].strip(), re.S)
    if not m:
        sys.exit("statement is neither `PEqualNP.MetaComplexity.HasCircuitSize n (fun ...) k` nor `PEqualNP.Represents.RepSizeAtMost (fun (u : Fin n) (v : Fin m) => ...) s`")
    n, fun, k = int(m[1]), m[2], int(m[3])
    split = max(0, n - SPLIT_AT) if split is None else split
    if not 0 <= split <= n:
        sys.exit(f"--split {split}: must be between 0 and n = {n}")
    check_shape(c, n, k)
    mod, g = gap["module"], len(c["gates"])
    gl = ", ".join(f"⟨GateOp.{op}, [{', '.join(map(str, a))}]⟩" for op, a in c["gates"])
    bs = [f"b{i}" for i in range(n)]
    xs = [f"x {i}" for i in range(n)]
    cases = " | ".join(["rfl"] * g) if g else ""
    ok = ("  intro g hg\n  simp only [C0, List.mem_cons, List.not_mem_nil, or_false] at hg\n"
          f"  rcases hg with {cases} <;> simp") if g else "  intro g hg\n  simp [C0] at hg"
    arms = "\n".join(f"  | ⟨{i}, _⟩ => rfl" for i in range(n))
    body = f"""{chr(10).join('import ' + i for i in gap.get('imports') or ['PEqualNP.Defs'])}

namespace {mod}

open PEqualNP.CircuitLowerBounds PEqualNP.MetaComplexity

/-- The function of the statement. -/
def F : (Fin {n} → Bool) → Bool := {fun}

/-- {g} gates; wires 0..{n - 1} are the inputs, gate j makes wire {n} + j. -/
def C0 : Circuit := ⟨[{gl}], {c['output']}⟩

theorem ok0 : FanInTwo C0 := by
{ok}

{cofactors(n, split)}

theorem ofFn{n} (x : Fin {n} → Bool) : List.ofFn x = [{', '.join(xs)}] := by
  simp [List.ofFn_succ]

theorem vec (x : Fin {n} → Bool) : (fun i : Fin {n} => [{', '.join(xs)}].getD i.val false) = x := by
  funext i
  match i with
{arms}
  | ⟨_ + {n}, h⟩ => exact absurd h (by omega)

end {mod}

theorem {mod} : {gap['statement'].strip()} :=
  ⟨{mod}.C0, {mod}.ok0, by decide, fun x => by
      rw [{mod}.ofFn{n}]
      exact ({mod}.ev0 {' '.join('(' + x + ')' for x in xs)}).trans (congrArg {mod}.F ({mod}.vec x))⟩
"""
    if len(body.encode()) > MAX_BYTES:
        sys.exit(f"file is {len(body.encode())} bytes > 512 KiB")
    return body


def main(argv):
    args = argv[1:]
    out = rev = table = split = None
    rest = []
    while args:
        a = args.pop(0)
        if a == "-o": out = args.pop(0)
        elif a == "--reverse-inputs": rev = True
        elif a == "--table": table = args.pop(0)
        elif a == "--split": split = int(args.pop(0))
        else: rest.append(a)
    if len(rest) != 2:
        sys.exit(__doc__)
    d = json.load(open(rest[0]))
    gap = d.get("gap", d)
    text = open(rest[1]).read()
    c = json.loads(text) if text.lstrip().startswith("{") else \
        parse_sketch(text) if re.match(r"\s*(AND|OR|NOT)\s*\(", text) else parse_bench(text)
    if rev:
        c = reverse_inputs(c)
    if table:
        check_table(c, table)
    body = lean(gap, c, split)
    if out:
        open(out, "w").write(body)
        print(f"{out}: {len(c['gates'])} gates, {len(body.encode())} bytes", file=sys.stderr)
    else:
        sys.stdout.write(body)


def demo():
    # maj3 from Cirbo's bench, then check: the table of "at least 2 of 3" is 0xE8 (rows 3,5,6,7)
    bench = "INPUT(0)\nINPUT(1)\nINPUT(2)\nOUTPUT(s6)\ns3 = AND(1, 2)\ns4 = OR(1, 2)\ns5 = AND(0, s4)\ns6 = OR(s3, s5)\n"
    c = parse_bench(bench)
    assert c == {"n": 3, "gates": [["and", [1, 2]], ["or", [1, 2]], ["and", [0, 4]], ["or", [3, 5]]], "output": 6}, c
    check_table(c, "e8")
    assert reverse_inputs(reverse_inputs(c)) == c
    lnot = parse_bench("INPUT(a)\nINPUT(b)\nOUTPUT(y)\nt = LNOT(a, b)\ny = IFF(t)\n")
    assert lnot == {"n": 2, "gates": [["not", [0]]], "output": 2}, lnot
    # cofactor tree: 2^k leaves by decide, 2^k - 1 match nodes, every name defined before use, root ev0
    t = cofactors(3, 2)
    names = re.findall(r"theorem (\w+) :", t)
    assert names == ["ev_00", "ev_01", "ev_10", "ev_11", "ev_0", "ev_1", "ev0"], names
    assert t.count("decide +kernel") == 4 and "[true, false, b2]" in t
    assert cofactors(3, 0).count("decide +kernel") == 1 and "theorem ev0 : ∀ b0 b1 b2" in cofactors(3, 0)
    assert "theorem ev_111 : C0.eval [true, true, true]" in cofactors(3, 3)  # k = n: closed rows
    # RepSizeAtMost: 2x2 identity graph (mask 0b1001), wires u0 u1 v0 v1, AND(u0,v0) OR AND(u1,v1)
    gap = {"module": "M", "statement": "PEqualNP.Represents.RepSizeAtMost (fun (u : Fin 2) (v : Fin 2) => "
           "(9 : ℕ).testBit (2 * u.val + v.val)) 3"}
    rep = {"n": 4, "gates": [["and", [0, 2]], ["and", [1, 3]], ["or", [4, 5]]], "output": 6}
    assert one_a_side(2, 2, 9) == [(5, True), (9, False), (6, False), (10, True)]
    assert "Monotone2 C0" in lean(gap, rep) and "by decide +kernel⟩" in lean(gap, rep)
    for bad in ({**rep, "output": 4}, {**rep, "gates": rep["gates"] + [["or", [6, 6]]], "output": 7},
                {**rep, "gates": [["not", [0]]] + rep["gates"][1:]}):
        try:
            lean(gap, bad); raise AssertionError(f"accepted {bad}")
        except SystemExit:
            pass
    print("demo ok")


if __name__ == "__main__":
    demo() if sys.argv[1:] == ["--demo"] else main(sys.argv)
