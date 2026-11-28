#!/usr/bin/env python3
"""sol_gen.py: Lean proof of a Table 2 unit ("six-input monotone f: every AND/OR/NOT circuit has an AND/OR one no larger")
from the "Sol" engine of the merged L_meta_46290 (David Li, dli7319, open-goat/pequalnp-proofs#51796), the engine other
handles use for Table 2 at m = 11-12 and one-NOT at M >= 14.

usage: python3 -I sol_gen.py <lease.json> <out.lean> [--clone DIR] [--rt "Z:L,Z:L,..."] [--witness FILE] [--diag]

Only the data lines of the template change; the engine and its proofs are kept verbatim. The instance is a function of
the truth table alone (checked bit for bit against 46290 and 46236): coordinates = the 64 rows, then the separating pairs
(t, f) with t true, f false: every edge t > f, plus (t, 0) and (t, max false point) for each minimal true t; listed by t
(X part, spacer after each t) then by f (Y part). rt = lower bounds for f with the inputs of Z fixed to 0 (|Z| <= 3,
restriction not constant), checked in the kernel by okE; default L = AND/OR size of the restriction - |Z| - 1 (the rule
of the two merged files, which sometimes use one less on |Z| = 3: lower an entry with --rt when its okE check fails).
M (the AND/OR size, from `live` mode 0) picks the template: L_meta_46290 (M = 12, #51796) or L_meta_43480 (M = 11,
#51005), both by David Li, read from upstream/main of the clone (default $PENP/pequalnp-proofs).
"""
import json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.realpath(__file__))
TEMPLATES = {12: ("L_meta_46290", "51796"), 11: ("L_meta_43480", "51005")}   # David Li (dli7319), merged upstream

def instance(T, n=6):
    R = 1 << n; tv = lambda a: T >> a & 1
    ones = [a for a in range(R) if tv(a)]
    mins = [a for a in ones if all(not tv(a ^ (1 << i)) for i in range(n) if a >> i & 1)]
    maxs = [a for a in range(R) if not tv(a) and all(tv(a | (1 << i)) for i in range(n) if not a >> i & 1)]
    P = set()
    for t in ones:
        P |= {(t, t ^ (1 << i)) for i in range(n) if t >> i & 1 and not tv(t ^ (1 << i))}
        if t in mins: P |= {(t, 0)} | {(t, f) for f in maxs}
    co = [(r, 0, "") for r in range(R)]
    for t in sorted({t for t, _ in P}):
        co += [(t, f, "A") for (u, f) in sorted(P) if u == t]; co.append((0, 0, "x"))
    for f in sorted({f for _, f in P}):
        co += [(t, f, "A") for (t, g) in sorted(P, key=lambda p: (p[1], p[0])) if g == f]; co.append((0, 0, "y"))
    NN = len(co)
    bits = lambda cond: sum(1 << c for c, x in enumerate(co) if cond(x))
    AA = bits(lambda x: x[2] == "A")
    sp = lambda fl, start: list(zip([start] + [c for c, x in enumerate(co) if x[2] == fl][:-1], [c for c, x in enumerate(co) if x[2] == fl]))
    segX = sp("x", R - 1)
    return dict(NN=NN, AA=AA, HX=bits(lambda x: x[2] == "x"), HY=bits(lambda x: x[2] == "y"),
                TG=AA | sum(1 << r for r in range(R) if tv(r)),
                raw=[sum(((a >> i & 1) << c) | ((b >> i & 1) << (NN + c)) for c, (a, b, _) in enumerate(co)) for i in range(n)],
                segX=segX, segY=sp("y", segX[-1][1]), mins=mins)

def live(tab, lo=0, hi=16):
    """exact AND/OR size and a least circuit of a 6-input monotone table (fleet-tools/live mode 0)"""
    o = subprocess.run([os.path.join(HERE, "live"), "%016x" % tab, "0x3f", "0", "0", str(lo), str(hi), "26"],
                       capture_output=True, text=True, timeout=900).stdout
    m = re.search(r"N=(\d+) FOUND", o)
    if not m: return None, None
    wires = {sum(1 << a for a in range(64) if a >> i & 1): i for i in range(6)}
    gates = []
    for op, a, b, c in re.findall(r"(and|or) ([0-9a-f]{16}) ([0-9a-f]{16}) -> ([0-9a-f]{16})", o.split(m.group(0))[1] if False else o):
        a, b, c = int(a, 16), int(b, 16), int(c, 16)
        gates.append((op, wires[a], wires[b])); wires[c] = 6 + len(gates) - 1
    return int(m.group(1)), gates

def restr(T, Z): return sum((T >> (a & ~Z) & 1) << a for a in range(64))

def big(x):
    limbs = []
    while x: limbs.append(x & (2 ** 64 - 1)); x >>= 64
    return "([%s] : List Nat).foldr (fun x a => x + 18446744073709551616 * a) 0" % ", ".join(map(str, limbs or [0]))

def mono(m, var):
    return "(" + " && ".join(var(i) for i in range(6) if m >> i & 1) + ")"

