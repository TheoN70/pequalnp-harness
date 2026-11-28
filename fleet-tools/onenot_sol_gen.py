#!/usr/bin/env python3
"""onenot_sol_gen.py: "At fan-in two, one NOT gate saves nothing on edges ..." (8 vertices) at AND/OR size M = 14, on the
"Sol" engine of the merged L_meta_29168 (Tianhao Wang, open-goat/pequalnp-proofs#42324).

usage: python3 -I onenot_sol_gen.py <lease.json> <out.lean> [--clone DIR] [--gates JSON]
The instance is a function of the graph (checked bit for bit against 29168): rows = the 64 smallest true points, then the
separating pairs (t, f) as in sol_gen.py (edges t > f, plus (t, 0) and (t, maximal independent set) for each minimal t).
rt = the exact AND/OR size of G - Z (liveg) for every |Z| <= 3 leaving an edge (29168 uses exactly these).
M and the witness come from liveg (or --gates, pequalnp numbering). Exit 3: M is not 14 (no template) or other shape.
"""
import json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.realpath(__file__))
TID, PR, TPL_M = "L_meta_29168", "42324", 14
N = 8

def liveg(edges, lo=0, hi=16):
    es = ",".join("%d-%d" % e for e in edges)
    for tb in ("26", "27"):
        o = subprocess.run([os.path.join(HERE, "liveg"), str(N), es, "0", "0", str(lo), str(hi), tb],
                           capture_output=True, text=True, timeout=1800).stdout
        m = re.findall(r"N=(\d+) FOUND", o)
        if m: break
    else: return None, None
    gs = re.findall(r"w\d+ = (and|or) \[(\d+), (\d+)\]", o.split("FOUND", 1)[1])
    return int(m[0]), [(op, int(a), int(b)) for op, a, b in gs]

def instance(E):
    R = 1 << N; tv = lambda a: any(a >> i & 1 and a >> j & 1 for i, j in E)
    ones = [a for a in range(R) if tv(a)]
    mins = [a for a in ones if all(not tv(a ^ (1 << i)) for i in range(N) if a >> i & 1)]
    maxs = [a for a in range(R) if not tv(a) and all(tv(a | (1 << i)) for i in range(N) if not a >> i & 1)]
    P = set()
    for t in ones:
        P |= {(t, t ^ (1 << i)) for i in range(N) if t >> i & 1 and not tv(t ^ (1 << i))}
        if t in mins: P |= {(t, 0)} | {(t, f) for f in maxs}
    co = [(r, 0, "") for r in ones[:64]]
    for t in sorted({t for t, _ in P}):
        co += [(t, f, "A") for (u, f) in sorted(P) if u == t]; co.append((0, 0, "x"))
    for f in sorted({f for _, f in P}):
        co += [(t, f, "A") for (t, g) in sorted(P, key=lambda p: (p[1], p[0])) if g == f]; co.append((0, 0, "y"))
    NN = len(co)
    bits = lambda cond: sum(1 << c for c, x in enumerate(co) if cond(x))
    AA = bits(lambda x: x[2] == "A")
    sp = lambda fl, start: list(zip([start] + [c for c, x in enumerate(co) if x[2] == fl][:-1], [c for c, x in enumerate(co) if x[2] == fl]))
    segX = sp("x", 63)
    return dict(NN=NN, AA=AA, HX=bits(lambda x: x[2] == "x"), HY=bits(lambda x: x[2] == "y"), TG=AA | bits(lambda x: x[2] == "" and tv(x[0])),
                raw=[sum(((a >> i & 1) << c) | ((b >> i & 1) << (NN + c)) for c, (a, b, _) in enumerate(co)) for i in range(N)],
                segX=segX, segY=sp("y", segX[-1][1]))

def nest(items, op):
    return items[0] if len(items) == 1 else "(%s %s %s)" % (items[0], op, nest(items[1:], op))

def forms(E):
    return (nest(["(x %d && x %d)" % e for e in E], "||"), nest(["(b%d && b%d)" % e for e in E], "||"),
            nest(["(rawP.getD %d 0 &&& rawP.getD %d 0)" % e for e in E], "|||"))

