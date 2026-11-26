# Generator: "one NOT gate saves nothing" on an 8-vertex graph, with ANY small core checked by the in-kernel search.
# Engine: merged L_meta_11525 (itself from L_meta_10886 by k-sandhu, Apache-2.0), ported to 8 inputs by lane Normal4
# (onenot_tri8_gen.py); here the core is a parameter: k vertices, universe = k singles + all pairs, the search of the
# engine refutes every signed circuit with fewer than c gates on that universe.
# Argument: no NOT gate -> the list is its own AND/OR witness; with a NOT gate, each deleted vertex pays one
# two-input gate, the core needs c, plus the NOT gate: len(order) + c + 1 gates, which must be >= the witness length.
# usage: python3 -I onenot_core8_gen.py <template L_meta_11525.lean> <config.json> <out file>
# config: {"step": <lease json path>, "order": [deleted vertices, each with an edge left when deleted],
#          "core": [core vertices, in the order of the abstract core], "c": <signed size of the core>,
#          "gates": [["or",[0,1]],...], "out": <output wire>}
# Find a core with cores.py and liveg; check c with mirror-style search below (done here before writing).
import sys, re, json, itertools
sys.setrecursionlimit(100000)
N = 8
template, cfgpath, out = sys.argv[1:4]
cfg = json.load(open(cfgpath))
g = json.load(open(cfg["step"]))["gap"]
stmt, module = g["statement"], g["module"]
new_id = module.split(".")[-1]
flat = [int(v) for v in re.search(r"\[([0-9, ]+)\] : List ℕ", stmt).group(1).split(",")]
edges = list(zip(flat[0::2], flat[1::2]))
order, core, c = cfg["order"], cfg["core"], cfg["c"]
gates = [(op, ins) for op, ins in cfg["gates"]]; outw = cfg["out"]
K = len(core)
BOUND = len(order) + c + 1
adj = {v: set() for v in range(N)}
for a, b in edges: adj[a].add(b); adj[b].add(a)
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
assert all(op in ("and", "or") and len(ins) == 2 for op, ins in gates)
assert len(gates) <= BOUND, (len(gates), BOUND)

# the abstract core: rows = K singles, then the pairs in lexicographic order
pairs = list(itertools.combinations(range(K), 2))
R = K + len(pairs); ALLM = (1 << R) - 1; POW = 1 << R
isE = {p: (core[p[1]] in adj[core[p[0]]]) for p in pairs}
T = sum(1 << (K + i) for i, p in enumerate(pairs) if isE[p])
falses = [j for j in range(R) if not (T >> j) & 1]
ins = [(1 << j) | sum(1 << (K + i) for i, p in enumerate(pairs) if j in p) for j in range(K)]
assert len(set(ins)) == K

# mirror of the Lean search: it must fail for every s < c
def gM(k, a, b): return (a & b, a | b, a ^ (a & b), b ^ (a & b))[k]
def cov(ws):
    acc = 0
    for t in ws: acc |= t
    if acc & T != T: return False
    for p in falses:
        acc = 0
        for t in ws: acc |= (t ^ ALLM) if (t >> p) & 1 else t
        if acc & T != T: return False
    return True
calls = 0
def search(r, ws):
    global calls; calls += 1
    if r == 0: return ws == [T]
    if len(ws) > r + 1 or not cov(ws): return False
    d = sorted(set(ws))
    for a in d:
        for b in d:
            if a < b:
                for k in range(4):
                    gg = gM(k, a, b)
                    if gg == 0 or gg == a or gg == b: continue
                    rest = list(ws); rest.remove(a); rest.remove(b)
                    for u in range(r + 2 - len(ws)):
                        if search(r - 1, [gg] * (u + 1) + rest): return True
    return False
cost = {}                      # recursive calls of the search, by s, by (s, m0), by (s, m0, m1)
for s in range(c):
    for m in itertools.product(range(s + 2), repeat=K):
        if sum(m) > s + 1 and s > 0: continue
        c0 = calls
        assert not search(s, [x for i in range(K) for x in [ins[i]] * m[i]]), "the core has a signed circuit with %d gates: c is too large" % s
        d = calls - c0 - 1
        for key in ((s,), (s, m[0]), (s, m[0], m[1])): cost[key] = cost.get(key, 0) + d
