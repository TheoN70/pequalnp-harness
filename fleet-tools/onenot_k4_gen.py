# Generator for "one NOT gate saves nothing" proofs on 7-vertex graphs that contain a K4,
# from the merged template L_meta_11525 (engine of L_meta_10886): delete three vertices, each pays
# one binary gate, then the K4 core needs seven; with the NOT gate that is 11 gates.
import sys, re, itertools, json

def table(edges, removed=()):
    t = 0
    for m in range(128):
        x = [(m >> i) & 1 for i in range(7)]
        for r in removed: x[r] = 0
        if any(x[a] and x[b] for a, b in edges): t |= 1 << m
    return t

def ev(gates, out, x):
    w = list(x)
    for op, ins in gates:
        vals = [w[i] if i < len(w) else 0 for i in ins]
        w.append(int(all(vals)) if op == "and" else int(any(vals)))
    return w[out] if out < len(w) else 0

def gen(template, new_id, stmt, edges, order, core, gates, out):
    src = open(template, encoding="utf-8").read()
    old_id = re.search(r"namespace PEqualNP\.Outside\.(L_meta_\d+)", src).group(1)
    head = src[:src.index("theorem lower_with_not")]
    head = head.replace(old_id, new_id)
    # the header comments are dropped (the contributor script removes comments anyway)
    lines = head.split("\n")
    head = "\n".join(l for l in lines if not l.startswith("--"))
    n = 7
    adj = {v: set() for v in range(n)}
    for a, b in edges: adj[a].add(b); adj[b].add(a)
    assert len(core) == 4 and all(b in adj[a] for a in core for b in core if a != b), "core is not a K4"
    assert sorted(order + core) == list(range(7))
    coreEdge = (1 << core[0]) | (1 << core[1])
    T = [table(edges, order[:k]) for k in range(4)]
    tests = []
    removed = []
    for p in order:
        q = next(v for v in sorted(adj[p]) if v not in removed)  # an edge at p that is still present
        tests.append((1 << p) | (1 << q)); removed.append(p)
    # sanity of the witness
    for m in range(128):
        x = [(m >> i) & 1 for i in range(7)]
        assert ev(gates, out, x) == int(any(x[a] and x[b] for a, b in edges)), "witness wrong"
    assert all(op in ("and", "or") and len(ins) <= 2 for op, ins in gates)
    assert len(gates) <= 11
    def er(k):
        s = "(Finset.univ : Finset (Fin 7))"
        for p in order[:k]: s = "(%s.erase %d)" % (s, p)
        return s
    G = lambda k: "(graphTable %d)" % T[k]
    L = []
    A = L.append
    A("theorem lower_with_not (gates : List Gate) (o : ℕ) (legal : GOK gates)")
    A("    (hnot : ∃ g ∈ gates, g.op = GateOp.not)")
    A("    (comp : ∀ x : Fin 7 → Bool, Circuit.eval ⟨gates, o⟩ (List.ofFn x) = %s x) :" % G(0))
    A("    11 ≤ gates.length := by")
    A("  have hg : (wiresF gates (List.ofFn var)).getD o zF = %s := by" % G(0))
    A("    funext x")
    A("    rw [← comp x, ← getD_map_x, ← wires_eq]")
    A("    simp only [Circuit.eval, Circuit.wires, List.map_ofFn]")
    A("    rfl")
    A("  have start := trans_binary gates (List.ofFn var) (sourceVars Finset.univ) legal (by")
    A("    intro w hw")
    A("    obtain ⟨i, rfl⟩ := List.mem_ofFn.1 hw")
    A("    exact Or.inr ⟨i, Finset.mem_univ i, ori_zp rfl⟩) o")
    A("  rw [hg, ori_zp (by decide : %s (fun _ => false) = false)] at start" % G(0))
    A("  rcases start with e | base")
    A("  · have c := congrFun e (assignment %d)" % coreEdge)
    A("    exact False.elim ((by decide : %s (assignment %d) ≠ false) c)" % (G(0), coreEdge))
    prev = "base"; prevS = "(countBinary gates)"
    for k in range(3):
        p = order[k]
        xs = er(k) if k else "(Finset.univ : Finset (Fin 7))"
        A("  obtain ⟨t%d, pay%d, h%d⟩ := remove_var %s %d %s" % (k+1, k+1, k+1, G(k), p, xs))
        A("    %s ⟨assignment %d, by decide⟩ (by" % (prevS, tests[k]))
        A("      intro h")
        A("      have c := congrFun h (assignment %d)" % coreEdge)
        A("      exact (by decide : rst %d %s (assignment %d) ≠ false) c) %s" % (p, G(k), coreEdge, prev))
        A("  have eq%d : rst %d %s = %s := equalSeven (by decide)" % (k+1, p, G(k), G(k+1)))
        A("  rw [eq%d] at h%d" % (k+1, k+1))
        prev = "h%d" % (k+1); prevS = "(t%d)" % (k+1)
    A("  let core : Fin 4 → Fin 7 := ![%s]" % ", ".join(map(str, core)))
    A("  have injective : Function.Injective core := by decide +kernel")
    A("  have single : ∀ i, %s (singleInput (core i)) = false := by decide +kernel" % G(3))
    A("  have pair : ∀ i j, i ≠ j → %s (pairInput (core i) (core j)) = true := by decide +kernel" % G(3))
    A("  have sources : ∀ w, sourceVars %s w → ∃ j, w = var (core j) := by" % er(3))
    A("    rintro w ⟨i, hi, rfl⟩")
    A("    have covered : ∀ i ∈ %s, ∃ j, core j = i := by decide +kernel" % er(3))
    A("    obtain ⟨j, rfl⟩ := covered i hi")
    A("    exact ⟨j, rfl⟩")
    A("  have mapped := UC_monoS gF (fun _ => True) t3 _ _ _ sources h3")
    A("  have extra := countBinary_lt gates hnot")
    A("  by_contra! small")
    A("  exact U4 core injective %s single pair (UC_le (by omega) mapped)" % G(3))
    A("")
    A("def graph (x : Fin 7 → Bool) : Bool := " + " || ".join("(x %d && x %d)" % e for e in edges))
    A("")
    A("def witness : List Gate := [" + ", ".join("⟨.%s, [%s]⟩" % (op, ", ".join(map(str, ins))) for op, ins in gates) + "]")
    A("")
    A("theorem witnessBasis : ∀ g ∈ witness,")
    A("    (g.op = GateOp.and ∨ g.op = GateOp.or) ∧ g.inputs.length ≤ 2 := by")
    A("  intro g hg")
    A("  simp only [witness, List.mem_cons, List.not_mem_nil, or_false] at hg")
    A("  rcases hg with " + " | ".join(["rfl"] * len(gates)) + " <;> simp")
    A("")
    A("set_option maxRecDepth 12000 in")
    A("set_option maxHeartbeats 0 in")
    A("theorem witnessCorrect : ∀ x : Fin 7 → Bool,")
    A("    Circuit.eval ⟨witness, %d⟩ (List.ofFn x) = graph x := by" % out)
    A("  decide +kernel")
    A("")
    flat = ", ".join(str(v) for e in edges for v in e)
    spec = ("decide (∃ i < ([%s] : List ℕ).length / 2, (List.ofFn x).getD (([%s] : List ℕ).getD (2 * i) 0) false = true ∧ "
            "(List.ofFn x).getD (([%s] : List ℕ).getD (2 * i + 1) 0) false = true)") % (flat, flat, flat)
    assert spec in stmt, "the statement does not hold the expected edge-list form"
    A("set_option maxRecDepth 12000 in")
    A("set_option maxHeartbeats 0 in")
    A("theorem graph_correct : ∀ x : Fin 7 → Bool, graph x = %s := by" % spec)
    A("  decide +kernel")
    A("")
    A("end PEqualNP.Outside.%s" % new_id)
    A("")
    A("open PEqualNP.Outside.%s PEqualNP.CircuitLowerBounds PEqualNP.MetaComplexity in" % new_id)
    A("theorem PEqualNP.Outside.%s : (%s) := by" % (new_id, stmt))
    A("  intro gates o legal _oneNot computes")
    A("  by_cases hnot : ∃ g ∈ gates, g.op = GateOp.not")
    A("  · have comp : ∀ x : Fin 7 → Bool, Circuit.eval ⟨gates, o⟩ (List.ofFn x) = graph x :=")
    A("      fun x => (computes x).trans (graph_correct x).symm")
    A("    have eq : graph = %s := equalSeven (by decide)" % G(0))
    A("    have large := lower_with_not gates o legal hnot (fun x => (comp x).trans (congrFun eq x))")
    A("    have hw : witness.length = %d := rfl" % len(gates))
    A("    exact ⟨witness, %d, witnessBasis, by omega, fun x => (witnessCorrect x).trans (graph_correct x)⟩" % out)
    A("  · refine ⟨gates, o, ?_, le_rfl, computes⟩")
    A("    intro g hg")
    A("    obtain ⟨ops, hlen⟩ := legal g hg")
    A("    refine ⟨?_, hlen⟩")
    A("    rcases ops with h | h | h")
    A("    · exact Or.inl h")
    A("    · exact Or.inr h")
    A("    · exact False.elim (hnot ⟨g, hg, h⟩)")
    return head.lstrip("\n") if False else head + "\n".join(L) + "\n", T, tests, coreEdge

if __name__ == "__main__":
    cfg = json.load(open(sys.argv[1]))
    text, T, tests, ce = gen(cfg["template"], cfg["new_id"], cfg["stmt"], [tuple(e) for e in cfg["edges"]],
                             cfg["order"], cfg["core"], [(op, ins) for op, ins in cfg["gates"]], cfg["out"])
    open(cfg["outfile"], "w", encoding="utf-8").write(text)
    print("tables", T, "tests", tests, "coreEdge", ce, "bytes", len(text.encode()))
