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
TID15, PR15 = "L_meta_36030", "48070"   # NlkIas9, M = 15: all 256 rows, one lemma per restriction, root split in cases
PENP = os.path.join(HERE, "..", "..")
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

def instance(E, rows="true64"):   # rows: the 64 smallest true points (29168) or all 256 points (M = 15 files)
    R = 1 << N; tv = lambda a: any(a >> i & 1 and a >> j & 1 for i, j in E)
    ones = [a for a in range(R) if tv(a)]
    mins = [a for a in ones if all(not tv(a ^ (1 << i)) for i in range(N) if a >> i & 1)]
    maxs = [a for a in range(R) if not tv(a) and all(tv(a | (1 << i)) for i in range(N) if not a >> i & 1)]
    P = set()
    for t in ones:
        P |= {(t, t ^ (1 << i)) for i in range(N) if t >> i & 1 and not tv(t ^ (1 << i))}
        if t in mins: P |= {(t, 0)} | {(t, f) for f in maxs}
    co = [(r, 0, "") for r in (ones[:64] if rows == "true64" else range(R))]
    for t in sorted({t for t, _ in P}):
        co += [(t, f, "A") for (u, f) in sorted(P) if u == t]; co.append((0, 0, "x"))
    for f in sorted({f for _, f in P}):
        co += [(t, f, "A") for (t, g) in sorted(P, key=lambda p: (p[1], p[0])) if g == f]; co.append((0, 0, "y"))
    NN = len(co)
    bits = lambda cond: sum(1 << c for c, x in enumerate(co) if cond(x))
    AA = bits(lambda x: x[2] == "A")
    sp = lambda fl, start: list(zip([start] + [c for c, x in enumerate(co) if x[2] == fl][:-1], [c for c, x in enumerate(co) if x[2] == fl]))
    segX = sp("x", (64 if rows == "true64" else R) - 1)
    return dict(NN=NN, AA=AA, HX=bits(lambda x: x[2] == "x"), HY=bits(lambda x: x[2] == "y"), TG=AA | bits(lambda x: x[2] == "" and tv(x[0])),
                raw=[sum(((a >> i & 1) << c) | ((b >> i & 1) << (NN + c)) for c, (a, b, _) in enumerate(co)) for i in range(N)],
                segX=segX, segY=sp("y", segX[-1][1]))

def nest(items, op):
    return items[0] if len(items) == 1 else "(%s %s %s)" % (items[0], op, nest(items[1:], op))

def forms(E):
    return (nest(["(x %d && x %d)" % e for e in E], "||"), nest(["(b%d && b%d)" % e for e in E], "||"),
            nest(["(rawP.getD %d 0 &&& rawP.getD %d 0)" % e for e in E], "|||"))

def lsg_witness(edges, G, secs=20, core=None):
    core = core or str(min(os.sched_getaffinity(0)))   # the caller's core (autosolve pins one with taskset)
    args = [str(x) for e in edges for x in e]
    o = subprocess.run(["taskset", "-c", core, os.path.join(HERE, "lsg"), str(G), "1", str(secs), str(N)] + args,
                       capture_output=True, text=True).stdout
    gs = re.findall(r"^w(\d+) = (AND|OR)\(w(\d+),w(\d+)\)", o, re.M)
    if not gs: return None
    assert int(gs[0][0]) == N and len(gs) == G
    return [(op.lower(), int(a), int(b)) for _, op, a, b in gs]

def lsg_size(edges, hi=16, secs=3, core="13"):
    best = None
    for G in range(hi, 0, -1):
        if lsg_witness(edges, G, secs, core): best = G
        else: break
    return best

def compile_(path, clone, mem="6G", t="25m"):   # M = 15 files peak at 6.74 GB (upstream 36030): mem="8G", still one at a time (heavy.lock)
    core = subprocess.run([os.path.join(HERE, "slots"), "1", "--range", "8-13"], capture_output=True, text=True).stdout.strip() or "13"
    r = subprocess.run(["flock", os.path.join(PENP, "master", "heavy.lock"), "taskset", "-c", core, os.path.join(HERE, "capmem"),
                        "-m", mem, "-t", t, "lake", "env", "lean", os.path.abspath(path)], cwd=os.path.join(clone, "lean"),
                       capture_output=True, text=True)
    return r.returncode, [int(m) for m in re.findall(r"^\S+?:(\d+):\d+: error", r.stdout + r.stderr, re.M)]

