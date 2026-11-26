# Generator for L_meta_14144: "one NOT gate saves nothing" on an 8-vertex graph with a triangle core.
# Engine: merged L_meta_11525 (itself from L_meta_10886 by k-sandhu, Apache-2.0), ported from 7 to 8 inputs,
# its K4 core (7 gates, 10-point universe) replaced by a triangle core (4 gates, 6-point universe).
# usage: python3 -I gen14144.py <template L_meta_11525.lean> <step json> <out file>
import sys, re, json

N = 8
template, stepjson, out = sys.argv[1:4]
g = json.load(open(stepjson))["gap"]
stmt, module = g["statement"], g["module"]
new_id = module.split(".")[-1]
flat = [int(v) for v in re.search(r"\[([0-9, ]+)\] : List ℕ", stmt).group(1).split(",")]
edges = list(zip(flat[0::2], flat[1::2]))
order = [3, 6, 5, 1, 2]          # deleted vertices, each pays one binary gate
core = [0, 4, 7]                 # the triangle
gates = [("or", [0, 1]), ("or", [0, 7]), ("or", [8, 2]), ("or", [8, 3]), ("and", [4, 9]),
         ("and", [11, 6]), ("or", [13, 12]), ("or", [7, 5]), ("and", [10, 15]), ("or", [16, 14])]
outw = 17
BOUND = len(order) + 4 + 1       # 5 deletions + triangle 4 + the NOT gate

adj = {v: set() for v in range(N)}
for a, b in edges: adj[a].add(b); adj[b].add(a)
assert all(b in adj[a] for a in core for b in core if a != b), "core is not a triangle"
assert sorted(order + core) == list(range(N))

def f(x): return int(any(x[a] and x[b] for a, b in edges))
def table(removed=()):
    t = 0
    for m in range(1 << N):
        x = [(m >> i) & 1 for i in range(N)]
        for r in removed: x[r] = 0
        if f(x): t |= 1 << m
    return t
def ev(x):
    w = list(x)
    for op, ins in gates:
        vals = [w[i] if i < len(w) else 0 for i in ins]
        w.append(int(all(vals)) if op == "and" else int(any(vals)))
    return w[outw]
for m in range(1 << N):
    x = [(m >> i) & 1 for i in range(N)]
    assert ev(x) == f(x), "witness wrong"
assert len(gates) == BOUND, (len(gates), BOUND)

src = open(template, encoding="utf-8").read().split("\n")
old_id = "L_meta_11525"
L = lambda a, b: "\n".join(src[a - 1:b])      # 1-based inclusive line ranges of the template
def port(s):
    s = s.replace(old_id, new_id).replace("Fin 7", "Fin 8")
    return "\n".join(l for l in s.split("\n") if not l.startswith("--"))

generic = port(L(5, 233))                      # namespace .. end Generic
mid = port(L(234, 508))                        # BF .. run_search
for a, b in (("1008", "56"), ("1023", "63"), ("1024", "64"), ("(n := 10)", "(n := 6)"), ("i < 10", "i < 6")):
    assert a in mid; mid = mid.replace(a, b)
def sub1(s, a, b):
    assert s.count(a) == 1, (a, s.count(a)); return s.replace(a, b)
mid = sub1(mid, "covB id ws && covB (sg 0) ws && covB (sg 1) ws && covB (sg 2) ws && covB (sg 3) ws",
           "covB id ws && covB (sg 0) ws && covB (sg 1) ws && covB (sg 2) ws")
mid = sub1(mid, "exact ⟨⟨⟨⟨k1, k2 0 (by decide)⟩, k2 1 (by decide)⟩, k2 2 (by decide)⟩, k2 3 (by decide)⟩",
           "exact ⟨⟨⟨k1, k2 0 (by decide)⟩, k2 1 (by decide)⟩, k2 2 (by decide)⟩")
mid = sub1(mid, "exact ⟨⟨⟨⟨key _ h.1.1.1.1, key _ h.1.1.1.2⟩, key _ h.1.1.2⟩, key _ h.1.2⟩, key _ h.2⟩",
           "exact ⟨⟨⟨key _ h.1.1.1, key _ h.1.1.2⟩, key _ h.1.2⟩, key _ h.2⟩")

