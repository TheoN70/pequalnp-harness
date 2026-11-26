# Generator of a Lean proof for the desk rows "six-input monotone f ...: every fan-in-two AND/OR/NOT circuit has an
# AND/OR one no larger" (template block6-fanin2), by a layered live-set certificate.
# Engine: the merged lean/PEqualNP/Outside/L_meta_8645.lean (five inputs, 30 separating pairs), ported to six inputs
# and to the p pairs (true point, adjacent false point) of the function. Proves: no signed circuit (NOT free) with
# n = m - 2 two-input gates, so a circuit holding a NOT gate has at least m gates; m AND/OR gates suffice (witness).
# usage: python3 -I six_cert_gen.py <template L_meta_8645.lean> <step id, e.g. L_meta_12274> <table as written in the
#        statement, e.g. "4269866496 * 2 ^ 32 + 4269834240"> <m> <witness file: lines "w7 = OR(w5,w6)"> <out.lean> [chunk]
# Get m and the witness first: fleet-tools/live (exact sizes) and lst.c mode 0 (prints the witness lines).
import sys, re, itertools
tpl, sid, tstr, m, wit, out = sys.argv[1:7]; m = int(m); n = m - 2
CH = int(sys.argv[7]) if len(sys.argv) > 7 else 48
T = eval(tstr.replace("^", "**"), {"__builtins__": {}}); N = 6
ones = [a for a in range(64) if T >> a & 1]
P = [(t, t ^ (1 << i)) for t in ones for i in range(N) if not T >> (t ^ (1 << i)) & 1]
p = len(P); M = (1 << p) - 1; FULL = (1 << (2 * p)) - 1
def word(i):
    w = 0
    for j, (t, f) in enumerate(P):
        if f >> i & 1: w |= 1 << j
        if t >> i & 1: w |= 1 << (p + j)
    return w
ins = [word(i) for i in range(N)]
assert len(set(ins)) == N
goal = M << p; ngoal = goal ^ FULL
def cuts(ws):
    c = 0
    for w in ws: c |= ((w >> p) ^ w) & M
    return c == M
def children(k, ws):
    res = set(); L = len(ws)
    for i in range(L):
        for j in range(i + 1, L):
            a, b = ws[i], ws[j]; r = [w for q, w in enumerate(ws) if q != i and q != j]
            for z in (a & b, a | b, a & (FULL ^ b), b & (FULL ^ a)):
                for kept in (r, [a] + r, [b] + r, [a, b] + r):
                    if len(kept) <= k and cuts([z] + kept): res.add(tuple(sorted([z] + kept)))
    return res
levels = {n: set()}
for r in range(N + 1):
    for sub in itertools.combinations(ins, r):
        if len(sub) <= n + 1 and cuts(sub): levels[n].add(tuple(sorted(sub)))
for k in range(n - 1, -1, -1):
    levels[k] = set()
    for s in levels[k + 1]: levels[k] |= children(k, list(s))
for k in levels:
    assert (goal,) not in levels[k] and (ngoal,) not in levels[k], "a signed circuit with n gates exists: m is too large"
names = {}
def nm(w):
    if w not in names: names[w] = "v%d" % len(names)
    return names[w]
for w in ins: nm(w)
# witness
gates = []
for l in open(wit):
    g = re.match(r"w(\d+) = (AND|OR)\(w(\d+),w(\d+)\)", l.strip())
    if g: gates.append((g.group(2).lower(), int(g.group(3)), int(g.group(4))))
assert len(gates) == m
for a in range(64):
    w = [(a >> i) & 1 for i in range(N)]
    for op, x, y in gates: w.append((w[x] & w[y]) if op == "and" else (w[x] | w[y]))
    assert w[-1] == (T >> a & 1), "witness wrong"
# engine
src = open(tpl, encoding="utf-8").read().split("\n")
a0 = next(i for i, l in enumerate(src) if l.startswith("section Live"))
a1 = next(i for i, l in enumerate(src) if re.match(r"def v\d+ : W := ", l))
eng = "\n".join(l for l in src[a0:a1] if not l.startswith("--"))
eng = re.sub(r"\bFin 5\b", "Fin 6", eng).replace("ins.length = 5", "ins.length = 6")
eng = re.sub(r"\b60\b", "@@2P@@", eng); eng = re.sub(r"\b30\b", "@@P@@", eng)
eng = eng.replace("@@2P@@", str(2 * p)).replace("@@P@@", str(p))
ns = "PEqualNP.Outside." + sid
B = []
OPT = "set_option maxRecDepth 16000 in\nset_option maxHeartbeats 8000000 in\n"
def lit(states):   # balanced search tree as a literal
    if not states: return ".nil"
    h = len(states) // 2
    return "(.node [%s] %s %s)" % (",".join(nm(w) for w in states[h]), lit(states[:h]), lit(states[h + 1:]))