def flat(E, a, op):
    return (" %s " % op).join(a % e for e in E)

SHARDS = [(0xfff << (12 * k), 0) for k in range(17)] + [(0xf << (12 * 17), 0), (0x3f << (12 * 17 + 4), 1)]   # covers MM = 214 buckets

def sharded_floor():
    """baseFloor (Imp [] 0 14) cut into one kernel check per (t, shard): one decide of the whole floor ran past 8 GB on
    33565 (bisected). Same shards and combination as RobinAllenson's L-meta-52262 (#56653), here for every t < 14."""
    opt = "set_option maxRecDepth 100000 in\nset_option maxHeartbeats 0 in\n"
    sh = ", ".join("(0x%x,%d)" % p for p in SHARDS)
    L = ["def fullShards : List (ℕ × ℕ) := [%s]" % sh, opt + "lemma fullShardsCover : mFull fullShards = true := by decide +kernel", "",
         "noncomputable def baseChk (t : ℕ) (p : ℕ × ℕ) : Bool := !chk [] (pr P1 0) 0 13 t p.1 p.2"]
    for t in range(14):
        for k, p in enumerate(SHARDS):
            L.append(opt + "lemma base%d_%d : baseChk %d (0x%x,%d) = true := by decide +kernel" % (t, k, t, p[0], p[1]))
        L.append("lemma baseAll_%d : ∀ p ∈ fullShards, baseChk %d p = true := by\n  intro p hp\n"
                 "  simp only [fullShards, List.mem_cons, List.not_mem_nil, or_false] at hp\n  rcases hp with %s\n%s"
                 % (t, t, " | ".join(["rfl"] * len(SHARDS)), "\n".join("  · exact base%d_%d" % (t, k) for k in range(len(SHARDS)))))
    L.append(opt + "lemma baseFloor : Imp [] 0 14 := by\n"
             "  refine imp_of (E := []) (Q := pr P1 0) (Z := 0) (L := 14) (Or.inl rfl) (by decide +kernel) (by decide)\n"
             "    (fun e he => P1ok e (List.mem_of_mem_filter he)) (Or.inr fun t ht => ?_)\n  interval_cases t\n" +
             "\n".join("  · exact ⟨fullShards, fullShardsCover, fun p hp => by simpa only [baseChk, Bool.not_eq_true'] using baseAll_%d p hp⟩" % t for t in range(14)) + "\n")
    return "\n".join(L) + "\n"

