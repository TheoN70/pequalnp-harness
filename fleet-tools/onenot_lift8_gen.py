# "One NOT gate saves nothing" on an 8-vertex graph G, from a MERGED 7-vertex proof of G - v (ForestCore engine,
# e.g. L_meta_11763): the merged file is kept whole up to its `wholeBound`, then one `lower_slice` step deletes v
# (pays one binary gate), so the bound is (merged bound) + 1 binary gates, + 1 for the NOT gate.
# Works when AND/OR minimum(G) = AND/OR minimum(G - v) + 1 and G - v is isomorphic to the merged file's graph.
# usage: python3 -I onenot_lift8_gen.py <merged L_meta_N.lean> <lease json> <out file> <v> <witness gates json> <out wire>
#   witness gates json: [["and",[1,4]],["or",[8,5]],...] (liveg prints one; wires 0..7 are the inputs)
import sys, re, json, itertools

template, stepjson, out, vdel, gates_json, outw = sys.argv[1:7]
vdel, outw = int(vdel), int(outw)
gates = [(op, list(ins)) for op, ins in json.loads(gates_json)]
g = json.load(open(stepjson))["gap"]
stmt, module = g["statement"], g["module"]
new_id = module.split(".")[-1]
flat = [int(x) for x in re.search(r"\[([0-9, ]+)\] : List ℕ", stmt).group(1).split(",")]
edges = list(zip(flat[0::2], flat[1::2]))
N = 8
assert "Fin 8 → Bool" in stmt

src = open(template, encoding="utf-8").read()
old_id = re.search(r"namespace PEqualNP\.Outside\.(L_meta_\d+)", src).group(1)
# the merged file's own graph, coding and bound
i_final = src.rindex("\ntheorem PEqualNP.Outside." + old_id)
oflat = [int(x) for x in re.search(r"\[([0-9, ]+)\] : List ℕ", src[i_final:]).group(1).split(",")]
oedges = list(zip(oflat[0::2], oflat[1::2]))
coding = [int(x) for x in re.search(r"def coding : Fin 7 → Nat := !\[([0-9, ]+)\]", src).group(1).split(",")]
ocg = int(re.search(r"def codedGraph : Sig := (0x[0-9a-f]+)", src).group(1), 16)
obound = int(re.search(r"theorem wholeBound : Lower true roots codedGraph (\d+)", src).group(1))
owit = int(re.search(r"have hw : witness\.length = (\d+) := rfl", src).group(1))
assert owit == obound + 1

def coded(edges, code):
    t = 0
    for r in range(512):
        if any((r >> code[a]) & 1 and (r >> code[b]) & 1 for a, b in edges): t |= 1 << r
    return t
assert coded(oedges, coding) == ocg, "row convention differs from the merged file"

# isomorphism G - v  ->  merged graph
rest = [u for u in range(N) if u != vdel]
sub = [(a, b) for a, b in edges if vdel not in (a, b)]
oset = {frozenset(e) for e in oedges}
iso = None
for p in itertools.permutations(range(7)):
    m = dict(zip(rest, p))
    if len(sub) == len(oset) and all(frozenset((m[a], m[b])) in oset for a, b in sub): iso = m; break
assert iso is not None, "G - v is not isomorphic to the merged file's graph"
free = [s for s in range(9) if s not in coding]
coding8 = [free[0] if u == vdel else coding[iso[u]] for u in range(N)]
slot = coding8[vdel]
cg8 = coded(edges, coding8)
assert all(((cg8 >> (r & ~(1 << slot))) & 1) == ((ocg >> r) & 1) for r in range(512))
nb = next(b if a == vdel else a for a, b in edges if vdel in (a, b))
r0 = 1 << coding8[nb]; r1 = r0 | (1 << slot)
assert (cg8 >> r0) & 1 == 0 and (cg8 >> r1) & 1 == 1
assert cg8 & 1 == 0

def f(x): return int(any(x[a] and x[b] for a, b in edges))
for mm in range(1 << N):
    x = [(mm >> i) & 1 for i in range(N)]
    w = list(x)
    for op, ins in gates:
        vals = [w[i] if i < len(w) else 0 for i in ins]
        w.append(int(all(vals)) if op == "and" else int(any(vals)))
    assert w[outw] == f(x), "witness wrong"
bound = obound + 1
assert len(gates) == bound + 1, (len(gates), bound + 1)
assert all(op in ("and", "or") and len(ins) == 2 for op, ins in gates)

