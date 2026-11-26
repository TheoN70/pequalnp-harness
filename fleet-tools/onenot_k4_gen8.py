# Generator for "one NOT gate saves nothing" proofs on 7-vertex graphs that contain a K4,
# from the merged template L_meta_11525 (engine of L_meta_10886): delete three vertices, each pays
# one binary gate, then the K4 core needs seven; with the NOT gate that is 11 gates.
import sys, re, itertools, json

def table(edges, removed=()):
    t = 0
    for m in range(256):
        x = [(m >> i) & 1 for i in range(8)]
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
    head = head.replace("Fin 7", "Fin 8")
    o1 = "x = ![x 0, x 1, x 2, x 3, x 4, x 5, x 6] := by"
    o2 = "theorem equalSeven {f g : (Fin 8 → Bool) → Bool}\n    (h : ∀ a b c d e v w : Bool, f ![a, b, c, d, e, v, w] = g ![a, b, c, d, e, v, w]) : f = g := by\n  funext x\n  rw [inputVector x]\n  exact h (x 0) (x 1) (x 2) (x 3) (x 4) (x 5) (x 6)"
    assert head.count(o1) == 1 and head.count(o2) == 1
    head = head.replace(o1, "x = ![x 0, x 1, x 2, x 3, x 4, x 5, x 6, x 7] := by")
    head = head.replace(o2, "theorem equalEight {f g : (Fin 8 → Bool) → Bool}\n    (h : ∀ a b c d e v w u : Bool, f ![a, b, c, d, e, v, w, u] = g ![a, b, c, d, e, v, w, u]) : f = g := by\n  funext x\n  rw [inputVector x]\n  exact h (x 0) (x 1) (x 2) (x 3) (x 4) (x 5) (x 6) (x 7)")
    assert "Seven" not in head and "Fin 7" not in head
    # the header comments are dropped (the contributor script removes comments anyway)
    lines = head.split("\n")
    head = "\n".join(l for l in lines if not l.startswith("--"))
    n = 8
    B = 8 + len(order)
    adj = {v: set() for v in range(n)}
    for a, b in edges: adj[a].add(b); adj[b].add(a)
    assert len(core) == 4 and all(b in adj[a] for a in core for b in core if a != b), "core is not a K4"
    assert sorted(order + core) == list(range(8))
    coreEdge = (1 << core[0]) | (1 << core[1])
    T = [table(edges, order[:k]) for k in range(len(order) + 1)]
    tests = []
    removed = []
    for p in order:
        q = next(v for v in sorted(adj[p]) if v not in removed)  # an edge at p that is still present
        tests.append((1 << p) | (1 << q)); removed.append(p)
    # sanity of the witness
    for m in range(256):
        x = [(m >> i) & 1 for i in range(8)]
        assert ev(gates, out, x) == int(any(x[a] and x[b] for a, b in edges)), "witness wrong"
    assert all(op in ("and", "or") and len(ins) <= 2 for op, ins in gates)
    assert len(gates) <= B
    def er(k):
        s = "(Finset.univ : Finset (Fin 8))"
        for p in order[:k]: s = "(%s.erase %d)" % (s, p)
        return s
    G = lambda k: "(graphTable %d)" % T[k]
    L = []
    A = L.append
    A("theorem lower_with_not (gates : List Gate) (o : ℕ) (legal : GOK gates)")
    A("    (hnot : ∃ g ∈ gates, g.op = GateOp.not)")
    A("    (comp : ∀ x : Fin 8 → Bool, Circuit.eval ⟨gates, o⟩ (List.ofFn x) = %s x) :" % G(0))
    A("    %d ≤ gates.length := by" % B)
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
    for k in range(len(order)):
        p = order[k]
        xs = er(k) if k else "(Finset.univ : Finset (Fin 8))"
        A("  obtain ⟨t%d, pay%d, h%d⟩ := remove_var %s %d %s" % (k+1, k+1, k+1, G(k), p, xs))
        A("    %s ⟨assignment %d, by decide⟩ (by" % (prevS, tests[k]))
        A("      intro h")
        A("      have c := congrFun h (assignment %d)" % coreEdge)
        A("      exact (by decide : rst %d %s (assignment %d) ≠ false) c) %s" % (p, G(k), coreEdge, prev))
        A("  have eq%d : rst %d %s = %s := equalEight (by decide)" % (k+1, p, G(k), G(k+1)))
        A("  rw [eq%d] at h%d" % (k+1, k+1))
        prev = "h%d" % (k+1); prevS = "(t%d)" % (k+1)
    A("  let core : Fin 4 → Fin 8 := ![%s]" % ", ".join(map(str, core)))
    A("  have injective : Function.Injective core := by decide +kernel")
    A("  have single : ∀ i, %s (singleInput (core i)) = false := by decide +kernel" % G(len(order)))
    A("  have pair : ∀ i j, i ≠ j → %s (pairInput (core i) (core j)) = true := by decide +kernel" % G(len(order)))
    A("  have sources : ∀ w, sourceVars %s w → ∃ j, w = var (core j) := by" % er(len(order)))
    A("    rintro w ⟨i, hi, rfl⟩")
    A("    have covered : ∀ i ∈ %s, ∃ j, core j = i := by decide +kernel" % er(len(order)))
    A("    obtain ⟨j, rfl⟩ := covered i hi")
    A("    exact ⟨j, rfl⟩")
    A("  have mapped := UC_monoS gF (fun _ => True) t%d _ _ _ sources h%d" % (len(order), len(order)))
    A("  have extra := countBinary_lt gates hnot")
    A("  by_contra! small")
    A("  exact U4 core injective %s single pair (UC_le (by omega) mapped)" % G(len(order)))
    A("")
    A("def graph (x : Fin 8 → Bool) : Bool := " + " || ".join("(x %d && x %d)" % e for e in edges))
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
    A("theorem witnessCorrect : ∀ x : Fin 8 → Bool,")
    A("    Circuit.eval ⟨witness, %d⟩ (List.ofFn x) = graph x := by" % out)
    A("  decide +kernel")
    A("")
    flat = ", ".join(str(v) for e in edges for v in e)
    spec = ("decide (∃ i < ([%s] : List ℕ).length / 2, (List.ofFn x).getD (([%s] : List ℕ).getD (2 * i) 0) false = true ∧ "
            "(List.ofFn x).getD (([%s] : List ℕ).getD (2 * i + 1) 0) false = true)") % (flat, flat, flat)
    assert spec in stmt, "the statement does not hold the expected edge-list form"
    A("set_option maxRecDepth 12000 in")
    A("set_option maxHeartbeats 0 in")
    A("theorem graph_correct : ∀ x : Fin 8 → Bool, graph x = %s := by" % spec)
    A("  decide +kernel")
    A("")
    A("end PEqualNP.Outside.%s" % new_id)
    A("")
    A("open PEqualNP.Outside.%s PEqualNP.CircuitLowerBounds PEqualNP.MetaComplexity in" % new_id)
    A("theorem PEqualNP.Outside.%s : (%s) := by" % (new_id, stmt))
    A("  intro gates o legal _oneNot computes")
    A("  by_cases hnot : ∃ g ∈ gates, g.op = GateOp.not")
    A("  · have comp : ∀ x : Fin 8 → Bool, Circuit.eval ⟨gates, o⟩ (List.ofFn x) = graph x :=")
    A("      fun x => (computes x).trans (graph_correct x).symm")
    A("    have eq : graph = %s := equalEight (by decide)" % G(0))
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