def main():
    leasep, outp = sys.argv[1:3]
    clone = sys.argv[sys.argv.index("--clone") + 1] if "--clone" in sys.argv else os.path.join(HERE, "..", "..", "pequalnp-proofs")
    g = json.load(open(leasep))["gap"]; st = g["statement"]
    m = re.search(r"\(\[([\d, ]+)\] : List ℕ\)", st)
    if not ("Fin 8 → Bool" in st and "GateOp.not → i = j" in st and m) or st.lstrip().startswith("¬"): sys.exit(3)
    lit = "[%s]" % m.group(1); L = [int(x) for x in m.group(1).split(",")]
    E = [(L[2 * k], L[2 * k + 1]) for k in range(len(L) // 2)]
    if "--gates" in sys.argv:
        gates = [(o, a, b) for o, (a, b) in json.loads(sys.argv[sys.argv.index("--gates") + 1])]; M = len(gates)
    else:
        M, gates = liveg(E)
    if M != TPL_M: print("M = %s; the template proves M = %d only" % (M, TPL_M), file=sys.stderr); sys.exit(3)
    rt = {}
    for Z in range(1, 256):
        sub = [e for e in E if not (Z >> e[0] & 1 or Z >> e[1] & 1)]
        if bin(Z).count("1") <= 3 and sub: rt[Z] = liveg(sub)[0]
    I = instance(E)
    src = subprocess.run(["git", "-C", clone, "show", "upstream/main:lean/PEqualNP/Outside/%s.lean" % TID],
                         capture_output=True, text=True, check=True).stdout
    oldlit = re.search(r"decide \(∃ i < \((\[[\d, ]+\]) : List ℕ\)", src).group(1)
    OL = [int(x) for x in oldlit[1:-1].split(",")]
    OE = [(OL[2 * k], OL[2 * k + 1]) for k in range(len(OL) // 2)]
    for o, n in zip(forms(OE), forms(E)):
        assert o in src, o[:60]; src = src.replace(o, n)
    src = src.replace(oldlit, lit).replace(TID, g["id"].replace("-", "_"))
    def sub(pat, new):
        nonlocal src
        assert len(re.findall(pat, src, re.M)) == 1, pat
        src = re.sub(pat, lambda _: new, src, flags=re.M)
    h = lambda x: "0x%x" % x
    sub(r"^def NN : Nat := \d+$", "def NN : Nat := %d" % I["NN"])
    for k in ("AA", "HX", "HY"): sub(r"^def %s : Nat := 0x[0-9a-f]+$" % k, "def %s : Nat := %s" % (k, h(I[k])))
    sub(r"^def TG : ℕ := 0x[0-9a-f]+$", "def TG : ℕ := %s" % h(I["TG"]))
    sub(r"^def rawP : List ℕ := \[.*\]$", "def rawP : List ℕ := [%s]" % ", ".join(h(w) for w in I["raw"]))
    sub(r"^def segsX : List \(ℕ × ℕ\) := .*$", "def segsX : List (ℕ × ℕ) := %s" % str(I["segX"]))
    sub(r"^def segsY : List \(ℕ × ℕ\) := .*$", "def segsY : List (ℕ × ℕ) := %s" % str(I["segY"]))
    for k in (1, 2, 3):
        sub(r"^def rt%d : List \(ℕ × ℕ\) := .*$" % k, "def rt%d : List (ℕ × ℕ) := [%s]" % (k, ", ".join(
            "(%d, %d)" % (Z, rt[Z]) for Z in sorted(rt) if bin(Z).count("1") == k)))
    sub(r"^def smallGates : List Gate := .*$", "def smallGates : List Gate := [%s]" % ", ".join("⟨.%s, [%d, %d]⟩" % gg for gg in gates))
    hdr = ("-- Engine copied verbatim from the merged %s by Tianhao Wang (open-goat/pequalnp-proofs#%s);\n"
           "-- only the instance data, restriction bounds, graph and witness are regenerated (fleet-tools/onenot_sol_gen.py).\n" % (TID, PR))
    src = src.replace("import PEqualNP.Defs\n", "import PEqualNP.Defs\n" + hdr, 1)
    open(outp, "w", encoding="utf-8").write(src)
    print("wrote %s: NN=%d, M=%d, %d rt entries, %d bytes" % (outp, I["NN"], M, len(rt), len(src.encode())))

if __name__ == "__main__":
    main()