tri = """
def mk (m0 m1 m2 : ℕ) : List ℕ :=
  List.replicate m0 25 ++ List.replicate m1 42 ++ List.replicate m2 52

theorem mk_perm (ws : List ℕ) (h : ∀ w ∈ ws, w = 25 ∨ w = 42 ∨ w = 52) :
    ws.Perm (mk (ws.count 25) (ws.count 42) (ws.count 52)) := by
  rw [List.perm_iff_count]
  intro a
  simp only [mk, List.count_append, List.count_replicate]
  by_cases h0 : a = 25
  · subst h0; simp
  by_cases h1 : a = 42
  · subst h1; simp
  by_cases h2 : a = 52
  · subst h2; simp
  have : a ∉ ws := fun hm => by rcases h a hm with h | h | h <;> contradiction
  simp [List.count_eq_zero_of_not_mem this, Ne.symm h0, Ne.symm h1, Ne.symm h2]

def searchS (s : ℕ) : Bool :=
  (List.range (s + 2)).any fun m0 => (List.range (s + 2)).any fun m1 =>
    (List.range (s + 2)).any fun m2 => search s (mk m0 m1 m2)

theorem run_searchS {s : ℕ} {ws : List ℕ} (h : NR s ws)
    (hw : ∀ w ∈ ws, w = 25 ∨ w = 42 ∨ w = 52) : searchS s = true := by
  have hp := mk_perm ws hw
  have hl := TR.len h
  rw [hp.length_eq] at hl
  simp only [mk, List.length_append, List.length_replicate, List.length_singleton] at hl
  have hs := search_perm s _ _ hp (run_search h)
  simp only [searchS, List.any_eq_true, List.mem_range]
  exact ⟨ws.count 25, by omega, ws.count 42, by omega, ws.count 52, by omega, hs⟩

set_option maxRecDepth 100000 in
theorem searchS_false : (List.range 4).all (fun s => !searchS s) = true := by
  decide +kernel

theorem U3 (ι : Fin 3 → Fin 8) (hι : Function.Injective ι) (F : BF)
    (hs : ∀ j, F (singleInput (ι j)) = false)
    (hp : ∀ j j', j ≠ j' → F (pairInput (ι j) (ι j')) = true) :
    ¬ UC gF (fun _ => True) 3 (fun w => ∃ j, w = var (ι j)) F := by
  intro hu
  let rows : List (Fin 8 → Bool) := [singleInput (ι 0), singleInput (ι 1), singleInput (ι 2),
    pairInput (ι 0) (ι 1), pairInput (ι 0) (ι 2), pairInput (ι 1) (ι 2)]
  have hF : enc F rows = 56 := by
    simp only [rows, enc, hs, hp 0 1 (by decide), hp 0 2 (by decide), hp 1 2 (by decide)]
    rfl
  have hv : ∀ j, enc (var (ι j)) rows = 25 ∨ enc (var (ι j)) rows = 42 ∨
      enc (var (ι j)) rows = 52 := by
    intro j
    fin_cases j <;>
      simp [rows, enc, var, singleInput, pairInput, hι.eq_iff, Nat.bit]
  have hu2 : UC gN (fun _ => True) 3
      (fun w => w = 25 ∨ w = 42 ∨ w = 52) (enc F rows) :=
    UC_map (fun w => enc w rows) (fun k a b => enc_gF k a b rows) 3 _ _ F
      (by rintro w ⟨j, rfl⟩; exact hv j) hu
  rw [hF] at hu2
  obtain ⟨t', ht, ws, hws, hr⟩ := normalize gN 0 (fun _ => True) (fun t => t < 64) gN_lt
    gN_zero_left gN_zero_right gN_self 3 _ 56
    (by rintro w (rfl | rfl | rfl) <;> norm_num) (by decide) hu2
  have h1 := run_searchS hr fun w hw => (hws w hw).1
  have h2 := searchS_false
  rw [List.all_eq_true] at h2
  have h3 := h2 t' (List.mem_range.2 (by omega))
  rw [h1] at h3
  exact Bool.noConfusion h3
"""

