"""Lean proof of a one-a-side promise lower bound `¬ RepSizeAtMost (fun (u : Fin n) (v : Fin m) => (M : ℕ).testBit
(m * u.val + v.val)) k` from the merged L_meta_9291 (5x5, tb-16's argument), with the mask, its one-points OO and
zero-points ZZ, the shape and the bound replaced.

Usage: python3 -I rep_lower_gen.py <lease.json> [-o out.lean] [--drop-zero p,..]   statement and module from the lease
       python3 -I rep_lower_gen.py --raw <n> <m> <M> <k> <ident> [-o out.lean] [--drop-zero p,..]
         e.g. --raw 4 5 104317 9 L_meta_21063;  --raw 5 5 31523873 9 L_meta_21267 --drop-zero 4

Shapes: 5x5 (the template as is) and 4x5 (Research-L-meta-21063's substitutions, work/L-meta-21063/lean/gen.py,
checked: 21062 and 21063 compile, 109 KB, 17 s, 4.4 GB). Other shapes are refused: the template's 5s and 10s mean
several things (rows, columns, wires) and each shape needs its substitutions checked by hand.
k: the first argument of `lower`; the in-kernel search depth is k + 1 - (n + m) (0 below n + m - 1). Refused when
k > n + m (deeper searches are untested) or when some row or column does not serve (the argument needs every input:
each row has a 1 in a column where another row has a 0, each column a 1 in a row where another column has a 0), or
when OO or ZZ has more than 16 points (the bit-matrix layout). More than 16 zero-points: --drop-zero leaves some
out of ZZ (any subset of the zeros is sound, ZZ_ok checks each listed one; whether the in-kernel search still
succeeds is Lean's call: Research-L-meta-21267 dropped point 4 of 31523873, 17 zeros, and it compiled). Lean is the judge: compile it (`lake env lean`, ~5 GB,
capmem -m 6G), then `tools/pnp.sh check`.
Template: pequalnp-proofs/lean/PEqualNP/Outside/L_meta_9291.lean (next to harness/, read at run time).
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.realpath(__file__))
TEMPLATE = os.path.join(HERE, "../../pequalnp-proofs/lean/PEqualNP/Outside/L_meta_9291.lean")
STMT = re.compile(r"¬\s*\(?\s*PEqualNP\.Represents\.RepSizeAtMost \(fun \(u : Fin (\d+)\) \(v : Fin (\d+)\) => "
                  r"\((\d+) : ℕ\)\.testBit \((\d+) \* u\.val \+ v\.val\)\) (\d+)\s*\)?")


def check_mask(n, m, M, drop=()):
    A = [[M >> (m * u + v) & 1 for v in range(m)] for u in range(n)]
    for u in range(n):
        if not any(A[u][v] and not A[w][v] for v in range(m) for w in range(n)):
            sys.exit(f"row u{u} does not serve (no 1 where another row has a 0): the argument needs every input")
    for v in range(m):
        if not any(A[u][v] and not A[u][x] for u in range(n) for x in range(m)):
            sys.exit(f"column v{v} does not serve (no 1 where another column has a 0): the argument needs every input")
    OO = [p for p in range(n * m) if M >> p & 1]
    if any(p >= n * m or M >> p & 1 for p in drop):
        sys.exit(f"--drop-zero {list(drop)}: each must be a zero-point of the mask")
    ZZ = [p for p in range(n * m) if not M >> p & 1 and p not in drop]
    if len(OO) > 16 or len(ZZ) > 16:
        sys.exit(f"{len(OO)} one-points, {len(ZZ)} zero-points kept: the template holds at most 16 of each"
                 + (" (leave zeros out with --drop-zero p,..)" if len(ZZ) > 16 else ""))
    return OO, ZZ


def to_4x5(t, mask):
    """Research's 5x5 -> 4x5 substitutions (work/L-meta-21063/lean/gen.py), each counted. 10 (wires) -> 9, 25 -> 20."""
    def sub(a, b, n=None):
        nonlocal t
        c = t.count(a)
        assert c > 0 and (n is None or c == n), (a, c)
        t = t.replace(a, b)
    if "def X" in t:
        sub("oneEach (⟨p / 5 % 5, by omega⟩ : Fin 5) (⟨p % 5, by omega⟩ : Fin 5)",
            "oneEach (⟨p / 5 % 4, by omega⟩ : Fin 4) (⟨p % 5, by omega⟩ : Fin 5)", 1)
        sub("[31, 992, 31744, 1015808, 32505856, 1082401, 2164802, 4329604, 8659208, 17318416]",
            "[31, 992, 31744, 1015808, 33825, 67650, 135300, 270600, 541200]", 1)
        sub("def MM : ℕ := 3247934", "def MM : ℕ := %d" % mask, 1)
        sub("def ro (v : Fin 5) : List Bool := List.replicate 5 false ++",
            "def ro (v : Fin 5) : List Bool := List.replicate 4 false ++", 1)
        sub("def lo (u : Fin 5) : List Bool := List.ofFn (fun j : Fin 5 => decide (j = u))",
            "def lo (u : Fin 4) : List Bool := List.ofFn (fun j : Fin 4 => decide (j = u))", 1)
        sub("theorem lo_len : ∀ v : Fin 5,", "theorem lo_len : ∀ v : Fin 4,", 1)
        sub("i ≠ 5 + (v : ℕ)", "i ≠ 4 + (v : ℕ)", 1)
        sub("(hv : 5 + (v : ℕ) ∉ D)", "(hv : 4 + (v : ℕ) ∉ D)", 1)
        sub("C.eval x = C.eval y) (u : Fin 5)", "C.eval x = C.eval y) (u : Fin 4)", 1)
    else:
        sub("(hrow : ∀ u : Fin 5, (u : ℕ) ∈ R → ∃ (u' : Fin 5) (v : Fin 5),",
            "(hrow : ∀ u : Fin 4, (u : ℕ) ∈ R → ∃ (u' : Fin 4) (v : Fin 5),", 1)
        sub("(hcol : ∀ v : Fin 5, 5 + (v : ℕ) ∈ R → ∃ (v' : Fin 5) (u : Fin 5),",
            "(hcol : ∀ v : Fin 5, 4 + (v : ℕ) ∈ R → ∃ (v' : Fin 5) (u : Fin 4),", 1)
        sub("by_cases h4 : i < 5", "by_cases h4 : i < 4", 1)
        sub("have e : 5 + (i - 5) = i", "have e : 4 + (i - 4) = i", 1)
        sub("⟨i - 5, by omega⟩", "⟨i - 4, by omega⟩")
        sub("hrep ⟨p / 5 % 5, by omega⟩ ⟨p % 5, by omega⟩", "hrep ⟨p / 5 % 4, by omega⟩ ⟨p % 5, by omega⟩", 1)
        sub("5 * (p / 5 % 5) + p % 5 = p", "5 * (p / 5 % 4) + p % 5 = p", 1)
        sub("Fin 10", "Fin 9", 1)
        sub("{0, 1, 2, 3, 4, 5, 6, 7, 8, 9}", "{0, 1, 2, 3, 4, 5, 6, 7, 8}", 1)
        sub("(3247934 : ℕ)", "(%d : ℕ)" % mask, 1)
        sub("fun u v : Fin 5 =>", "fun (u : Fin 4) (v : Fin 5) =>", 1)
    t = t.replace("Fin 5 → Fin 5 → Bool", "Fin 4 → Fin 5 → Bool")
    t = t.replace("(u : Fin 5) (v : Fin 5)", "(u : Fin 4) (v : Fin 5)")
    t = re.sub(r"\b25\b", "20", t)
    t = re.sub(r"\b10\b", "9", t)
    t = re.sub(r"\b1024\b", "512", t)
    t = re.sub(r"\b1023\b", "511", t)
    return t.replace("c1023", "c511")


