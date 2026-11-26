"""Write the Lean proof of a desk step `HasCircuitSize n f k` from a circuit that computes f.

Usage: python3 -I circuit2lean.py <lease-or-gap.json> <circuit> [--reverse-inputs] [--table HEX] [-o out.lean]

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

The proof (same shape as the merged L_meta_1001): the circuit as a `def`, `FanInTwo` by cases, the size by
`decide`, and the values on all 2^n rows by `decide +kernel`. The Lean checker is the judge: run
`tools/pnp.sh check <id>` (under capmem) on the written file.
ponytail: one `decide +kernel` over all 2^n rows; fine to n ~ 12, split by cofactors when a step needs more.
"""
import json, re, sys

MAX_BYTES = 512 * 1024


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


def lean(gap, c):
    m = re.fullmatch(r"PEqualNP\.MetaComplexity\.HasCircuitSize (\d+) (\(fun .*\)) (\d+)", gap["statement"].strip(), re.S)
    if not m:
        sys.exit("statement is not `PEqualNP.MetaComplexity.HasCircuitSize n (fun ...) k`")
    n, fun, k = int(m[1]), m[2], int(m[3])
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

theorem ev0 : ∀ {' '.join(bs)} : Bool,
    C0.eval [{', '.join(bs)}] = F (fun i => [{', '.join(bs)}].getD i.val false) := by
  decide +kernel

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
    out = rev = table = None
    rest = []
    while args:
        a = args.pop(0)
        if a == "-o": out = args.pop(0)
        elif a == "--reverse-inputs": rev = True
        elif a == "--table": table = args.pop(0)
        else: rest.append(a)
    if len(rest) != 2:
        sys.exit(__doc__)
    d = json.load(open(rest[0]))
    gap = d.get("gap", d)
    text = open(rest[1]).read()
    c = json.loads(text) if text.lstrip().startswith("{") else parse_bench(text)
    if rev:
        c = reverse_inputs(c)
    if table:
        check_table(c, table)
    body = lean(gap, c)
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
    print("demo ok")


if __name__ == "__main__":
    demo() if sys.argv[1:] == ["--demo"] else main(sys.argv)
