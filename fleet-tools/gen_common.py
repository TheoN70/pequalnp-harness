#!/usr/bin/env python3
"""gen_common.py: shared skeleton for family generators (stdlib only), so a new generator is ~50 lines.

    from gen_common import *
    g = load_lease(sys.argv[1])                    # Gap: id, title, statement, module, imports, sid, file
    m = match(g.statement, r"D\\.size ≤ (\\d+)")    # exit OTHER (3) when the shape is not the family's
    src = template("three_out_49912.lean")         # from fleet-tools/templates/
    src = subst(src, [(old, new), ...])            # each old must occur (count checked), else exit OTHER
    src = set_statement(src, old_id, g, " := by\\n  rintro")   # renames old_id -> g.sid, swaps the theorem statement
    write(out, src)                                # 512 KiB check (exit NOTHING when too big)
    compile_check(out, worktree, heavy=True)       # optional: capmem -m 6G + lake env lean, under master/heavy.lock

Exit codes (autosolve.sh's convention): OK 0 written, NOTHING 2 nothing found / too big, OTHER 3 other family,
FALSE 4 the unit is false. `precheck(cond, code, msg)` exits with code when cond is false.
Self-check: python3 -I gen_common.py --demo (rebuilds three_out_gen.py's output for L-meta-49912 byte for byte).
"""
import json, os, re, subprocess, sys, tempfile
from collections import namedtuple

HERE = os.path.dirname(os.path.realpath(__file__))
PENP = os.path.dirname(os.path.dirname(HERE))
OK, NOTHING, OTHER, FALSE = 0, 2, 3, 4
MAX_BYTES = 512 * 1024
Gap = namedtuple("Gap", "id title statement module imports sid file raw")


def die(code, msg=""):
    if msg: print(msg, file=sys.stderr)
    sys.exit(code)


def precheck(cond, code=OTHER, msg=""):
    """Python pre-check hook: exit with code (OTHER, FALSE, NOTHING) unless cond holds."""
    if not cond: die(code, msg)


def load_lease(path):
    """Lease answer ({"gap": ..., "lease": ...}) or a bare gap JSON. sid = Lean-safe id (L_meta_123)."""
    with open(path, encoding="utf-8") as f: d = json.load(f)
    g = d.get("gap", d) if isinstance(d, dict) else {}
    gid, st = g.get("id"), g.get("statement")
    precheck(isinstance(gid, str) and re.fullmatch(r"[A-Za-z0-9_-]+", gid) and isinstance(st, str), OTHER, "bad lease JSON")
    sid = gid.replace("-", "_")
    return Gap(gid, str(g.get("title", "")), st.strip(), g.get("module") or "PEqualNP.Outside." + sid,
               list(g.get("imports") or []), sid, g.get("file") or "lean/PEqualNP/Outside/%s.lean" % sid, g)


def match(text, pattern, code=OTHER):
    """re.search or exit code (the statement is not of this family)."""
    m = re.search(pattern, text)
    precheck(m, code, "no match: " + pattern)
    return m


def template(name):
    with open(os.path.join(HERE, "templates", name), encoding="utf-8") as f: return f.read()


def subst(src, pairs, code=OTHER):
    """Plain replacements; each old (str) or (old, new, count) must occur, count times when given."""
    for p in pairs:
        old, new, cnt = (p + (None,))[:3]
        n = src.count(old)
        precheck(n and (cnt is None or n == cnt), code, "template: %r found %d times" % (old[:60], n))
        src = src.replace(old, new)
    return src


def set_statement(src, old_id, g, end=" := by", ns="PEqualNP.Outside."):
    """Rename old_id (underscored) to g.sid everywhere, then replace the theorem statement up to `end` by (g.statement)."""
    src = src.replace(old_id, g.sid)
    head = "theorem %s%s : " % (ns, g.sid)
    a = src.index(head); b = src.index(end, a)
    return src[:a] + head + "(%s)" % g.statement + src[b:]


