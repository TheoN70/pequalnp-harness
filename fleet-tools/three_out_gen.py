#!/usr/bin/env python3
"""three_out_gen.py: "Three ordered outputs a, b, c exceed k gates at a two-NOT limit", on 4 input bits (6 wires, 5 rows:
Normal5's templates/three_out_49912.lean, #54038) or 5 input bits (7 wires, 6 rows: Normal4's three_out_50211.lean,
#54296, for k <= 5; Normal2's split generator three_out_gen6.py on three_out_50195.lean, #54937, for k = 6).

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
START = {4: (30, 28, 24, 16, 0, 31), 5: (62, 60, 56, 48, 32, 0, 63)}   # thermometer columns, false, true (bit t = row t)

def circuit_exists(T, k, nots_max, n=4):
    T = set(T); FULL = (1 << (n + 1)) - 1
    def dfs(w, nots, used):
        if T <= set(w): return True
        if used == k or len(T - set(w)) > k - used: return False
        seen = set(w)
        cand = {op for i in range(len(w)) for j in range(i, len(w)) for op in (w[i] & w[j], w[i] | w[j])} - seen
        neg = ({FULL ^ v for v in w} - seen - cand) if nots < nots_max else set()
        return any(dfs(w + (v,), nots, used + 1) for v in sorted(cand)) or \
               any(dfs(w + (v,), nots + 1, used + 1) for v in sorted(neg))
    return dfs(START[n], 0, 0)

def main():
    leasep, outp = sys.argv[1:3]
    g = json.load(open(leasep))["gap"]
    st = g["statement"].strip()
    n = 5 if "(p q r : Fin (7+D.size))" in st else 4
    shape = ("(p q r : Fin (%d+D.size))" % (n + 2) in st and "NotBracket.notCount D ≤" in st and "∀ t : Fin %d" % (n + 1) in st
             and "(fun i : Fin %d => decide (i.val < t.val))) ++ [false,true]" % n in st)
    T = [int(x) for x in re.findall(r"\((\d+) : Nat\)\.testBit t\.val", st)]
    k = re.search(r"D\.size ≤ (\d+)", st); nb = re.search(r"notCount D ≤ (\d+)", st)
    if not (shape and len(T) == 3 and len(set(T)) == 3 and all(t < 2 ** (n + 1) for t in T) and k and nb): sys.exit(3)
    k, nb = int(k.group(1)), int(nb.group(1))
    exceed = st.startswith("¬")
    if circuit_exists(T, k, nb, n) or not exceed:
        print("%s: %s" % (g["id"], "a circuit exists: false" if exceed else "fit unit: no generator for the positive side"
                          if circuit_exists(T, k, nb, n) else "fit unit with no circuit: false"), file=sys.stderr)
        sys.exit(4 if (exceed or not circuit_exists(T, k, nb, n)) else 3)
    sid = g["id"].replace("-", "_"); tl = "[%s]" % ", ".join(map(str, T))
    if n == 5 and k == 6 and nb == 2:   # Normal2's split generator (one decide is too big at k = 6)
        import subprocess
        r = subprocess.run([sys.executable, "-I", os.path.join(HERE, "three_out_gen6.py"), g["id"]] + [str(t) for t in T],
                           capture_output=True, text=True)
        if r.returncode or "theorem PEqualNP.Outside.%s :" % sid not in r.stdout: print(r.stderr, file=sys.stderr); sys.exit(2)
        open(outp, "w", encoding="utf-8").write(r.stdout); print("wrote %s (k=6 split): targets %s" % (outp, T)); return
    if n == 5 and k > 5 or n == 4 and k > 6: print("no template for n=%d k=%d" % (n, k), file=sys.stderr); sys.exit(3)
    tid, old_t, old_k = ("L_meta_49912", "[5, 17, 22]", 6) if n == 4 else ("L_meta_50211", "[13, 40, 45]", 5)
    src = open(os.path.join(HERE, "templates", "three_out_%s.lean" % tid[7:]), encoding="utf-8").read()
    src = src.replace(tid, sid)
    src = src.replace("theorem search_false : search %s %d m0 2 = false" % (old_t, old_k),
                      "theorem search_false : search %s %d m0 %d = false" % (tl, k, nb))
    src = src.replace("no_circuit %s (by decide) %d 2 search_false" % (old_t, old_k), "no_circuit %s (by decide) %d %d search_false" % (tl, k, nb))
    a = src.index("theorem PEqualNP.Outside.%s : " % sid); b = src.index(" := by\n  rintro", a)
    src = src[:a] + "theorem PEqualNP.Outside.%s : (%s)" % (sid, st) + src[b:]
    assert src.count(tl) >= 2 and (old_t not in src or tl == old_t)
    open(outp, "w", encoding="utf-8").write(src)
    print("wrote %s: targets %s, k=%d, NOT budget %d" % (outp, T, k, nb))

if __name__ == "__main__":
    main()