def generate(n, m, M, k, ident, stmt=None, drop=()):
    if (n, m) not in ((5, 5), (4, 5)):
        sys.exit(f"shape {n}x{m} not supported (only 5x5 and 4x5, whose substitutions were checked)")
    N, D = n + m, 2 ** (n + m) - 1
    if not 1 <= k <= N:
        sys.exit(f"k = {k}: supported 1 <= k <= n + m = {N} (deeper in-kernel searches are untested)")
    OO, ZZ = check_mask(n, m, M, drop)
    src = open(TEMPLATE).read()
    head, tail = src.split("def OO : List ℕ :=", 1)
    rest = tail.split("\n", 2)[2]  # drop the template's OO rest and ZZ line
    if (n, m) == (5, 5):
        fix = lambda t: t.replace("def MM : ℕ := 3247934", f"def MM : ℕ := {M}").replace("(3247934 : ℕ)", f"({M} : ℕ)")
    else:
        fix = lambda t: to_4x5(t, M)
    out = fix(head) + f"def OO : List ℕ := {OO}\ndef ZZ : List ℕ := {ZZ}\n" + fix(rest)
    if (n, m) == (4, 5):
        out = out.replace("""-- This file is the proof of L-meta-9195 by tb-16 (same repository) with the mask, the list OO of its
-- one-points and the list ZZ of its zero-points replaced; the argument is unchanged.""",
                          """-- This file is the merged proof of L-meta-9291 (itself L-meta-9195 by tb-16, same repository) moved
-- from 5 x 5 to 4 x 5: 9 input wires and 20 points instead of 10 and 25, with the mask, the list OO
-- of its one-points and the list ZZ of its zero-points replaced; the argument is unchanged.""")
    depth = max(0, k + 1 - N)
    for a, b in ((f".lower {N} {D} {{", f".lower {k} {D} {{"), (f"chkM 1 lf {N} {D} = true", f"chkM {depth} lf {N} {D} = true")):
        assert out.count(a) == 1, (a, out.count(a))
        out = out.replace(a, b)
    out = out.replace("L_meta_9291", ident)
    a = f"v.val)) {N} := by\n  refine PEqualNP.Outside.{ident}.lower"  # the bound in the final statement
    assert out.count(a) == 1, a
    out = out.replace(a, a.replace(f")) {N} := by", f")) {k} := by"))
    if stmt:  # the lease's statement, verbatim, as the final theorem's type
        last = re.search(r"theorem PEqualNP\.Outside\.%s : (.*) := by\n" % re.escape(ident), out)
        assert last, "final theorem not found"
        out = out[:last.start(1)] + stmt + out[last.end(1):]
    return out