def main15(g, E, lit, outp, clone, gates):
    """M = 15: template 36030; bounds start at lsg sizes of G - Z, each rejected p_Z / g_Z lowered by one (up to 6 compiles)"""
    from concurrent.futures import ThreadPoolExecutor
    Zs = [Z for Z in range(1, 256) if bin(Z).count("1") <= 3]
    subs = {Z: [e for e in E if not (Z >> e[0] & 1 or Z >> e[1] & 1)] for Z in Zs}
    if not all(subs.values()): print("a restriction loses every edge: not the template's 92 masks", file=sys.stderr); sys.exit(3)
    def bound(i, Z):   # an overshoot makes its okE check search until it runs out of memory (36030: OOM at 8G), so
        core = str(8 + i % 6)   # exact liveg when it ends in 20 s, else the best of two lsg seeds at 10 s per level
        es = ",".join("%d-%d" % e for e in subs[Z])
        try:
            o = subprocess.run(["taskset", "-c", core, os.path.join(HERE, "liveg"), str(N), es, "0", "0", "0", "16", "26"],
                               capture_output=True, text=True, timeout=20).stdout
            m = re.findall(r"N=(\d+) FOUND", o)
            if m: return int(m[0])
        except subprocess.TimeoutExpired: pass
        best = lsg_size(subs[Z], secs=10, core=core)
        for G in range(best - 1, 0, -1):
            o = subprocess.run(["taskset", "-c", core, os.path.join(HERE, "lsg"), str(G), "2", "10", str(N)] + [str(x) for e in subs[Z] for x in e],
                               capture_output=True, text=True).stdout
            if re.search(r"^w\d+ =", o, re.M): best = G
            else: break
        return best
    with ThreadPoolExecutor(2) as ex:   # liveg peaks ~2.2 GB: two at once fit the 5G scope autosolve gives this run
        sz = list(ex.map(lambda iz: bound(*iz), enumerate(Zs)))
    # one less on single-vertex restrictions: the kernel search cannot always prove their exact size (36030 proves 12 where
    # liveg gives 13 for Z = 4), and an unprovable bound costs more than 8 GB before it fails
    down = int(os.environ.get("SOL_DOWN", "1"))   # lower by one every bound with |Z| <= SOL_DOWN
    sz = [v - (bin(Z).count("1") <= down) for Z, v in zip(Zs, sz)]
    rt = dict(zip(Zs, sz))
    if os.environ.get("RT_FROM"):   # test: take the bounds of a merged file (Lean source path)
        rt.update({int(z): int(l) for z, l in re.findall(r"^lemma p_(\d+) : Imp \[\] \d+ (\d+) :=", open(os.environ["RT_FROM"]).read(), re.M)})
    I = instance(E, rows="all")
    tpl = subprocess.run(["git", "-C", clone, "show", "upstream/main:lean/PEqualNP/Outside/%s.lean" % TID15],
                         capture_output=True, text=True, check=True).stdout
    oldlit = re.search(r"decide \(∃ i < \((\[[\d, ]+\]) : List ℕ\)", tpl).group(1)
    OL = [int(x) for x in oldlit[1:-1].split(",")]; OE = [(OL[2 * k], OL[2 * k + 1]) for k in range(len(OL) // 2)]
    sid = g["id"].replace("-", "_")
    def render():
        src = tpl
        for a, op in (("(x %d && x %d)", "||"), ("(rawP.getD %d 0 &&& rawP.getD %d 0)", "|||"), ("(b%d && b%d)", "||")):
            if flat(OE, a, op) in src: src = src.replace(flat(OE, a, op), flat(E, a, op))
        src = src.replace(oldlit, lit).replace(TID15, sid)
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
        sub(r"^def CC : List PEqualNP\.CircuitLowerBounds\.Gate := .*$",
            "def CC : List PEqualNP.CircuitLowerBounds.Gate := [%s]" % ", ".join("⟨.%s, [%d, %d]⟩" % gg for gg in gates))
        src = re.sub(r"Imp \[\] (\d+) (\d+) :=", lambda m: "Imp [] %s %d :=" % (m.group(1), rt[int(m.group(1))]) if int(m.group(1)) in rt else m.group(0), src)
        src = re.sub(r"\(e := \((\d+),(\d+)\)\)", lambda m: "(e := (%s,%d))" % (m.group(1), rt[int(m.group(1))]) if int(m.group(1)) in rt else m.group(0), src)
        src = re.sub(r"HasGrade 1 \((\d+),(\d+)\) :=", lambda m: "HasGrade 1 (%s,%d) :=" % (m.group(1), rt[int(m.group(1))]), src)
        src = re.sub(r"^(def [PG][123] : List \(ℕ × ℕ\) := \[)([^\]]*)\]", lambda m: m.group(1) + ", ".join(
            "(%s, %d)" % (z, rt[int(z)]) for z in re.findall(r"\((\d+), \d+\)", m.group(2))) + "]", src, flags=re.M)
        old_bf = ("lemma baseFloor : Imp [] 0 14 :=\n  imp_okE (e := (0,14)) (Q := pr P1 0) (Or.inl rfl) (by decide +kernel)\n"
                  "    (fun e he => P1ok e (List.mem_of_mem_filter he))\n")
        if os.environ.get("SOL_ONE_FLOOR") is None:
            assert src.count(old_bf) == 1
            src = src.replace(old_bf, sharded_floor())
        hdr = ("-- Engine and case split copied verbatim from the merged %s by NlkIas9 (open-goat/pequalnp-proofs#%s);\n"
               "-- root floor split into shards as in NlkIas9's merged L-meta-51780 (open-goat/pequalnp-proofs#56612)\n"
               "-- and RobinAllenson's L-meta-52262 (open-goat/pequalnp-proofs#56653);\n"
               "-- only the instance data, restriction bounds, graph and witness are regenerated (fleet-tools/onenot_sol_gen.py).\n" % (TID15, PR15))
        return src.replace("import PEqualNP.Defs\n", "import PEqualNP.Defs\n" + hdr, 1)
    if os.environ.get("NO_COMPILE"):   # write the file only (measurements)
        open(outp, "w", encoding="utf-8").write(render()); print("wrote %s (not compiled)" % outp); return
    # pre-check (Orchestrator 2026-11-28): baseFloor alone, every other heavy check `sorry`; over 8G / 10 min = this unit's floor
    # does not fit (33565: > 8 GB unsharded), exit 3 before the long fit loop. 35422, 32301 pass at 4.4 GB.
    fl, cur = render().split("\n"), None
    for i, l in enumerate(fl):
        m = re.match(r"(?:lemma|theorem) (\w+)", l); cur = m.group(1) if m else cur
        if "decide +kernel" in l and cur and re.match(r"(p_\d+|g_\d+|case_\d+|casesCover)$", cur):
            fl[i] = l.replace("by decide +kernel", "by sorry")
    floorp = outp + ".floor.lean"; open(floorp, "w", encoding="utf-8").write("\n".join(fl))
    rc, errs = compile_(floorp, clone, "8G", "10m"); os.remove(floorp)
    if rc or errs: print("baseFloor pre-check failed (rc=%d, %d errors): floor too heavy for 8G" % (rc, len(errs)), file=sys.stderr); sys.exit(3)
    for k in range(6):
        src = render(); open(outp, "w", encoding="utf-8").write(src)
        rc, errs = compile_(outp, clone, "8G")
        lines = src.split("\n"); bad = set()
        for e in errs:
            z = next((int(m.group(1)) for l in reversed(lines[:e]) for m in [re.match(r"lemma [pg]_(\d+) :", l)] if m), None)
            if z is None or z not in rt: print("error at line %d outside a restriction lemma" % e, file=sys.stderr); sys.exit(2)
            bad.add(z)
        print("try %d: rc=%d, %d errors, lowered %s" % (k, rc, len(errs), sorted(bad)), flush=True)
        if rc and not errs: print("compile killed (rc=%d: 137 = over capmem 6G, 143 = SIGTERM), not a proof error" % rc, file=sys.stderr); sys.exit(2)
        if rc == 0 and not errs:
            print("wrote %s: NN=%d, M=15 (compiled), %d bytes" % (outp, I["NN"], len(src.encode()))); return
        for z in bad: rt[z] -= 1
    sys.exit(2)

def main():
    leasep, outp = sys.argv[1:3]
    clone = sys.argv[sys.argv.index("--clone") + 1] if "--clone" in sys.argv else os.path.join(HERE, "..", "..", "pequalnp-proofs")
    g = json.load(open(leasep))["gap"]; st = g["statement"]
    m = re.search(r"\(\[([\d, ]+)\] : List ℕ\)", st)
    if not ("Fin 8 → Bool" in st and "GateOp.not → i = j" in st and m) or st.lstrip().startswith("¬"): sys.exit(3)
    lit = "[%s]" % m.group(1); L = [int(x) for x in m.group(1).split(",")]
    E = [(L[2 * k], L[2 * k + 1]) for k in range(len(L) // 2)]
    if "--triage" in sys.argv:   # cheap, outside any lock (autosolve): exit 0 = M = 15 by lsg (15 found, 14 not), else 3
        w15 = lsg_witness(E, 15, 30)
        sys.exit(0 if w15 and not lsg_witness(E, 14, 30) else 3)
    if "--gates" in sys.argv:
        gates = [(o, a, b) for o, (a, b) in json.loads(sys.argv[sys.argv.index("--gates") + 1])]; M = len(gates)
    else:   # lsg first (seconds): 15 goes to the M = 15 template; 14 or less to liveg for the exact size
        M = 16 if lsg_witness(E, 16, 10) else None
        for G in (15, 14):
            w = lsg_witness(E, G, 30)
            if not w: break
            M, gates = G, w
        if M != 15: M, gates = liveg(E)
    if M == 15: return main15(g, E, lit, outp, clone, gates)
    if M != TPL_M: print("M = %s; templates prove M = 14 or 15 only" % M, file=sys.stderr); sys.exit(3)
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
