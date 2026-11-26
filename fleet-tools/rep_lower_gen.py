"""Lean proof of a one-a-side promise lower bound `¬ RepSizeAtMost (fun (u : Fin n) (v : Fin m) => (M : ℕ).testBit
(m * u.val + v.val)) k` from the merged L_meta_9291 (5x5, tb-16's argument), with the mask, its one-points OO and
zero-points ZZ, the shape and the bound replaced.

Usage: python3 -I rep_lower_gen.py <lease.json> [-o out.lean] [--drop-zero p,..]   statement and module from the lease (a positive statement: its negation)
       python3 -I rep_lower_gen.py --is-false <lease.json> [-o out.lean]   exit 0 only if shown false (counting, read-once DP, or the Lean proof compiles), 1 = keep
       python3 -I rep_lower_gen.py --raw <n> <m> <M> <k> <ident> [-o out.lean] [--drop-zero p,..]
         e.g. --raw 4 5 104317 9 L_meta_21063;  --raw 5 5 31523873 9 L_meta_21267 --drop-zero 4

Shapes: 5x5 (the template as is) and n x 5 for n = 3, 4 (Research-L-meta-21063's 4x5 substitutions generalised to n
rows by Research-L-meta-20500, work/L-meta-20500/lean/gen3.py; checked: 21062, 21063 (4x5) and 20500 (3x5) compile,
~107-109 KB, ~17 s, 4.4 GB). Other shapes (4x6, ...) are refused: the template's 5s mean both rows and columns
(the point index 5u+v, Fin 5 on both sides), so a column count other than 5 needs its substitutions checked by hand.
k: the first argument of `lower`. R = the inputs that serve (row u: a 1 where another row has a 0; columns
likewise); the others may stay unread: `lower k c R DL` checks chkM (k + 1 - |D|) for every read set D ⊇ R
(Research-L-meta-21062, work/one-a-side-4x5/gen2.py: 20970, 21033 with DL = [503, 511]). Refused when k > |R| + 1 or
k > n + m (deeper searches untested), when no input serves, or
when OO or ZZ has more than 16 points (the bit-matrix layout). More than 16 zero-points: --drop-zero leaves some
out of ZZ (any subset of the zeros is sound, ZZ_ok checks each listed one; whether the in-kernel search still
succeeds is Lean's call: Research-L-meta-21267 dropped point 4 of 31523873, 17 zeros, and it compiled). Lean is the judge: compile it (`lake env lean`, ~5 GB,
capmem -m 6G), then `tools/pnp.sh check`.
Template: pequalnp-proofs/lean/PEqualNP/Outside/L_meta_9291.lean (next to harness/, read at run time).
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.realpath(__file__))
TEMPLATE = os.path.join(HERE, "../../pequalnp-proofs/lean/PEqualNP/Outside/L_meta_9291.lean")
STMT = re.compile(r"(?:¬\s*\(?\s*)?PEqualNP\.Represents\.RepSizeAtMost \(fun (?:\(u : Fin (\d+)\) \(v : Fin (\d+)\)|u v : Fin (\d+)) => "
                  r"\((\d+) : ℕ\)\.testBit \((\d+) \* u\.val \+ v\.val\)\) (\d+)\s*\)?")


def check_mask(n, m, M, drop=()):
    A = [[M >> (m * u + v) & 1 for v in range(m)] for u in range(n)]
    # R: the inputs that serve (row u: a 1 where another row has a 0; column v likewise); the others may be unread
    R = [u for u in range(n) if any(A[u][v] and not A[w][v] for v in range(m) for w in range(n))]
    R += [n + v for v in range(m) if any(A[u][v] and not A[u][x] for u in range(n) for x in range(m))]
    if not R:
        sys.exit("no input serves (empty or complete graph): the argument does not apply")
    OO = [p for p in range(n * m) if M >> p & 1]
    if any(p >= n * m or M >> p & 1 for p in drop):
        sys.exit(f"--drop-zero {list(drop)}: each must be a zero-point of the mask")
    ZZ = [p for p in range(n * m) if not M >> p & 1 and p not in drop]
    if len(OO) > 16 or len(ZZ) > 16:
        sys.exit(f"{len(OO)} one-points, {len(ZZ)} zero-points kept: the template holds at most 16 of each"
                 + (" (leave zeros out with --drop-zero p,..)" if len(ZZ) > 16 else ""))
    return OO, ZZ, R


def to_nx5(t, mask, n):
    """to_4x5 of rep_lower_gen.py with 4 -> n rows (Research-L-meta-20500, n = 3). Wires 10 -> n+5, points 25 -> 5n."""
    N = n + 5
    def sub(a, b, c_=None):
        nonlocal t
        c = t.count(a)
        assert c > 0 and (c_ is None or c == c_), (a, c)
        t = t.replace(a, b)
    if "def X" in t:
        sub("oneEach (⟨p / 5 % 5, by omega⟩ : Fin 5) (⟨p % 5, by omega⟩ : Fin 5)",
            f"oneEach (⟨p / 5 % {n}, by omega⟩ : Fin {n}) (⟨p % 5, by omega⟩ : Fin 5)", 1)
        X = [31 << 5 * u for u in range(n)] + [sum(1 << 5 * u + v for u in range(n)) for v in range(5)]
        sub("[31, 992, 31744, 1015808, 32505856, 1082401, 2164802, 4329604, 8659208, 17318416]",
            "[" + ", ".join(map(str, X)) + "]", 1)
        sub("def MM : ℕ := 3247934", "def MM : ℕ := %d" % mask, 1)
        sub("def ro (v : Fin 5) : List Bool := List.replicate 5 false ++",
            f"def ro (v : Fin 5) : List Bool := List.replicate {n} false ++", 1)
        sub("def lo (u : Fin 5) : List Bool := List.ofFn (fun j : Fin 5 => decide (j = u))",
            f"def lo (u : Fin {n}) : List Bool := List.ofFn (fun j : Fin {n} => decide (j = u))", 1)
        sub("theorem lo_len : ∀ v : Fin 5,", f"theorem lo_len : ∀ v : Fin {n},", 1)
        sub("i ≠ 5 + (v : ℕ)", f"i ≠ {n} + (v : ℕ)", 1)
        sub("(hv : 5 + (v : ℕ) ∉ D)", f"(hv : {n} + (v : ℕ) ∉ D)", 1)
        sub("C.eval x = C.eval y) (u : Fin 5)", f"C.eval x = C.eval y) (u : Fin {n})", 1)
    else:
        sub("(hrow : ∀ u : Fin 5, (u : ℕ) ∈ R → ∃ (u' : Fin 5) (v : Fin 5),",
            f"(hrow : ∀ u : Fin {n}, (u : ℕ) ∈ R → ∃ (u' : Fin {n}) (v : Fin 5),", 1)
        sub("(hcol : ∀ v : Fin 5, 5 + (v : ℕ) ∈ R → ∃ (v' : Fin 5) (u : Fin 5),",
            f"(hcol : ∀ v : Fin 5, {n} + (v : ℕ) ∈ R → ∃ (v' : Fin 5) (u : Fin {n}),", 1)
        sub("by_cases h4 : i < 5", f"by_cases h4 : i < {n}", 1)
        sub("have e : 5 + (i - 5) = i", f"have e : {n} + (i - {n}) = i", 1)
        sub("⟨i - 5, by omega⟩", f"⟨i - {n}, by omega⟩")
        sub("hrep ⟨p / 5 % 5, by omega⟩ ⟨p % 5, by omega⟩", f"hrep ⟨p / 5 % {n}, by omega⟩ ⟨p % 5, by omega⟩", 1)
        sub("5 * (p / 5 % 5) + p % 5 = p", f"5 * (p / 5 % {n}) + p % 5 = p", 1)
        sub("Fin 10", f"Fin {N}", 1)
        sub("{0, 1, 2, 3, 4, 5, 6, 7, 8, 9}", "{" + ", ".join(map(str, range(N))) + "}", 1)
        sub("(3247934 : ℕ)", "(%d : ℕ)" % mask, 1)
        sub("fun u v : Fin 5 =>", f"fun (u : Fin {n}) (v : Fin 5) =>", 1)
    t = t.replace("Fin 5 → Fin 5 → Bool", f"Fin {n} → Fin 5 → Bool")
    t = t.replace("(u : Fin 5) (v : Fin 5)", f"(u : Fin {n}) (v : Fin 5)")
    t = re.sub(r"\b25\b", str(5 * n), t)
    t = re.sub(r"\b10\b", str(N), t)
    t = re.sub(r"\b1024\b", str(2 ** N), t)
    t = re.sub(r"\b1023\b", str(2 ** N - 1), t)
    return t.replace("c1023", f"c{2 ** N - 1}")


def generate(n, m, M, k, ident, stmt=None, drop=()):
    if not (m == 5 and 3 <= n <= 5):
        sys.exit(f"shape {n}x{m} not supported (only 3x5, 4x5 and 5x5, whose substitutions were checked)")
    N, D = n + m, 2 ** (n + m) - 1
    if not 1 <= k <= N:
        sys.exit(f"k = {k}: supported 1 <= k <= n + m = {N} (deeper in-kernel searches are untested)")
    OO, ZZ, R = check_mask(n, m, M, drop)
    if k + 1 > len(R) + 2:
        sys.exit(f"k = {k} > |R| + 1 = {len(R) + 1} ({len(R)} inputs serve): beyond the recipe")
    src = open(TEMPLATE).read()
    head, tail = src.split("def OO : List ℕ :=", 1)
    rest = tail.split("\n", 2)[2]  # drop the template's OO rest and ZZ line
    if (n, m) == (5, 5):
        fix = lambda t: t.replace("def MM : ℕ := 3247934", f"def MM : ℕ := {M}").replace("(3247934 : ℕ)", f"({M} : ℕ)")
    else:
        fix = lambda t: to_nx5(t, M, n)
    out = fix(head) + f"def OO : List ℕ := {OO}\ndef ZZ : List ℕ := {ZZ}\n" + fix(rest)
    if n < 5:
        out = out.replace("""-- This file is the proof of L-meta-9195 by tb-16 (same repository) with the mask, the list OO of its