i_graph = src.index("\ndef graph (x : Fin 7 → Bool)")
i_coding = src.index("\ndef coding : Fin 7 → Nat")
i_sample = src.index("\ndef sampleInput")
head = src[:i_graph] + src[i_coding:i_sample]          # everything up to wholeBound, without the Fin 7 graph
head = head.replace(old_id, new_id)
head = "\n".join(l for l in head.split("\n") if not l.lstrip().startswith("--"))
# ponytail: drop `import Mathlib` (about 4 GB at the verifier); put it back if the build misses a Mathlib name
head = "\n".join(l for l in head.split("\n") if l.strip() != "import Mathlib")
assert head.startswith("import ")

I = lambda s: "inputs.getD %d zero" % s
A = []
a = A.append
a("")
a("def coding8 : Fin 8 → Nat := ![%s]" % ", ".join(map(str, coding8)))
a("")
a("def roots8 : List Sig := List.ofFn (fun i : Fin 8 => inputs.getD (coding8 i) zero)")
a("")
a("def codedGraph8 : Sig := 0x%0128x" % cg8)
a("")
a("def pins8 : Finset Sig := {%s}" % I(slot))
a("")
a("def pinRow8 (r : Row) : Row := Fin.ofNat 512 (r.val &&& %d)" % (511 ^ (1 << slot)))
a("")
a("set_option maxRecDepth 12000 in")
a("set_option maxHeartbeats 0 in")
a("theorem wholeBound8 : Lower true roots8 codedGraph8 %d := by" % bound)
a("  have card : %d + pins8.card = %d := by decide +kernel" % (obound, bound))
a("  rw [← card]")
a("  refine lower_slice (T := codedGraph8) (G := codedGraph) (roots := roots8)")
a("    (other := roots) (singles := pins8) (by unfold proper; decide +kernel) (by decide +kernel)")
a("    (by decide +kernel) (by unfold proper; decide +kernel) pinRow8 (by decide +kernel) ?_ ?_ ?_ %d wholeBound" % obound)
a("  · intro a ha")
a("    change a ∈ [%s] at ha" % ", ".join(I(s) for s in coding8))
a("    simp only [List.mem_cons, List.not_mem_nil, or_false] at ha")
a("    rcases ha with " + " | ".join(["rfl"] * N))
for s in coding8:
    if s == slot:
        a("    · have he : rename pinRow8 (%s) = zero := by decide +kernel" % I(s))
        a("      rw [he]")
        a("      exact Or.inr (Or.inl ⟨false, funext bit_zero⟩)")
    else:
        a("    · have he : rename pinRow8 (%s) = (%s) := by decide +kernel" % (I(s), I(s)))
        a("      rw [he]")
        a("      exact Or.inl (List.mem_map_of_mem (by decide +kernel : (%s) ∈ roots))" % I(s))
