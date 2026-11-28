#!/usr/bin/env python3
"""sol13_gen.py: Lean proof of a Table 2 unit ("six-input monotone f: every AND/OR/NOT circuit has an AND/OR one no
larger") at AND/OR size M = 13, from willakone's merged L_meta_49521 (open-goat/pequalnp-proofs#53178), a Sol-engine
variant with restrictions to 0 AND to 1.

usage: python3 -I sol13_gen.py <lease.json> <out.lean> [--clone DIR] [--rt "Z:L,..."] [--only-rt] [--witness FILE] [--diag]
(sol_gen.py hands M = 13 tables here, so sol_fit.py and autosolve.sh need no change.)

Only data changes; the engine, the root case split (k11t*/k12t*, unit-independent covers of the MM buckets) and every
proof are kept verbatim. Data, all functions of the table (49521 reproduces bit for bit except rt fitting):
- instance (NN, AA, HX, HY, rawP, TG, segsX/Y) = sol_gen.instance;
- cutMasks: 12 masks, cut j<6 = "x_j := 0", cut 6+j = "x_j := 1"; a coordinate (a, b) survives cut (j, v) iff
  a_j = v and b_j = v (rows < 64: iff a_j = v);
- rt: Z = 12-bit set of cuts, 1 <= |Z| <= 3, restriction not constant; L = AND/OR size of the restriction - |Z| - 1
  (49521 uses one less on some |Z| = 3: lower an entry with --rt when its okE fails, as with sol_fit.py).
Exit 3 when the AND/OR size is not 13.
"""
import json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, HERE)
from sol_gen import instance, live, big, mono

TID, PR = "L_meta_49521", "53178"

def restr(T, Z):
    z0, z1 = Z & 63, Z >> 6
    return sum((T >> ((a & ~z0) | z1) & 1) << a for a in range(64))