print("core search: no signed circuit below", c, "gates;", calls, "search calls; rows", R, "target", T, "inputs", ins, "false rows", falses)
# One kernel call costs about 2.5 GB + 0.15 GB per thousand search calls (measured on L_meta_14920: 6.6 GB for the
# whole gem search in one theorem, checker limit about 6.5 GB). So the search is cut into theorems of at most LIM calls.
LIM = 9500

src = open(template, encoding="utf-8").read().split("\n")
old_id = "L_meta_11525"
L = lambda a, b: "\n".join(src[a - 1:b])      # 1-based inclusive line ranges of the template
def port(s):
    s = s.replace(old_id, new_id).replace("Fin 7", "Fin 8")
    return "\n".join(l for l in s.split("\n") if not l.startswith("--"))
def sub1(s, a, b):
    assert s.count(a) == 1, (a, s.count(a)); return s.replace(a, b)

generic = port(L(5, 233))                      # namespace .. end Generic
mid = port(L(234, 508))                        # BF .. run_search
for a, b in (("1008", "@@T@@"), ("1023", "@@ALL@@"), ("1024", "@@POW@@"), ("(n := 10)", "(n := %d)" % R), ("i < 10", "i < %d" % R)):
    assert a in mid; mid = mid.replace(a, b)
mid = mid.replace("@@T@@", str(T)).replace("@@ALL@@", str(ALLM)).replace("@@POW@@", str(POW))
mid = sub1(mid, "covB id ws && covB (sg 0) ws && covB (sg 1) ws && covB (sg 2) ws && covB (sg 3) ws",
           "covB id ws" + "".join(" && covB (sg %d) ws" % p for p in falses))
t1 = "k1"
for p in falses: t1 = "⟨%s, k2 %d (by decide)⟩" % (t1, p)
mid = sub1(mid, "exact ⟨⟨⟨⟨k1, k2 0 (by decide)⟩, k2 1 (by decide)⟩, k2 2 (by decide)⟩, k2 3 (by decide)⟩", "exact " + t1)
nf = len(falses)
t2 = "key _ h" + ".1" * nf
for i in range(1, nf + 1): t2 = "⟨%s, key _ h%s.2⟩" % (t2, ".1" * (nf - i))
mid = sub1(mid, "exact ⟨⟨⟨⟨key _ h.1.1.1.1, key _ h.1.1.1.2⟩, key _ h.1.1.2⟩, key _ h.1.2⟩, key _ h.2⟩", "exact " + t2)

ms = ["m%d" % i for i in range(K)]
alt = lambda v: " ∨ ".join("%s = %d" % (v, e) for e in ins)
C = []
c_ = C.append
c_("def mk (%s : ℕ) : List ℕ :=" % " ".join(ms))
c_("  " + " ++ ".join("List.replicate %s %d" % (ms[i], ins[i]) for i in range(K)))
c_("")
c_("theorem mk_perm (ws : List ℕ) (h : ∀ w ∈ ws, %s) :" % alt("w"))
c_("    ws.Perm (mk %s) := by" % " ".join("(ws.count %d)" % e for e in ins))
c_("  rw [List.perm_iff_count]")
c_("  intro a")
c_("  simp only [mk, List.count_append, List.count_replicate]")
for i in range(K):
    c_("  by_cases h%d : a = %d" % (i, ins[i]))
    c_("  · subst h%d; simp" % i)