def emit(name, states, test):
    if len(states) <= CH:
        B.append("def %s : BinaryTree (List W) := %s" % (name, lit(states)))
        B.append(OPT + "theorem ok_%s : everyKey (%s) %s = true := by decide +kernel" % (name, test, name))
    else:
        h = len(states) // 2
        emit(name + "l", states[:h], test); emit(name + "r", states[h + 1:], test)
        B.append("def %s : BinaryTree (List W) := .node [%s] %sl %sr" % (name, ",".join(nm(w) for w in states[h]), name, name))
        B.append(OPT + "theorem ok_%s : everyKey (%s) %s = true := by\n  change (_ && everyKey _ %sl && everyKey _ %sr) = true\n  rw [ok_%sl, ok_%sr]\n  decide +kernel" % (name, test, name, name, name, name, name))
for k in range(n + 1):
    states = sorted(levels[k])
    test = "fun q => !doneTest q" if k == 0 else "rowOK %d tree_%d" % (k - 1, k - 1)
    emit("tree_%d" % k, states, test)
    if k == 0: B.append("theorem closed_0 : Closed 0 tree_0 := closed_nil tree_0 ok_tree_0")
    else: B.append("theorem closed_%d : Closed %d tree_%d := closed_next %d (by decide) tree_%d tree_%d closed_%d ok_tree_%d" % (k, k, k, k - 1, k, k - 1, k - 1, k))
fn = lambda v: "Nat.testBit (%s) (∑ i : Fin 6, if %s then 2^(i : ℕ) else 0)" % (tstr, v)
H = ["import PEqualNP.Defs", "",   # all of Mathlib is not needed and costs 4 GB of checker memory
      "namespace " + ns, "",
     "-- Layered live-set certificate; the engine is the one of the merged L-meta-8645 (itself after L-meta-1423,",
     "-- L-meta-703 and L-meta-1429), ported from five to six inputs and to the %d adjacent separating pairs." % p,
     "-- A NOT gate costs one gate in the given circuit and zero in the signed search.", eng]
H += ["def %s : W := 0x%x" % (v, w) for w, v in sorted(names.items(), key=lambda kv: int(kv[1][1:]))]
H += ["", "def ins6 : List W := [%s]" % ", ".join(nm(w) for w in ins),
      "theorem nd6 : ins6.Nodup := by decide +kernel",
      OPT + "theorem rows6 : ∀ j : Fin %d, %s = goal[j.val] := by decide +kernel" % (2 * p, fn("(ins6.getD i.val 0)[j.val]"))]
Z = ["theorem lower6 : ∀ z, z = goal ∨ z = ~~~goal → ¬ build basicOps z %d ins6.toFinset := @no_build %d tree_%d ins6 nd6 (by decide) closed_%d (by decide +kernel)" % (n, n, n, n),
     "def gates6 : List Gate := [%s]" % ", ".join("⟨.%s, [%d, %d]⟩" % g for g in gates),
     OPT + "theorem upper6 : ∃ (gs : List Gate) (o : ℕ), (∀ g ∈ gs, (g.op = .and ∨ g.op = .or) ∧ g.inputs.length ≤ 2) ∧ gs.length = %d ∧ ∀ x : Fin 6 → Bool, Circuit.eval ⟨gs,o⟩ (List.ofFn x) = %s := by" % (m, fn("x i")),
     "  exact ⟨gates6, %d, by simp [gates6], rfl, by decide +kernel⟩" % (N + m - 1), "", "end " + ns, "",
     "open %s in" % ns]
stmt = "∀ s : ℕ, PEqualNP.MetaComplexity.HasCircuitSize 6 (fun x : Fin 6 → Bool => Nat.testBit (%s) (∑ i : Fin 6, if x i then 2 ^ (i : ℕ) else 0)) s → ∃ C : PEqualNP.CircuitLowerBounds.Circuit, PEqualNP.MetaComplexity.Monotone2 C ∧ C.size ≤ s ∧ ∀ x : Fin 6 → Bool, C.eval (List.ofFn x) = Nat.testBit (%s) (∑ i : Fin 6, if x i then 2 ^ (i : ℕ) else 0)" % (tstr, tstr)
Z += ["theorem %s : (%s) := by" % (ns, stmt), "  intro s h", "  obtain ⟨C, basis, size, computes⟩ := h",
      "  obtain ⟨gates, output, mono, bound, correct⟩ :=",
      "    replace (%s) %d ins6 nd6 rows6 rfl" % (tstr, m),
      "      lower6 upper6 C.gates C.output basis computes",
      "  exact ⟨⟨gates, output⟩, mono, bound.trans size, correct⟩", ""]
text = "\n".join(H + B + Z)
open(out, "w", encoding="utf-8").write(text)
print("pairs", p, "states", {k: len(v) for k, v in levels.items()}, "words", len(names), "bytes", len(text.encode()))