-- one-points and the list ZZ of its zero-points replaced; the argument is unchanged.""",
                          """-- This file is the merged proof of L-meta-9291 (itself L-meta-9195 by tb-16, same repository) moved
-- from 5 x 5 to %d x 5: %d input wires and %d points instead of 10 and 25, with the mask, the list OO
-- of its one-points and the list ZZ of its zero-points replaced; the argument is unchanged.""" % (n, n + 5, 5 * n))
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
    # Rebuild the tail for R (all inputs: the template's own tail): `lower k c R DL` with DL = every read set D ⊇ R,
    # one kernel check chkM (k + 1 - |D|) per D (Research-L-meta-21062, work/one-a-side-4x5/gen2.py).
    ns = f"PEqualNP.Outside.{ident}"
    final = re.search(r"theorem %s : (.*) := by\n" % re.escape(ns), out)[1]
    cut = out.index(f"theorem c{D} : chkM {depth} lf {N} {D} = true := by decide +kernel\n")
    c = sum(1 << i for i in R)
    DL = [x for x in range(D + 1) if x & c == c]
    chks = "".join(f"theorem c{x} : chkM {max(0, k + 1 - bin(x).count('1'))} lf {N} {x} = true := by decide +kernel\n"
                   for x in DL)
    tail = (f"\nend {ns}\n\ntheorem {ns} : {final} := by\n"
            f"  refine {ns}.lower {k} {c} {{{', '.join(map(str, R))}}} [{', '.join(map(str, DL))}] (by decide +kernel) (by decide +kernel) (by decide)\n"
            f"    (by decide) (by decide +kernel) (fun i hi => ?_) (by decide) (by decide +kernel) (by decide +kernel) ?_\n"
            f"  · exact Nat.testBit_lt_two_pow (lt_of_lt_of_le (by norm_num : {c} < 2 ^ {N})\n"
            f"      (Nat.pow_le_pow_right (by norm_num) hi))\n"
            f"  · intro D hD\n"
            f"    simp only [List.mem_cons, List.not_mem_nil, or_false] at hD\n"
            f"    rcases hD with {' | '.join(['rfl'] * len(DL))}\n" + "".join(f"    · exact {ns}.c{x}\n" for x in DL))
    return out[:cut] + chks + tail


def serving(n, m, M):
    A = lambda u, v: M >> (m * u + v) & 1
    return ([u for u in range(n) if any(A(u, v) and not A(w, v) for v in range(m) for w in range(n))] +
            [n + v for v in range(m) if any(A(u, v) and not A(u, x) for u in range(n) for x in range(m))])


def readonce(n, m, M, R):
    """A read-once AND/OR tree on exactly the leaves R that equals the graph on the n*m promise points, or None
    (Research-L-meta-21062, work/one-a-side-4x5/readonce.py: DP over leaf subsets, vectors on the points)."""
    pts = [(u, v) for u in range(n) for v in range(m)]
    vec = lambda i: sum(1 << p for p, (u, v) in enumerate(pts) if (i < n and u == i) or (i >= n and v == i - n))
    target = M & ((1 << (n * m)) - 1)
    memo = {}

    def F(S):
        if S not in memo:
            if len(S) == 1:
                memo[S] = {vec(S[0]): f"w{S[0]}"}
            else:
                out, first, rest = {}, S[0], S[1:]
                for k in range(1 << len(rest)):  # S1 holds `first`: each split once
                    S1 = (first,) + tuple(x for j, x in enumerate(rest) if k >> j & 1)
                    S2 = tuple(x for j, x in enumerate(rest) if not k >> j & 1)
                    if S2:
                        for a, fa in F(S1).items():
                            for b, fb in F(S2).items():
                                out.setdefault(a & b, f"({fa} & {fb})"); out.setdefault(a | b, f"({fa} | {fb})")
                memo[S] = out
        return memo[S]
    return F(tuple(R)).get(target)


def lean_ok(text):
    """Compile `text` in the shared clone (one core from `slots`, capmem 6G, 10 min): True only on a clean build."""
    import subprocess, tempfile
    lean_dir = os.path.join(HERE, "../../pequalnp-proofs/lean")
    core = subprocess.run([os.path.join(HERE, "slots"), "1"], capture_output=True, text=True)
    if core.returncode:
        print(f"no free core to compile ({core.stderr.strip()}): keep it", file=sys.stderr)
        return False
    with tempfile.TemporaryDirectory() as t:
        f = os.path.join(t, "Check.lean")
        open(f, "w").write(text)
        try:
            r = subprocess.run(["taskset", "-c", core.stdout.strip(), os.path.join(HERE, "capmem"), "-m", "6G", "lake", "env",
                                "lean", f], cwd=lean_dir, capture_output=True, text=True, timeout=600)
        except subprocess.TimeoutExpired:
            return False
    return r.returncode == 0 and "error" not in r.stdout and "sorry" not in r.stdout


def shown_false(n, m, M, k, R, text):
    """(False-for-sure, why). k <= |R|-2: every serving input is read, a tree on |R| leaves needs |R|-1 gates.
    k = |R|-1: R-1 gates reading R inputs = a read-once tree on R: false iff none fits. k = |R|: only the recipe's
    in-kernel checks decide: false iff the generated Lean compiles. Anything else, or any doubt: not false."""
    if k <= len(R) - 2:
        return True, f"k = {k} <= |R| - 2 = {len(R) - 2}: reading the {len(R)} serving inputs takes >= {len(R) - 1} gates"
    if k == len(R) - 1:
        f = readonce(n, m, M, R)
        return (False, f"a read-once tree fits: {f}") if f else (True, f"k = |R| - 1 = {k} and no read-once tree on R fits")
    if k == len(R) and text and lean_ok(text):
        return True, f"k = |R| = {k}: the generated Lean proof compiles"
    return False, f"k = {k}, |R| = {len(R)}: not shown false (the Lean check failed or was not possible)"


def main(a):
    out, drop = None, ()
    is_false = "--is-false" in a
    if is_false:
        a.remove("--is-false")
    if "-o" in a:
        i = a.index("-o"); out = a[i + 1]; del a[i:i + 2]
    if "--drop-zero" in a:
        i = a.index("--drop-zero"); drop = tuple(map(int, a[i + 1].split(","))); del a[i:i + 2]
    if a[:1] == ["--raw"] and len(a) == 6:
        n, m, M, k = map(int, a[1:5]); text = generate(n, m, M, k, a[5], drop=drop)
    elif len(a) == 1:
        d = json.load(open(a[0])); g = d.get("gap", d)
        st = g["statement"].strip()
        if not st.startswith("¬"):  # the positive unit itself (refuted): prove its negation
            print("positive statement: writing the proof of its negation", file=sys.stderr)
            st = "¬ " + st
        mt = STMT.fullmatch(st)
        n_, m_ = (int(mt[1]), int(mt[2])) if mt and mt[1] else (int(mt[3]), int(mt[3])) if mt else (0, 0)
        if is_false:  # grab.sh --skip-false-siblings: exit 0 = shown false (shown_false), 1 = keep it
            if not mt or int(mt[5]) != m_ or not (m_ == 5 and 3 <= n_ <= 5):
                sys.exit(1)
            M_, k_ = int(mt[4]), int(mt[6])
            R = serving(n_, m_, M_)
            if not R or k_ > len(R):
                sys.exit(1)
            try:
                text = generate(n_, m_, M_, k_, g["module"].rsplit(".", 1)[1], st, drop)
            except (SystemExit, AssertionError) as e:
                text = None
                print(f"no proof generated: {e}", file=sys.stderr)
            ok, why = shown_false(n_, m_, M_, k_, R, text)
            print(("false: " if ok else "keep: ") + why, file=sys.stderr)
            if ok and out and text:
                open(out, "w").write(text)
            sys.exit(0 if ok else 1)
        if not mt or int(mt[5]) != m_:
            sys.exit("statement is not `¬ PEqualNP.Represents.RepSizeAtMost (fun (u : Fin n) (v : Fin m) => "
                     "(M : ℕ).testBit (m * u.val + v.val)) k`")
        ident = g["module"].rsplit(".", 1)[1]
        if not g["module"].startswith("PEqualNP.Outside."):
            sys.exit(f"module {g['module']}: the template lives in PEqualNP.Outside")
        text = generate(n_, m_, int(mt[4]), int(mt[6]), ident, st, drop)
    else:
        sys.exit(__doc__)
    if out:
        open(out, "w").write(text)
        print(f"{out}: {len(text.encode()):,} bytes", file=sys.stderr)
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main(sys.argv[1:])