low = port(L(689, 1114))                       # zF .. remove_var
vec = ", ".join("x %d" % i for i in range(N))
names = "a b c d e v w z"
bvec = ", ".join(names.split())
low = sub1(low, "theorem inputVector (x : Fin 8 → Bool) : x = ![x 0, x 1, x 2, x 3, x 4, x 5, x 6] := by",
           "theorem inputVector (x : Fin 8 → Bool) : x = ![%s] := by" % vec)
low = sub1(low, "theorem equalSeven {f g : (Fin 8 → Bool) → Bool}", "theorem equalEight {f g : (Fin 8 → Bool) → Bool}")
low = sub1(low, "(h : ∀ a b c d e v w : Bool, f ![a, b, c, d, e, v, w] = g ![a, b, c, d, e, v, w]) : f = g := by",
           "(h : ∀ %s : Bool, f ![%s] = g ![%s]) : f = g := by" % (names, bvec, bvec))
low = sub1(low, "exact h (x 0) (x 1) (x 2) (x 3) (x 4) (x 5) (x 6)",
           "exact h " + " ".join("(x %d)" % i for i in range(N)))

T = [table(order[:k]) for k in range(len(order) + 1)]
G = lambda k: "(graphTable %d)" % T[k]
coreEdge = (1 << core[0]) | (1 << core[1])
tests, removed = [], []
for p in order:
    q = next(v for v in sorted(adj[p]) if v not in removed)
    tests.append((1 << p) | (1 << q)); removed.append(p)
def er(k):
    s = "(Finset.univ : Finset (Fin 8))"
    for p in order[:k]: s = "(%s.erase %d)" % (s, p)
    return s

A = []
a = A.append
a("theorem lower_with_not (gates : List Gate) (o : ℕ) (legal : GOK gates)")
a("    (hnot : ∃ g ∈ gates, g.op = GateOp.not)")
a("    (comp : ∀ x : Fin 8 → Bool, Circuit.eval ⟨gates, o⟩ (List.ofFn x) = %s x) :" % G(0))
a("    %d ≤ gates.length := by" % BOUND)
a("  have hg : (wiresF gates (List.ofFn var)).getD o zF = %s := by" % G(0))
a("    funext x")
a("    rw [← comp x, ← getD_map_x, ← wires_eq]")
a("    simp only [Circuit.eval, Circuit.wires, List.map_ofFn]")
a("    rfl")
a("  have start := trans_binary gates (List.ofFn var) (sourceVars Finset.univ) legal (by")
a("    intro w hw")
a("    obtain ⟨i, rfl⟩ := List.mem_ofFn.1 hw")
a("    exact Or.inr ⟨i, Finset.mem_univ i, ori_zp rfl⟩) o")
a("  rw [hg, ori_zp (by decide +kernel : %s (fun _ => false) = false)] at start" % G(0))
a("  rcases start with e | base")
a("  · have c := congrFun e (assignment %d)" % coreEdge)
a("    exact False.elim ((by decide +kernel : %s (assignment %d) ≠ false) c)" % (G(0), coreEdge))
prev = "base"
for k, p in enumerate(order, 1):
    s_in = "(countBinary gates)" if k == 1 else "(t%d)" % (k - 1)
    a("  obtain ⟨t%d, pay%d, h%d⟩ := remove_var %s %d %s" % (k, k, k, G(k - 1), p, er(k - 1)))
    a("    %s ⟨assignment %d, by decide +kernel⟩ (by" % (s_in, tests[k - 1]))
    a("      intro h")
    a("      have c := congrFun h (assignment %d)" % coreEdge)
    a("      exact (by decide +kernel : rst %d %s (assignment %d) ≠ false) c) %s" % (p, G(k - 1), coreEdge, prev))
    a("  have eq%d : rst %d %s = %s := equalEight (by decide +kernel)" % (k, p, G(k - 1), G(k)))
    a("  rw [eq%d] at h%d" % (k, k))
    prev = "h%d" % k