def main(a):
    out, drop = None, ()
    if "-o" in a:
        i = a.index("-o"); out = a[i + 1]; del a[i:i + 2]
    if "--drop-zero" in a:
        i = a.index("--drop-zero"); drop = tuple(map(int, a[i + 1].split(","))); del a[i:i + 2]
    if a[:1] == ["--raw"] and len(a) == 6:
        n, m, M, k = map(int, a[1:5]); text = generate(n, m, M, k, a[5], drop=drop)
    elif len(a) == 1:
        d = json.load(open(a[0])); g = d.get("gap", d)
        st = g["statement"].strip()
        mt = STMT.fullmatch(st)
        if not mt or int(mt[4]) != int(mt[2]):
            sys.exit("statement is not `¬ PEqualNP.Represents.RepSizeAtMost (fun (u : Fin n) (v : Fin m) => "
                     "(M : ℕ).testBit (m * u.val + v.val)) k`")
        ident = g["module"].rsplit(".", 1)[1]
        if not g["module"].startswith("PEqualNP.Outside."):
            sys.exit(f"module {g['module']}: the template lives in PEqualNP.Outside")
        text = generate(int(mt[1]), int(mt[2]), int(mt[3]), int(mt[5]), ident, st, drop)
    else:
        sys.exit(__doc__)
    if out:
        open(out, "w").write(text)
        print(f"{out}: {len(text.encode()):,} bytes", file=sys.stderr)
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main(sys.argv[1:])
