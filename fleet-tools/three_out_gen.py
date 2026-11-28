#!/usr/bin/env python3
"""three_out_gen.py: "Three ordered outputs a, b, c exceed k gates at a two-NOT limit" (6 thermometer wires, 5 rows).

usage: python3 -I three_out_gen.py <lease.json> <out.lean>
Reads the targets, k and the NOT budget from the statement, runs the same search as the template's in-kernel `search`
(gates AND/OR on any two wires, NOT within the budget), then fills Normal5's generic template
(templates/three_out_49912.lean, L-meta-49912, open-goat/pequalnp-proofs#54038).
exit 0 file written ("exceed" unit, no circuit found); 4 a circuit exists, so an "exceed" unit is false and a "fit" unit
would be true (no generator for the "fit" side yet); for a "fit" unit with no circuit found: 4 as well (the unit is false);
3 statement of another shape.
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.realpath(__file__))
START, FULL = (30, 28, 24, 16, 0, 31), 31   # x0..x3 thermometer columns, false, true (bit t = row t)

def circuit_exists(T, k, nots_max):
    T = set(T)
    def dfs(w, nots, used):
        if T <= set(w): return True
        if used == k or len(T - set(w)) > k - used: return False
        seen = set(w)
        cand = {op for i in range(len(w)) for j in range(i, len(w)) for op in (w[i] & w[j], w[i] | w[j])} - seen
        neg = ({FULL ^ v for v in w} - seen - cand) if nots < nots_max else set()
        return any(dfs(w + (v,), nots, used + 1) for v in sorted(cand)) or \
               any(dfs(w + (v,), nots + 1, used + 1) for v in sorted(neg))
    return dfs(START, 0, 0)

def main():
    leasep, outp = sys.argv[1:3]
    g = json.load(open(leasep))["gap"]
    st = g["statement"].strip()
    shape = ("(p q r : Fin (6+D.size))" in st and "NotBracket.notCount D ≤" in st and "∀ t : Fin 5" in st
             and "(fun i : Fin 4 => decide (i.val < t.val))) ++ [false,true]" in st)
    T = [int(x) for x in re.findall(r"\((\d+) : Nat\)\.testBit t\.val", st)]
    k = re.search(r"D\.size ≤ (\d+)", st); nb = re.search(r"notCount D ≤ (\d+)", st)
    if not (shape and len(T) == 3 and len(set(T)) == 3 and all(t < 32 for t in T) and k and nb): sys.exit(3)
    k, nb = int(k.group(1)), int(nb.group(1))
    exceed = st.startswith("¬")
    if circuit_exists(T, k, nb) or not exceed:
        print("%s: %s" % (g["id"], "a circuit exists: false" if exceed else "fit unit: no generator for the positive side"
                          if circuit_exists(T, k, nb) else "fit unit with no circuit: false"), file=sys.stderr)
        sys.exit(4 if (exceed or not circuit_exists(T, k, nb)) else 3)
    src = open(os.path.join(HERE, "templates", "three_out_49912.lean"), encoding="utf-8").read()
    sid = g["id"].replace("-", "_")
    src = src.replace("L_meta_49912", sid)
    tl = "[%s]" % ", ".join(map(str, T))
    src = src.replace("theorem search_false : search [5, 17, 22] 6 m0 2 = false",
                      "theorem search_false : search %s %d m0 %d = false" % (tl, k, nb))
    src = src.replace("no_circuit [5, 17, 22] (by decide) 6 2 search_false", "no_circuit %s (by decide) %d %d search_false" % (tl, k, nb))
    a = src.index("theorem PEqualNP.Outside.%s : " % sid); b = src.index(" := by\n  rintro", a)
    src = src[:a] + "theorem PEqualNP.Outside.%s : (%s)" % (sid, st) + src[b:]
    assert src.count(tl) >= 2 and ("[5, 17, 22]" not in src or tl == "[5, 17, 22]")
    open(outp, "w", encoding="utf-8").write(src)
    print("wrote %s: targets %s, k=%d, NOT budget %d" % (outp, T, k, nb))

if __name__ == "__main__":
    main()