def main():
    leasep, outp = sys.argv[1:3]
    clone = sys.argv[sys.argv.index("--clone") + 1] if "--clone" in sys.argv else os.path.join(HERE, "..", "..", "pequalnp-proofs")
    gap = json.load(open(leasep))["gap"]
    sid = gap["id"].replace("-", "_")
    tstr = re.search(r"Nat\.testBit \((\d+ \* 2 \^ 32 \+ \d+)\)", gap["statement"]).group(1)
    T = int(tstr.split("*")[0]) * 2 ** 32 + int(tstr.split("+")[1])
    M, gates = live(T)
    if "--witness" in sys.argv:
        gates = [tuple(g) for g in json.load(open(sys.argv[sys.argv.index("--witness") + 1]))]; M = len(gates)
    if M not in TEMPLATES: print("AND/OR size M = %s; templates exist for M = %s only" % (M, sorted(TEMPLATES)), file=sys.stderr); sys.exit(3)
    tid, pr = TEMPLATES[M]
    I = instance(T)
    Zs = [Z for Z in range(1, 64) if bin(Z).count("1") <= 3 and restr(T, Z) not in (0, 2 ** 64 - 1)]
    rt = {Z: live(restr(T, Z))[0] - bin(Z).count("1") - 1 - (bin(Z).count("1") >= 2) for Z in Zs}   # one less from |Z| = 2: one compile instead of 3-4
    if "--rt" in sys.argv:
        for e in sys.argv[sys.argv.index("--rt") + 1].split(","):
            if e: z, l = e.split(":"); rt[int(z)] = int(l)
    rl = lambda k: "[%s]" % ", ".join("(%d, %d)" % (Z, rt[Z]) for Z in Zs if bin(Z).count("1") == k)
    src = subprocess.run(["git", "-C", clone, "show", "upstream/main:lean/PEqualNP/Outside/%s.lean" % tid],
                         capture_output=True, text=True, check=True).stdout
    old = re.search(r"theorem PEqualNP\.Outside\.(L_meta_\d+) :", src).group(1)
    otstr = re.search(r"Nat\.testBit \((\d+ \* 2 \^ 32 \+ \d+)\)", src).group(1)
    src = src.replace(old, sid).replace(otstr, tstr)
    def sub(pat, new):
        nonlocal src
        assert len(re.findall(pat, src, re.M)) == 1, pat
        src = re.sub(pat, lambda _: new, src, flags=re.M)
    B = {0: I["AA"], 1: I["HX"], 2: I["HY"], 11: I["TG"], **{3 + i: I["raw"][i] for i in range(6)}}
    for k, v in B.items(): sub(r"^def bigNat_%d : Nat := .*$" % k, "def bigNat_%d : Nat := %s" % (k, big(v)))
    sub(r"^def NN0 : Nat := \d+$", "def NN0 : Nat := %d" % I["NN"])
    sub(r"^def segsX0 : List \(ℕ × ℕ\) := .*$", "def segsX0 : List (ℕ × ℕ) := %s" % str(I["segX"]))
    sub(r"^def segsY0 : List \(ℕ × ℕ\) := .*$", "def segsY0 : List (ℕ × ℕ) := %s" % str(I["segY"]))
    for k in (1, 2, 3): sub(r"^def rt%d : List \(ℕ × ℕ\) := .*$" % k, "def rt%d : List (ℕ × ℕ) := %s" % (k, rl(k)))
    sub(r"^def f \(x : Fin 6 → Bool\) : Bool := .*$", "def f (x : Fin 6 → Bool) : Bool := " + " || ".join(mono(m, lambda i: "x %d" % i) for m in I["mins"]))
    sub(r"^def EF : ℕ := .*$", "def EF : ℕ := " + " ||| ".join(mono(m, lambda i: "rawP0.getD %d 0" % i).replace("&&", "&&&") for m in I["mins"]))
    sub(r"^def onWit : List Gate := .*$", "def onWit : List Gate := [%s]" % ", ".join("⟨.%s, [%d, %d]⟩" % g for g in gates))
    if "--diag" in sys.argv:   # one kernel check per rt entry, so a failing one is named by its line (sol_fit.py)
        prev = {3: "[]", 2: "rt3", 1: "rt3 ++ rt2"}
        for k in (3, 2, 1):
            ex = "".join("set_option maxRecDepth 100000 in\nset_option maxHeartbeats 0 in\nexample : okE [] (pr (%s) %d) (%d, %d) = true := by decide +kernel -- RT %d %d\n"
                         % (prev[k], Z, Z, rt[Z], Z, rt[Z]) for Z in Zs if bin(Z).count("1") == k)
            anchor = re.search(r"^lemma i%d : .*$" % k, src, re.M).group(0)
            src = src.replace(anchor, anchor + "\n" + ex, 1)
    hdr = ("-- Engine copied verbatim from the merged %s by David Li (GitHub dli7319, open-goat/pequalnp-proofs#%s);\n" % (tid, pr) +
           "-- only the instance data, restriction bounds, target and witness are regenerated for this table (fleet-tools/sol_gen.py).\n")
    src = src.replace("import PEqualNP.Defs\n", "import PEqualNP.Defs\n" + hdr, 1)
    open(outp, "w", encoding="utf-8").write(src)
    print("wrote %s: NN=%d, M=%d, %d rt entries, %d bytes" % (outp, I["NN"], M, len(rt), len(src.encode())))

if __name__ == "__main__":
    main()
