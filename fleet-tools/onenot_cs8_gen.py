# "One NOT gate saves nothing" on 8 vertices, any M, from the merged CoreSearch engine
# (template e.g. L_meta_29638.lean: restriction tree `one`/`two` + a core refuted by `replay`, NOT free).
# Usage: python3 -I onenot_cs8_gen.py <template.lean> <lease.json> <out.lean> [--gates '<liveg JSON>']
# Without --gates it runs ./liveg for the AND/OR witness. Writes nothing unless the Python replay
# of every kernel check passes. Lean check stays mandatory (pnp.sh check).
import sys, re, json, random, subprocess, functools, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from onenot_cs_replay import replay, sep, M32, GOAL

N = 8
ALL = (1 << 256) - 1

def table(edges):
    t = 0
    for m in range(256):
        if any(m >> a & 1 and m >> b & 1 for a, b in edges): t |= 1 << m
    return t

def bit(f, m): return f >> m & 1
def rs(i, c, f):
    t = 0
    for m in range(256):
        mm = (m | 1 << i) if c else (m & ~(1 << i))
        if bit(f, mm): t |= 1 << m
    return t
def dep(i, f): return any(bit(f, m) != bit(f, m | 1 << i) for m in range(256) if not m >> i & 1)
def const(f): return f == 0 or f == ALL
@functools.lru_cache(maxsize=None)
def relevant(f): return [i for i in range(N) if dep(i, f)]
def not_smp(i, c, f): return dep(i, f) and not const(rs(i, c, f))

def good_at(i, c, f):
    a = next(m for m in range(256) if not m >> i & 1 and bit(f, m) != bit(f, m | 1 << i))
    g = rs(i, c, f)
    b = next(m for m in range(256) if bit(g, m) != bit(g, 0))
    return a, b, 0

# ---- core: 32 (zero-point, one-point) query pairs on the relevant inputs, refuted by replay(n)
def core_cert(f, n, tries=300, seed=1):
    R = relevant(f)
    if len(R) > 6: return None
    pts = [sum(((p >> k) & 1) << R[k] for k in range(len(R))) for p in range(1 << len(R))]
    Z = [m for m in pts if not bit(f, m)]; O = [m for m in pts if bit(f, m)]
    near = [(z, o) for z in Z for o in O if bin(z ^ o).count("1") == 1]
    far = [(z, o) for z in Z for o in O if bin(z ^ o).count("1") > 1]
    rnd = random.Random(seed)
    for t in range(tries):
        ps = list(near)
        rnd.shuffle(ps)
        ps = ps[:32]
        pool = far + near
        while len(ps) < 32: ps.append(rnd.choice(pool))
        cols = [0] * N
        for j, (z, o) in enumerate(ps):
            for v in range(N):
                if z >> v & 1: cols[v] |= 1 << j
                if o >> v & 1: cols[v] |= 1 << (j + 32)
        roots = []
        for v in range(N):
            if cols[v] not in (0, (1 << 64) - 1) and cols[v] not in roots: roots.append(cols[v])
        # sample: f(point j) = goal bit j
        assert all(bit(f, sum((cols[v] >> j & 1) << v for v in range(N))) == (GOAL >> j & 1) for j in range(64))
        if not replay(n, roots): return cols, roots
    return None

CORE_MAX = int(os.environ.get("CORE_MAX", "5"))  # ponytail: 6-input cores cost ~1 min per try in Python
CORE_TRIES = int(os.environ.get("CORE_TRIES", "6"))
@functools.lru_cache(maxsize=None)
def core_ok(f, n):
    if len(relevant(f)) > CORE_MAX: return None
    return core_cert(f, n, tries=CORE_TRIES)

@functools.lru_cache(maxsize=None)
def can(f, v):
    """A plan proving Low v f, or None: ('zero',) | ('core', cert) | ('one', i, c, sub) | ('two', i, sub0, sub1)."""
    if v == 0: return ("zero",)
    R = relevant(f)
    for i in R:
        ok = [not_smp(i, c, f) for c in (0, 1)]
        if all(ok) and v >= 2:
            p0 = can(rs(i, 0, f), v - 2)
            p1 = p0 and can(rs(i, 1, f), v - 2)
            if p1: return ("two", i, p0, p1)
    for i in R:
        for c in (0, 1):
            if not_smp(i, c, f):
                p = can(rs(i, c, f), v - 1)
                if p: return ("one", i, c, p)
    cert = core_ok(f, v - 1)
    return ("core", cert) if cert else None

def fexpr(path):
    e = "(target)"
    for i, c in path: e = "(rs %d %s %s)" % (i, "true" if c else "false", e)
    return e

def ga(i, c, f):
    a, b, d = good_at(i, c, f)
    return "(good_at %d %d %d (by decide +kernel))" % (a, b, d)

def emit(f, v, path, plan):
    """Lean term of type Low v f."""
    k = plan[0]
    if k == "zero": return "(zero _)"
    if k == "core":
        cols, roots = plan[1]
        m = len(roots) * (len(roots) - 1) // 2
        rep = ("(CoreSearch.replay_split (m := %d) (by decide +kernel) (by decide +kernel) "
               "(by intro i hi; interval_cases i <;> decide +kernel))" % m) if m > 0 else "(by decide +kernel)"
        return ("(CoreSearch.lower (n := %d) (f := %s) %s %s (by decide +kernel) (by decide +kernel) "
                "(by unfold CoreSearch.Rep; decide +kernel) %s)" % (v - 1, fexpr(path), cols, roots, rep))
    if k == "two":
        i = plan[1]
        return "(two %d %s %s %s %s)" % (i, ga(i, 0, f), ga(i, 1, f),
            emit(rs(i, 0, f), v - 2, path + [(i, 0)], plan[2]), emit(rs(i, 1, f), v - 2, path + [(i, 1)], plan[3]))
    i, c = plan[1], plan[2]
    return "(one %d %s %s %s)" % (i, "true" if c else "false", ga(i, c, f), emit(rs(i, c, f), v - 1, path + [(i, c)], plan[3]))