n = len(order)
a("  let core : Fin 3 → Fin 8 := ![%s]" % ", ".join(map(str, core)))
a("  have injective : Function.Injective core := by decide +kernel")
a("  have single : ∀ i, %s (singleInput (core i)) = false := by decide +kernel" % G(n))
a("  have pair : ∀ i j, i ≠ j → %s (pairInput (core i) (core j)) = true := by decide +kernel" % G(n))
a("  have sources : ∀ w, sourceVars %s w → ∃ j, w = var (core j) := by" % er(n))
a("    rintro w ⟨i, hi, rfl⟩")
a("    have covered : ∀ i ∈ %s, ∃ j, core j = i := by decide +kernel" % er(n))
a("    obtain ⟨j, rfl⟩ := covered i hi")
a("    exact ⟨j, rfl⟩")
a("  have mapped := UC_monoS gF (fun _ => True) t%d _ _ _ sources h%d" % (n, n))
a("  have extra := countBinary_lt gates hnot")
a("  by_contra! small")
a("  exact U3 core injective %s single pair (UC_le (by omega) mapped)" % G(n))
a("")
a("def graph (x : Fin 8 → Bool) : Bool := " + " || ".join("(x %d && x %d)" % e for e in edges))
a("")
a("def witness : List Gate := [" + ", ".join("⟨.%s, [%d, %d]⟩" % (op, i[0], i[1]) for op, i in gates) + "]")
a("")
a("theorem witnessBasis : ∀ g ∈ witness,")
a("    (g.op = GateOp.and ∨ g.op = GateOp.or) ∧ g.inputs.length ≤ 2 := by")
a("  intro g hg")
a("  simp only [witness, List.mem_cons, List.not_mem_nil, or_false] at hg")
a("  rcases hg with " + " | ".join(["rfl"] * len(gates)) + " <;> simp")
a("")
target = re.search(r"decide \(∃ i < .*?= true\)", stmt).group(0)
assert stmt.count(target) == 2
a("set_option maxRecDepth 100000 in")
a("set_option maxHeartbeats 0 in")
a("theorem witnessCorrect : ∀ x : Fin 8 → Bool,")
a("    Circuit.eval ⟨witness, %d⟩ (List.ofFn x) = graph x := by" % outw)
a("  decide +kernel")
a("")
a("set_option maxRecDepth 100000 in")
a("set_option maxHeartbeats 0 in")
a("theorem graph_correct : ∀ x : Fin 8 → Bool, graph x = %s := by" % target)
a("  decide +kernel")
a("")
a("end PEqualNP.Outside.%s" % new_id)
a("")
a("open PEqualNP.Outside.%s PEqualNP.CircuitLowerBounds PEqualNP.MetaComplexity in" % new_id)
a("theorem PEqualNP.Outside.%s : (%s) := by" % (new_id, stmt))
a("  intro gates o legal _oneNot computes")
a("  by_cases hnot : ∃ g ∈ gates, g.op = GateOp.not")
a("  · have comp : ∀ x : Fin 8 → Bool, Circuit.eval ⟨gates, o⟩ (List.ofFn x) = graph x :=")
a("      fun x => (computes x).trans (graph_correct x).symm")
a("    have eq : graph = %s := equalEight (by decide +kernel)" % G(0))
a("    have large := lower_with_not gates o legal hnot (fun x => (comp x).trans (congrFun eq x))")
a("    have hw : witness.length = %d := rfl" % len(gates))
a("    exact ⟨witness, %d, witnessBasis, by omega, fun x => (witnessCorrect x).trans (graph_correct x)⟩" % outw)
a("  · refine ⟨gates, o, ?_, le_rfl, computes⟩")
a("    intro g hg")
a("    obtain ⟨ops, hlen⟩ := legal g hg")
a("    refine ⟨?_, hlen⟩")
a("    rcases ops with h | h | h")
a("    · exact Or.inl h")
a("    · exact Or.inr h")
a("    · exact False.elim (hnot ⟨g, hg, h⟩)")

# ponytail: no `import Mathlib` (PEqualNP.Defs brings enough; 3.6 GB peak instead of 7.5 GB, L-meta-14144)
text = "import PEqualNP.Defs\n\n" + generic + "\n" + mid + "\n" + tri + "\n" + low + "\n\n" + "\n".join(A) + "\n"
assert '"' not in text and "sorry" not in text and "native_decide" not in text
assert "Fin 7" not in text and "Seven" not in text
open(out, "w", encoding="utf-8").write(text)
print("wrote", out, len(text), "bytes;", "tables:", [hex(t)[:12] for t in T], "tests", tests)