def write(path, text, code=NOTHING):
    size = len(text.encode("utf-8"))
    precheck(size <= MAX_BYTES, code, "file is %d bytes > 512 KiB" % size)
    with open(path, "w", encoding="utf-8") as f: f.write(text)
    return size


def compile_check(path, worktree=os.path.join(PENP, "pequalnp-proofs"), heavy=False, mem="6G", t="25m", rng="0-13"):
    """`lake env lean` in <worktree>/lean on one slots core under capmem; (ok, output tail)."""
    core = subprocess.run([os.path.join(HERE, "slots"), "1", "--range", rng], capture_output=True, text=True).stdout.strip()
    cmd = (["taskset", "-c", core] if core else []) + [os.path.join(HERE, "capmem"), "-m", mem, "-t", t,
                                                       "lake", "env", "lean", os.path.abspath(path)]
    if heavy: cmd = ["flock", os.path.join(PENP, "master", "heavy.lock")] + cmd
    r = subprocess.run(cmd, cwd=os.path.join(worktree, "lean"), capture_output=True, text=True)
    out = r.stdout + r.stderr
    return r.returncode == 0 and not re.search(r": error", out), out[-2000:]


# ---- demo: three_out_gen.py's n=4 path (L-meta-49912 template) in ~25 lines on gen_common ----
def three_out4(lease, out):
    g = load_lease(lease); st = g.statement
    precheck("(p q r : Fin (6+D.size))" in st and "∀ t : Fin 5" in st and st.startswith("¬"))
    T = [int(x) for x in re.findall(r"\((\d+) : Nat\)\.testBit t\.val", st)]
    k, nb = int(match(st, r"D\.size ≤ (\d+)")[1]), int(match(st, r"notCount D ≤ (\d+)")[1])
    precheck(len(set(T)) == 3 and k <= 6)
    sys.path.insert(0, HERE); from three_out_gen import circuit_exists
    precheck(not circuit_exists(T, k, nb, 4), FALSE, "a circuit exists: false")
    tl = "[%s]" % ", ".join(map(str, T))
    src = subst(template("three_out_49912.lean"),
                [("search [5, 17, 22] 6 m0 2 = false", "search %s %d m0 %d = false" % (tl, k, nb)),
                 ("no_circuit [5, 17, 22] (by decide) 6 2 search_false", "no_circuit %s (by decide) %d %d search_false" % (tl, k, nb))])
    write(out, set_statement(src, "L_meta_49912", g, " := by\n  rintro"))


def demo():
    src = template("three_out_49912.lean"); head = "theorem PEqualNP.Outside.L_meta_49912 : ("
    a = src.index(head) + len(head); st = src[a:src.index(" := by\n  rintro", a) - 1]
    cases = [("L-meta-49912", st), ("L-meta-90001", st.replace("D.size ≤ 6", "D.size ≤ 5"))]
    bad = 0
    with tempfile.TemporaryDirectory() as d:
        for gid, s in cases:
            lp = os.path.join(d, "l.json"); json.dump({"gap": {"id": gid, "statement": s}}, open(lp, "w"))
            ref, new = os.path.join(d, "ref.lean"), os.path.join(d, "new.lean")
            subprocess.run([sys.executable, "-I", os.path.join(HERE, "three_out_gen.py"), lp, ref], check=True, capture_output=True)
            r = subprocess.run([sys.executable, "-I", os.path.realpath(__file__), "--three-out4", lp, new])
            same = r.returncode == 0 and open(ref, "rb").read() == open(new, "rb").read()
            print("%s: %s" % (gid, "byte-identical" if same else "DIFFERENT (rc %d)" % r.returncode)); bad += not same
    print("demo:", "OK" if not bad else "FAIL"); sys.exit(1 if bad else 0)


if __name__ == "__main__":
    if sys.argv[1:2] == ["--demo"]: demo()
    elif sys.argv[1:2] == ["--three-out4"]: three_out4(*sys.argv[2:4])
    else: die(2, __doc__)