c_("  have : a ∉ ws := fun hm => by rcases h a hm with %s <;> contradiction" % " | ".join(["h"] * K))
c_("  simp [List.count_eq_zero_of_not_mem this, %s]" % ", ".join("Ne.symm h%d" % i for i in range(K)))
c_("")
assert K >= 3
c_("def searchS2 (s m0 m1 : ℕ) : Bool :=")
c_("  " + " ".join("(List.range (s + 2)).any fun %s =>" % m for m in ms[2:]))
c_("    search s (mk %s)" % " ".join(ms))
c_("")
c_("def searchS1 (s m0 : ℕ) : Bool :=")
c_("  (List.range (s + 2)).any fun m1 => searchS2 s m0 m1")
c_("")
c_("def searchS (s : ℕ) : Bool :=")
c_("  (List.range (s + 2)).any fun m0 => searchS1 s m0")
c_("")
c_("theorem run_searchS {s : ℕ} {ws : List ℕ} (h : NR s ws)")
c_("    (hw : ∀ w ∈ ws, %s) : searchS s = true := by" % alt("w"))
c_("  have hp := mk_perm ws hw")
c_("  have hl := TR.len h")
c_("  rw [hp.length_eq] at hl")
c_("  simp only [mk, List.length_append, List.length_replicate, List.length_singleton] at hl")
c_("  have hs := search_perm s _ _ hp (run_search h)")
c_("  simp only [searchS, searchS1, searchS2, List.any_eq_true, List.mem_range]")
c_("  exact ⟨%s, hs⟩" % ", ".join("ws.count %d, by omega" % e for e in ins))
c_("")
def leaf(name, term):
    c_("set_option maxRecDepth 100000 in")
    c_("theorem %s : %s = false := by" % (name, term))
    c_("  decide +kernel")
    c_("")
def join(name, term, fn, var, n, parts):
    c_("theorem %s : %s = false := by" % (name, term))
    c_("  by_contra hne")
    c_("  have h : %s = true := by simpa using hne" % term)
    c_("  unfold %s at h" % fn)
    c_("  rw [List.any_eq_true] at h")
    c_("  obtain ⟨%s, hm, hv⟩ := h" % var)
    c_("  have hlt : %s < %d := by simpa using List.mem_range.1 hm" % (var, n))
    c_("  interval_cases %s <;> simp [%s] at hv" % (var, ", ".join(parts)))
    c_("")
pieces = 0
for s in range(c):
    if cost.get((s,), 0) <= LIM:
        leaf("f%d" % s, "searchS %d" % s); pieces += 1; continue
    for m0 in range(s + 2):
        if cost.get((s, m0), 0) <= LIM:
            leaf("g%d_%d" % (s, m0), "searchS1 %d %d" % (s, m0)); pieces += 1; continue
        for m1 in range(s + 2):
            assert cost.get((s, m0, m1), 0) <= LIM, "a piece of the core search is too large: %s" % cost.get((s, m0, m1))
            leaf("g%d_%d_%d" % (s, m0, m1), "searchS2 %d %d %d" % (s, m0, m1)); pieces += 1
        join("g%d_%d" % (s, m0), "searchS1 %d %d" % (s, m0), "searchS1", "m1", s + 2, ["g%d_%d_%d" % (s, m0, m1) for m1 in range(s + 2)])
    join("f%d" % s, "searchS %d" % s, "searchS", "m0", s + 2, ["g%d_%d" % (s, m0) for m0 in range(s + 2)])
print("kernel search cut into", pieces, "theorems; largest piece", max(v for k, v in cost.items() if len(k) == 3), "calls at the finest level")
c_("theorem searchS_false : ∀ s, s < %d → searchS s = false := by" % c)
c_("  intro s hs")
c_("  interval_cases s")
for s in range(c): c_("  · exact f%d" % s)
c_("")
hn = lambda p: "h%d%d" % p
c_("theorem Ucore (ι : Fin %d → Fin 8) (hι : Function.Injective ι) (F : BF)" % K)
c_("    (hs : ∀ j, F (singleInput (ι j)) = false)")
for p in pairs:
    c_("    (%s : F (pairInput (ι %d) (ι %d)) = %s)" % (hn(p), p[0], p[1], "true" if isE[p] else "false"))