def ev(gates, x):
    w = [x >> i & 1 for i in range(N)]
    for op, ins in gates:
        vals = [w[k] for k in ins]
        w.append(int(all(vals)) if op == "and" else int(any(vals)))
    return w[-1]

def liveg(edges, M0=10, M1=16):
    here = os.path.dirname(os.path.abspath(__file__))
    es = ",".join("%d-%d" % e for e in edges)
    for tb in ("26", "27"):   # 2^26 table first, 2^27 when it gives no witness (L-meta-34160)
        out = subprocess.run([os.path.join(here, "liveg"), "8", es, "0", "0", str(M0), str(M1), tb],
                             capture_output=True, text=True).stdout
        if "FOUND" in out: break
    else:
        sys.exit("liveg found no AND/OR witness with %d..%d gates (tables 26, 27): pass --gates" % (M0, M1))
    gs = re.findall(r"w\d+ = (and|or) \[(\d+), (\d+)\]", out.split("FOUND", 1)[1])
    return [(op, [int(a), int(b)]) for op, a, b in gs]

def main():
    tpl, leasep, outp = sys.argv[1:4]
    lease = json.load(open(leasep))
    gap = lease["gap"]
    new_id = gap["id"].replace("-", "_")
    stmt = gap["statement"].strip()
    lst = [int(x) for x in re.search(r"\(\[([\d, ]+)\] : List ℕ\)", stmt).group(1).split(",")]
    edges = [(lst[2 * k], lst[2 * k + 1]) for k in range(len(lst) // 2)]
    assert "Fin 8 → Bool" in stmt and "GateOp.not → i = j" in stmt, "not an 8-vertex one-NOT statement"
    f = table(edges)
    if "--gates" in sys.argv:
        gates = [(g[0], g[1]) for g in json.loads(sys.argv[sys.argv.index("--gates") + 1])]
    else:
        gates = liveg(edges)
    assert all(ev(gates, x) == bit(f, x) for x in range(256)), "witness wrong"
    M = len(gates)
    plan = can(f, M - 1)
    print("witness %d gates, tree for Low %d: %s" % (M, M - 1, "found" if plan else "none"), file=sys.stderr)
    if not plan: sys.exit("no restriction tree + core (<= %d inputs) reaches M-1 = %d" % (CORE_MAX, M - 1))
    term = emit(f, M - 1, [], plan)
    src = open(tpl, encoding="utf-8").read()
    old = re.search(r"namespace PEqualNP\.Outside\.(L_meta_\d+)", src).group(1)
    head = src[:src.index("end CoreSearch")].replace(old, new_id)
    assert "Fin 8" in head
    tgt = " || ".join("(x %d && x %d)" % e for e in edges)
    W = ", ".join("⟨.%s, [%d, %d]⟩" % (op, *ins) for op, ins in gates)
    sets = "set_option maxRecDepth 16000 in\nset_option maxHeartbeats 0 in\n"
    body = stmt[len("∀ x : Fin 8 → Bool, "):] if False else None
    rhs = re.search(r"Circuit\.eval ⟨gates, o⟩ \(List\.ofFn x\) = (decide \(.*?\)\)) →", stmt).group(1)
    tail = (f"end CoreSearch\ndef target : F := fun x => {tgt}\n\n\n{sets}theorem lower : Low {M - 1} target := {term}\n\n"
            f"def witness : List Gate := [{W}]\n\n"
            "theorem witness_ok : ∀ g ∈ witness, (g.op = .and ∨ g.op = .or) ∧ g.inputs.length ≤ 2 := by\n  simp [witness]\n\n"
            f"{sets}theorem witness_eval : ∀ x : X, Circuit.eval ⟨witness, {N + M - 1}⟩ (List.ofFn x) = target x := by\n  decide +kernel\n\n"
            f"{sets}theorem target_eq : ∀ x : X, target x = {rhs.replace('PEqualNP.CircuitLowerBounds.', '')} := by\n  decide +kernel\n\n"
            f"end PEqualNP.Outside.{new_id}\n\nopen PEqualNP.Outside.{new_id} in\ntheorem PEqualNP.Outside.{new_id} :\n{stmt} := by\n"
            f"  intro gates o hg _ he\n  by_cases hs : {M} ≤ gates.length\n"
            f"  · exact ⟨witness, {N + M - 1}, witness_ok, hs, fun x => (witness_eval x).trans (target_eq x)⟩\n"
            "  · exact ⟨gates, o, all_not_not lower gates o hg (by omega)\n"
            "      (fun x => (he x).trans (target_eq x).symm), le_rfl, he⟩\n")
    out = head + tail
    assert len(out.encode()) < 512 * 1024
    open(outp, "w", encoding="utf-8").write(out)
    print("wrote %s (%d bytes), Low %d" % (outp, len(out.encode()), M - 1), file=sys.stderr)

if __name__ == "__main__":
    main()