a("  · intro a ha")
a("    simp only [pins8, Finset.mem_insert, Finset.mem_singleton] at ha")
a("    rcases ha with rfl")
a("    · refine ⟨%d, %d, by decide +kernel, ?_⟩" % (r0, r1))
a("      have h : ∀ j : Fin 8, inputs.getD (coding8 j) zero ≠ (%s) →" % I(slot))
a("          bit %d (inputs.getD (coding8 j) zero) = bit %d (inputs.getD (coding8 j) zero) := by decide +kernel" % (r0, r1))
a("      intro v hv hn")
a("      rw [roots8] at hv")
a("      obtain ⟨j, rfl⟩ := List.mem_ofFn.mp hv")
a("      exact h j hn")
a("  · intro a ha")
a("    simp only [pins8, Finset.mem_insert, Finset.mem_singleton] at ha")
a("    rcases ha with rfl")
a("    · have he : rename pinRow8 (%s) = zero := by decide +kernel" % I(slot))
a("      rw [he]")
a("      exact ⟨false, funext bit_zero⟩")
a("")
a("def graph8 (x : Fin 8 → Bool) : Bool := " + " || ".join("(x %d && x %d)" % e for e in edges))
a("")
a("def sampleInput (r : Row) (i : Fin 8) : Bool := bit r (inputs.getD (coding8 i) zero)")
a("")
a("theorem sampledInput (r : Row) : List.ofFn (sampleInput r) = roots8.map (bit r) := by")
a("  rw [roots8, List.map_ofFn]")
a("  rfl")
a("")
a("set_option maxRecDepth 12000 in")
a("set_option maxHeartbeats 0 in")
a("theorem sampleCorrect : ∀ r : Row, bit r codedGraph8 = graph8 (sampleInput r) := by decide +kernel")
a("")
a("def signedNot (g : Gate) : Bool := match g.op with")
a("  | .not => true")
a("  | _ => false")
a("")
a("theorem binaryLower (C : Circuit) (fit : FanInTwo C)")
a("    (comp : ∀ x : Fin 8 → Bool, C.eval (List.ofFn x) = graph8 x) :")
a("    %d ≤ C.gates.countP (fun g => !signedNot g) := by" % bound)
a("  have goalEq : (execute C.gates roots8).getD C.output zero = codedGraph8 := by")
a("    apply bit_ext")
a("    intro r")
a("    rw [← b_read, execute_bits _ _ _ (fun g hg => (fit g hg).1), ← sampledInput]")
a("    exact (comp (sampleInput r)).trans (sampleCorrect r).symm")
a("  have out := get_rep (u := true) (execute C.gates roots8) C.output")
a("  rw [goalEq] at out")
a("  unfold ForestCore.Repr at out")
a("  have pg : bit 0 codedGraph8 = false := by decide +kernel")
a("  rw [nrm_id pg] at out")
a("  have properGoal : proper codedGraph8 := by unfold proper; decide +kernel")
a("  obtain ⟨k, S, hk, run, sub⟩ := extract (u := true) C.gates roots8 fit (by simp) properGoal")
a("    (out.resolve_right (fun h => h properGoal))")
a("  change k ≤ C.gates.countP (fun g => !signedNot g) at hk")
a("  rw [nrm_map (by decide +kernel : roots8.all plainWord = true)] at sub")
a("  have step := list_run run S.toList (Finset.nodup_toList _) (by simp)")
a("  have ready : supply true (roots8.map observe) (S.toList.map observe) := by")
a("    intro v hv")
a("    obtain ⟨a, ha, rfl⟩ := List.mem_map.mp hv")
a("    exact Or.inl (List.mem_map_of_mem (sub a (Finset.mem_toList.mp ha)))")
a("  obtain ⟨q, bank, reach, hit, paid⟩ := contraction (observe_proper properGoal) step _ Reach.start ready")
a("  have lower := wholeBound8 q bank reach hit")
a("  omega")
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
a("    Circuit.eval ⟨witness, %d⟩ (List.ofFn x) = graph8 x := by" % outw)
a("  decide +kernel")
a("")
a("set_option maxRecDepth 100000 in")
a("set_option maxHeartbeats 0 in")
a("theorem graph_correct : ∀ x : Fin 8 → Bool, graph8 x = %s := by" % target)
a("  decide +kernel")
a("")
a("end PEqualNP.Outside.%s" % new_id)
a("")
a("open PEqualNP.Outside.%s PEqualNP.CircuitLowerBounds PEqualNP.MetaComplexity in" % new_id)
a("theorem PEqualNP.Outside.%s : (%s) := by" % (new_id, stmt))
a("  intro gates o legal _oneNot computes")
a("  by_cases hnot : ∃ g ∈ gates, g.op = GateOp.not")
a("  · have fit : FanInTwo ⟨gates, o⟩ := by")
a("      intro g hg")
a("      exact (legal g hg)")
a("    have paid := binaryLower ⟨gates, o⟩ fit (fun x => (computes x).trans (graph_correct x).symm)")
a("    change %d ≤ gates.countP (fun g => !signedNot g) at paid" % bound)
a("    obtain ⟨g, hg, hop⟩ := hnot")
a("    have extra : gates.countP (fun t => !signedNot t) < gates.length := by")
a("      by_contra! large")
a("      have allNot := List.countP_eq_length.mp (Nat.le_antisymm List.countP_le_length large) g hg")
a("      simp [signedNot, hop] at allNot")
a("    have hw : witness.length = %d := rfl" % len(gates))
a("    exact ⟨witness, %d, witnessBasis, by omega, fun x => (witnessCorrect x).trans (graph_correct x)⟩" % outw)
a("  · refine ⟨gates, o, ?_, le_rfl, computes⟩")
a("    intro g hg")
a("    obtain ⟨ops, hlen⟩ := legal g hg")
a("    exact ⟨ops.imp_right (fun h => h.resolve_right (fun hn => hnot ⟨g, hg, hn⟩)), hlen⟩")

text = head.rstrip("\n") + "\n" + "\n".join(A) + "\n"
assert '"' not in text and "sorry" not in text and "native_decide" not in text
open(out, "w", encoding="utf-8").write(text)
print("wrote", out, len(text), "bytes; merged", old_id, "bound", obound, "-> bound", bound, "+ NOT =", bound + 1,
      "| coding8", coding8, "| deleted vertex", vdel, "at slot", slot, "| rows", r0, r1)