C[-1] += " :"
c_("    ¬ UC gF (fun _ => True) %d (fun w => ∃ j, w = var (ι j)) F := by" % (c - 1))
c_("  intro hu")
c_("  let rows : List (Fin 8 → Bool) := [%s," % ", ".join("singleInput (ι %d)" % j for j in range(K)))
c_("    %s]" % ", ".join("pairInput (ι %d) (ι %d)" % p for p in pairs))
c_("  have hF : enc F rows = %d := by" % T)
c_("    simp only [rows, enc, hs, %s]" % ", ".join(hn(p) for p in pairs))
c_("    rfl")
c_("  have hv : ∀ j, %s := by" % " ∨ ".join("enc (var (ι j)) rows = %d" % e for e in ins))
c_("    intro j")
c_("    fin_cases j <;>")
c_("      simp [rows, enc, var, singleInput, pairInput, hι.eq_iff, Nat.bit]")
c_("  have hu2 : UC gN (fun _ => True) %d" % (c - 1))
c_("      (fun w => %s) (enc F rows) :=" % alt("w"))
c_("    UC_map (fun w => enc w rows) (fun k a b => enc_gF k a b rows) %d _ _ F" % (c - 1))
c_("      (by rintro w ⟨j, rfl⟩; exact hv j) hu")
c_("  rw [hF] at hu2")
c_("  obtain ⟨t', ht, ws, hws, hr⟩ := normalize gN 0 (fun _ => True) (fun t => t < %d) gN_lt" % POW)
c_("    gN_zero_left gN_zero_right gN_self %d _ %d" % (c - 1, T))
c_("    (by rintro w (%s) <;> norm_num) (by decide) hu2" % " | ".join(["rfl"] * K))
c_("  have h1 := run_searchS hr fun w hw => (hws w hw).1")
c_("  have h3 := searchS_false t' (by omega)")
c_("  rw [h1] at h3")
c_("  exact Bool.noConfusion h3")
coreblock = "\n" + "\n".join(C) + "\n"

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

Tb = [table(order[:k]) for k in range(len(order) + 1)]
G = lambda k: "(graphTable %d)" % Tb[k]
ce = next(p for p in pairs if isE[p])
coreEdge = (1 << core[ce[0]]) | (1 << core[ce[1]])
tests, removed = [], []
for p in order:
    q = next(v for v in sorted(adj[p]) if v not in removed)   # fails if p has no edge left: change the order
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
a("  let core : Fin %d → Fin 8 := ![%s]" % (K, ", ".join(map(str, core))))
a("  have injective : Function.Injective core := by decide +kernel")
a("  have single : ∀ i, %s (singleInput (core i)) = false := by decide +kernel" % G(n))
for p in pairs:
    a("  have p%d%d : %s (pairInput (core %d) (core %d)) = %s := by decide +kernel" % (p[0], p[1], G(n), p[0], p[1], "true" if isE[p] else "false"))
a("  have sources : ∀ w, sourceVars %s w → ∃ j, w = var (core j) := by" % er(n))
a("    rintro w ⟨i, hi, rfl⟩")
a("    have covered : ∀ i ∈ %s, ∃ j, core j = i := by decide +kernel" % er(n))
a("    obtain ⟨j, rfl⟩ := covered i hi")
a("    exact ⟨j, rfl⟩")
a("  have mapped := UC_monoS gF (fun _ => True) t%d _ _ _ sources h%d" % (n, n))
a("  have extra := countBinary_lt gates hnot")
a("  by_contra! small")
a("  exact Ucore core injective %s single %s (UC_le (by omega) mapped)" % (G(n), " ".join("p%d%d" % p for p in pairs)))
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

text = "import PEqualNP.Defs\n\n" + generic + "\n" + mid + "\n" + coreblock + "\n" + low + "\n\n" + "\n".join(A) + "\n"
assert '"' not in text and "sorry" not in text and "native_decide" not in text
assert "Fin 7" not in text and "Seven" not in text
open(out, "w", encoding="utf-8").write(text)
print("wrote", out, len(text.encode()), "bytes; bound", BOUND, "witness", len(gates), "tests", tests)