def cut_masks(I):
    NN, raw = I["NN"], I["raw"]
    A = [sum((raw[j] >> c & 1) << j for j in range(6)) for c in range(NN)]
    B = [sum((raw[j] >> (NN + c) & 1) << j for j in range(6)) for c in range(NN)]
    keep = lambda c, j, v: (A[c] >> j & 1) == v and (c < 64 or (B[c] >> j & 1) == v)
    return [sum(1 << c for c in range(NN) if not keep(c, i % 6, i // 6)) for i in range(12)]

def zs(T):
    return [Z for Z in range(1, 4096) if not (Z & 63 & (Z >> 6)) and bin(Z).count("1") <= 3
            and restr(T, Z) not in (0, 2 ** 64 - 1)]

def main():
    leasep, outp = sys.argv[1:3]
    arg = lambda k: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else None
    clone = arg("--clone") or os.path.join(HERE, "..", "..", "pequalnp-proofs")
    gap = json.load(open(leasep))["gap"]
    sid = gap["id"].replace("-", "_")
    tstr = re.search(r"Nat\.testBit \((\d+ \* 2 \^ 32 \+ \d+)\)", gap["statement"]).group(1)
    T = int(tstr.split("*")[0]) * 2 ** 32 + int(tstr.split("+")[1])
    M, gates = live(T)
    if arg("--witness"):
        gates = [tuple(g) for g in json.load(open(arg("--witness")))]; M = len(gates)
    if M != 13: print("AND/OR size M = %s, not 13" % M, file=sys.stderr); sys.exit(3)
    I = instance(T)
    Z = zs(T)
    given = dict(map(int, e.split(":")) for e in (arg("--rt") or "").split(",") if e)
    if "--only-rt" in sys.argv: Z = [z for z in Z if z in given]   # reproduce a file's exact entry list
    rt = {}
    for z in Z:
        if z in given: rt[z] = given[z]; continue
        s = live(restr(T, z))[0]
        if s is not None: rt[z] = s - bin(z).count("1") - 1   # None: restriction is a single input, no bound
    Z = [z for z in Z if z in rt]
    src = subprocess.run(["git", "-C", clone, "show", "upstream/main:lean/PEqualNP/Outside/%s.lean" % TID],
                         capture_output=True, text=True, check=True).stdout
    otstr = re.search(r"Nat\.testBit \((\d+ \* 2 \^ 32 \+ \d+)\)", src).group(1)
    src = src.replace(TID, sid).replace(otstr, tstr)
    def sub(pat, new):
        nonlocal src
        assert len(re.findall(pat, src, re.M)) == 1, pat
        src = re.sub(pat, lambda _: new, src, flags=re.M)
    B = {0: I["AA"], 1: I["HX"], 2: I["HY"], 9: I["TG"], **{3 + i: I["raw"][i] for i in range(6)}}
    for k, v in B.items(): sub(r"^def bigNat_%d : Nat := .*$" % k, "def bigNat_%d : Nat := %s" % (k, big(v)))
    sub(r"^def NN : Nat := \d+$", "def NN : Nat := %d" % I["NN"])
    sub(r"^def segsX : List \(ℕ × ℕ\) := .*$", "def segsX : List (ℕ × ℕ) := %s" % I["segX"])
    sub(r"^def segsY : List \(ℕ × ℕ\) := .*$", "def segsY : List (ℕ × ℕ) := %s" % I["segY"])
    sub(r"^def cutMasks : List ℕ := .*$", "def cutMasks : List ℕ := [%s]" % ", ".join("(%s)" % big(c) for c in cut_masks(I)))
    sub(r"^def f \(x : Fin 6 → Bool\) : Bool := .*$", "def f (x : Fin 6 → Bool) : Bool := " + " || ".join(mono(m, lambda i: "x %d" % i) for m in I["mins"]))
    sub(r"^def EF : ℕ := .*$", "def EF : ℕ := " + " ||| ".join(mono(m, lambda i: "rawP.getD %d 0" % i).replace("&&", "&&&") for m in I["mins"]))
    sub(r"^  ⟨\[⟨\..*\], \d+⟩$", "  ⟨[%s], %d⟩" % (", ".join("⟨.%s, [%d, %d]⟩" % g for g in gates), 6 + len(gates) - 1))
    # restriction rows: groups of 4 (|Z| = 2, 3) or 1 (|Z| = 1), as in 49521
    prev = {3: "[]", 2: "rt3", 1: "(rt2 ++ rt3)"}
    defs, oks = [], []
    diag = "--diag" in sys.argv
    for k in (3, 2, 1):
        es = [(z, rt[z]) for z in Z if bin(z).count("1") == k]
        g = 1 if k == 1 or diag else 4   # --diag: one entry per theorem, tagged for sol_fit.py
        gs = [es[i:i + g] for i in range(0, len(es), g)]
        names = ["row%dg%d" % (k, i) for i in range(len(gs))]
        gm = {n: gg[0] for n, gg in zip(names, gs)}
        defs += ["def %s : List (ℕ × ℕ) := [%s]" % (n, ", ".join("(%d, %d)" % e for e in g)) for n, g in zip(names, gs)]
        defs.append("def rt%d : List (ℕ × ℕ) := %s" % (k, " ++ ".join(names)))
        for n in names:
            oks += ["set_option maxRecDepth 100000 in", "set_option maxHeartbeats 0 in",
                    "theorem %sok : %s.all (fun e => okE [] (pr %s e.1) e) = true := by decide +kernel" % (n, n, prev[k])
                    + (" -- RT %d %d" % gm[n] if diag else "")]
        oks.append("theorem r%d : rt%d.all (fun e => okE [] (pr %s e.1) e) = true := by" % (k, k, prev[k]))
        oks.append("  simp only [rt%d, List.all_append, Bool.and_true, %s]" % (k, ", ".join(n + "ok" for n in names)))
        oks.append({3: "lemma i3 : ∀ e ∈ rt3, Imp [] e.1 e.2 := okAll (T := []) r3 (by simp)",
                    2: "lemma i2 : ∀ e ∈ rt2, Imp [] e.1 e.2 := okAll r2 i3",
                    1: "lemma i1 : ∀ e ∈ rt1, Imp [] e.1 e.2 := okAll r1 (apI i2 i3)"}[k])
    L = src.split("\n")
    a = next(i for i, l in enumerate(L) if l.startswith("def row3g0 "))
    b = next(i for i, l in enumerate(L) if l.startswith("def rt1 "))
    L[a:b + 1] = defs
    a = next(i for i, l in enumerate(L) if l.startswith("theorem row3g0ok ")) - 2
    b = next(i for i, l in enumerate(L) if l.startswith("lemma i1 "))
    L[a:b + 1] = oks
    src = "\n".join(L)
    hdr = ("-- Engine copied verbatim from the merged %s by willakone (open-goat/pequalnp-proofs#%s), on David Li's Sol engine;\n" % (TID, PR) +
           "-- only the instance data, cut masks, restriction bounds, target and witness are regenerated (fleet-tools/sol13_gen.py).\n")
    src = src.replace("import PEqualNP.Defs\n", "import PEqualNP.Defs\n" + hdr, 1)
    open(outp, "w", encoding="utf-8").write(src)
    print("wrote %s: NN=%d, %d rt entries, %d bytes" % (outp, I["NN"], len(rt), len(src.encode())))

if __name__ == "__main__":
    main()
