#!/usr/bin/env python3
"""three_out_fit_gen.py: the "fit" side of "(On five input bits,) three ordered outputs a, b, c fit k gates with at most
two NOTs" (4 or 5 input bits): search a circuit, write it as foudres's data-only proof (L-meta-50062,
open-goat/pequalnp-proofs#54236; same shape as hillside-spengler's L-meta-49863, #53719): the circuit, the three output
wires, then FanInTwo by cases and `decide` for ReadsBack, the NOT count, the size and the rows.

usage: python3 -I three_out_fit_gen.py <lease.json> <out.lean> [--gates "not 1;or 2 6;..." --pqr 9,10,8]
  --gates/--pqr: write that circuit instead of searching (regression: --demo regenerates L_meta_50062 byte for byte).
exit 0 written; 3 not a "fit" unit of this shape; 4 no circuit within k gates and the NOT budget (the unit is false).
Called by autosolve.sh when three_out_gen.py exits 3 (true "fit" unit).
"""
import os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from gen_common import load_lease, write, die, OTHER, FALSE

START = {4: (30, 28, 24, 16, 0, 31), 5: (62, 60, 56, 48, 32, 0, 63)}   # wire values as row bitmasks (bit t = row t)
OP = "PEqualNP.CircuitLowerBounds.GateOp."

def search(T, k, nots_max, n):   # same DFS as three_out_gen.circuit_exists, but returns the gates
    T = set(T); FULL = (1 << (n + 1)) - 1
    def dfs(w, gates, nots):
        if T <= set(w): return gates
        if len(gates) == k or len(T - set(w)) > k - len(gates): return None
        seen, cand = set(w), {}
        for i in range(len(w)):
            for j in range(i, len(w)):
                for op, v in (("and", w[i] & w[j]), ("or", w[i] | w[j])):
                    if v not in seen: cand.setdefault(v, (op, [i, j]))
        neg = {}
        if nots < nots_max:
            for i, v in enumerate(w):
                if FULL ^ v not in seen and FULL ^ v not in cand: neg.setdefault(FULL ^ v, ("not", [i]))
        for v in sorted(cand):
            r = dfs(w + (v,), gates + [cand[v]], nots)
            if r is not None: return r
        for v in sorted(neg):
            r = dfs(w + (v,), gates + [neg[v]], nots + 1)
            if r is not None: return r
        return None
    g = dfs(START[n], [], 0)
    if g is None: return None
    w = list(START[n])
    for op, a in g: w.append(FULL ^ w[a[0]] if op == "not" else (w[a[0]] & w[a[1]] if op == "and" else w[a[0]] | w[a[1]]))
    return g, w

def render(g, gates, pqr, nw):
    gl = ", ".join("⟨%s%s, [%s]⟩" % (OP, op, ", ".join(map(str, a))) for op, a in gates)
    return ("import PEqualNP.Defs\nimport PEqualNP.Defs.NestedCoverCircuit\nimport PEqualNP.Defs.NotBracket\n\n"
            "theorem PEqualNP.Outside.%s : (%s) := by\n"
            "  refine ⟨⟨[%s], %d⟩, %s, ?_, ?_, ?_, ?_, ?_⟩\n"
            "  · intro g hg\n    simp only [List.mem_cons, List.not_mem_nil, or_false] at hg\n"
            "    rcases hg with %s <;> simp\n"
            "  · decide\n  · decide\n  · decide\n  · decide\n") % (
        g.sid, g.statement, gl, nw + len(gates) - 1, ", ".join("⟨%d, by decide⟩" % x for x in pqr),
        " | ".join(["rfl"] * len(gates)))

def main(a):
    g = load_lease(a[0]); st = g.statement.strip()
    if st.startswith("¬"): die(OTHER, "exceed unit: three_out_gen.py's side")
    n = 5 if "(p q r : Fin (7+D.size))" in st else 4
    T = [int(x) for x in re.findall(r"\((\d+) : Nat\)\.testBit t\.val", st)]
    k = re.search(r"D\.size ≤ (\d+)", st); nb = re.search(r"notCount D ≤ (\d+)", st)
    if not ("(p q r : Fin (%d+D.size))" % (n + 2) in st and "∀ t : Fin %d" % (n + 1) in st and len(T) == 3 and k and nb):
        die(OTHER, "not a three-outputs fit statement")
    k, nb = int(k.group(1)), int(nb.group(1))
    if "--gates" in a:
        gates = [(x.split()[0], [int(y) for y in x.split()[1:]]) for x in a[a.index("--gates") + 1].split(";")]
        pqr = [int(x) for x in a[a.index("--pqr") + 1].split(",")]
    else:
        r = search(T, k, nb, n)
        if r is None: die(FALSE, "%s: no circuit of <= %d gates with <= %d NOTs: the fit unit is false" % (g.id, k, nb))
        gates, w = r
        pqr = [w.index(t) for t in T]
    assert len(gates) <= k and sum(op == "not" for op, _ in gates) <= nb
    write(a[1], render(g, gates, pqr, n + 2))

if __name__ == "__main__":
    if sys.argv[1:2] == ["--demo"]:   # needs $PENP/pequalnp-proofs with upstream/main and the lease json of 50062
        import json, tempfile
        here = os.path.dirname(os.path.realpath(__file__)); clone = os.path.join(here, "..", "..", "pequalnp-proofs")
        ref = subprocess.run(["git", "-C", clone, "show", "upstream/main:lean/PEqualNP/Outside/L_meta_50062.lean"],
                             capture_output=True, text=True).stdout
        stmt = ref.split("theorem PEqualNP.Outside.L_meta_50062 : (", 1)[1].split(") := by\n", 1)[0]
        d = tempfile.mkdtemp(); lp = os.path.join(d, "l.json"); op = os.path.join(d, "o.lean")
        json.dump({"gap": {"id": "L-meta-50062", "statement": stmt, "title": "", "file": "", "module": ""}}, open(lp, "w"))
        main([lp, op, "--gates", "not 1;or 2 6;and 0 7;not 7;or 3 9", "--pqr", "9,10,8"])
        assert open(op).read() == ref, "50062 not regenerated"
        main([lp, op]); print("demo ok: 50062 regenerated byte for byte; searched circuit written too")
    else: main(sys.argv[1:])
