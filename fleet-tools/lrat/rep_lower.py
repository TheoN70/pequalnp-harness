"""Lean proof of a one-a-side promise lower bound, `¬ RepSizeAtMost (fun (u : Fin n) (v : Fin m) => (M : ℕ).testBit
(m * u.val + v.val)) s` (no AND/OR circuit of <= s gates represents the graph), by cube and conquer on LRAT.

Usage: python3 -I rep_lower.py <worktree> <n> <m> <M> <s> <out.lean> [--module MOD] [--cores K] [-m 2G] [--work DIR]

The library does the logic (pequalnp-proofs, PEqualNP.Library.LRAT.PromiseCube): `enc2_cover` says the
enc2CubeCount (n+m) s = 3(n+m+s) cubes `enc2Cube` (first source x operation of the last gate) cover every assignment,
and `rep_lower_mask_of_cubes` turns "every piece enc2 (n+m) s (gMask n m M) (repRows n m) ++ enc2Cube k is UNSAT"
into the bound. This script:
  1. has Lean dump that formula and the cubes (so the CNF is Lean's, clause for clause);
  2. refutes each piece with the toolchain's CaDiCaL (--lrat), K at a time on cores from `fleet-tools/slots`, each
     under capmem; restart-safe (pieces with a .lrat and rc 20 are kept in --work, default <out>.d/);
  3. packs each proof (lrat2lean.py) and writes one theorem per cube, the case split over k and the bound.
Exit 3 if a piece is SAT: a circuit of <= s gates exists, the bound is false.
The file imports PEqualNP.Library.LRAT.PromiseCube: fine only for a step whose imports allow it. Then check it with
`tools/pnp.sh check` (the 512 KiB limit and the checker's 20 min decide: a warning is printed above 512 KiB).
The worktree needs the LRAT oleans (`build_lib.sh --check`).
"""
import os, subprocess, sys, time

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, HERE)
from lrat2lean import convert, lean_list, pack, read_cnf

MAX_BYTES = 512 * 1024


def lean_env(wt, *cmd):
    return subprocess.run(["lake", "env", *cmd], cwd=os.path.join(wt, "lean"), capture_output=True, text=True)


def dump(wt, n, m, M, s, d):
    src = os.path.join(d, "dump.lean")
    open(src, "w").write(f"""import PEqualNP.Library.LRAT.PromiseCube
open PEqualNP.Defs.LratEncoding PEqualNP.Library.LRAT.Promise
def F : List (List ℕ) := enc2 {n + m} {s} (gMask {n} {m} {M}) (repRows {n} {m})
def lit (l : ℕ) : Int := if l % 2 == 0 then ((l / 2 : ℕ) : Int) else -((l / 2 : ℕ) : Int)
def line (c : List ℕ) : String := " ".intercalate (c.map (fun l => toString (lit l))) ++ " 0"
#eval do
  let mx := F.foldl (fun (m : ℕ) (c : List ℕ) => c.foldl (fun (m l : ℕ) => max m (l / 2)) m) 0
  let h ← IO.FS.Handle.mk "{d}/base.cnf" .write
  h.putStrLn s!"p cnf {{mx}} {{F.length}}"
  for c in F do h.putStrLn (line c)
  let g ← IO.FS.Handle.mk "{d}/cubes.txt" .write
  for k in List.range (enc2CubeCount {n + m} {s}) do
    g.putStrLn (" ;; ".intercalate ((enc2Cube {n + m} {s} k).map line))
""")
    r = lean_env(wt, "lean", src)
    if r.returncode:
        sys.exit(f"Lean dump failed:\n{r.stdout[-2000:]}{r.stderr[-2000:]}")
    return [l.rstrip("\n").split(" ;; ") for l in open(os.path.join(d, "cubes.txt"))]


def piece(d, k, base, cube):
    p = os.path.join(d, f"p{k}.cnf")
    hdr, body = base.split("\n", 1)
    _, _, nv, nc = hdr.split()
    nv = max([int(nv)] + [abs(int(x)) for c in cube for x in c.split()[:-1]])
    open(p, "w").write(f"p cnf {nv} {int(nc) + len(cube)}\n{body}" + "".join(c + "\n" for c in cube))
    return p


def solve_all(wt, d, cubes, ncores, mem):
    r = subprocess.run(["elan", "which", "lean"], cwd=os.path.join(wt, "lean"), capture_output=True, text=True)
    cad = os.path.join(os.path.dirname(r.stdout.strip()), "cadical")
    base = open(os.path.join(d, "base.cnf")).read()
    done = lambda k: os.path.exists(os.path.join(d, f"p{k}.ok"))
    todo = [k for k in range(len(cubes)) if not done(k)]
    if not todo:
        return
    got = subprocess.run([os.path.join(HERE, "..", "slots"), str(min(ncores, len(todo)))], capture_output=True, text=True)
    if got.returncode:
        sys.exit(got.stderr.strip())
    cores = [c for part in got.stdout.strip().split(",") for c in range(int(part.split("-")[0]), int(part.split("-")[-1]) + 1)]
    print(f"{len(todo)} of {len(cubes)} pieces to refute on cores {got.stdout.strip()}", flush=True)
    live, free, t0 = {}, list(cores), time.time()
    while todo or live:
        while todo and free:
            k, c = todo.pop(0), free.pop(0)
            p = piece(d, k, base, cubes[k])
            q = subprocess.Popen(["taskset", "-c", str(c), os.path.join(HERE, "..", "capmem"), "-m", mem, cad, "-q",
                                  "--lrat", "--binary=false", p, os.path.join(d, f"p{k}.lrat")],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            live[k] = (q, c)
        time.sleep(0.5)
        for k, (q, c) in list(live.items()):
            if q.poll() is None:
                continue
            del live[k]; free.append(c)
            if q.returncode == 10:
                for o, _ in live.values():
                    o.terminate()
                print(f"piece {k} is SAT: a circuit of <= s gates exists, the bound is false", file=sys.stderr)
                sys.exit(3)
            if q.returncode != 20:
                sys.exit(f"piece {k}: cadical exit {q.returncode} (memory cap? raise -m)")
            open(os.path.join(d, f"p{k}.ok"), "w").close()
    print(f"all {len(cubes)} pieces UNSAT in {time.time() - t0:.0f} s", flush=True)


def write_lean(d, n, m, M, s, cubes, out, mod):
    N, cnt = n + m, len(cubes)
    certs, thms = [], []
    for k in range(cnt):
        fk, toks = convert(read_cnf(os.path.join(d, f"p{k}.cnf")), os.path.join(d, f"p{k}.lrat"))
        W = max(max(fk), max(toks)).bit_length()
        certs.append(f"def c{k}_W : Nat := {W}\n" + lean_list(f"c{k}_Kw", pack(fk, W)) + lean_list(f"c{k}_Pw", pack(toks, W)))
        thms.append(f"set_option maxRecDepth 1000000 in\nset_option maxHeartbeats 0 in\n"
                    f"theorem u{k} : ¬ FormulaSat (F ++ enc2Cube {N} {s} {k}) :=\n"
                    f"  PEqualNP.Library.LRAT.checkW_sound _ (PEqualNP.Library.LRAT.unpack c{k}_W c{k}_Kw) c{k}_W c{k}_Pw "
                    f"(by decide +kernel)\n")
    arms = "\n".join(f"  | {k}, _ => exact u{k}" for k in range(cnt))
    stmt = f"¬ PEqualNP.Represents.RepSizeAtMost (fun (u : Fin {n}) (v : Fin {m}) => ({M} : ℕ).testBit ({m} * u.val + v.val)) {s}"
    text = f"""import PEqualNP.Defs
import PEqualNP.Library.LRAT.PromiseCube

namespace {mod}

open PEqualNP.Defs.LratEncoding PEqualNP.Library.LRAT.Promise

/-- The AND/OR encoding of "some circuit of at most {s} gates represents the graph", on its {n * m} promise rows. -/
def F : List (List ℕ) := enc2 {N} {s} (gMask {n} {m} {M}) (repRows {n} {m})

{chr(10).join(certs)}
{chr(10).join(thms)}
theorem cubes : ∀ k < enc2CubeCount {N} {s}, ¬ FormulaSat (F ++ enc2Cube {N} {s} k) := by
  intro k hk
  have hk' : k < {cnt} := by simpa [enc2CubeCount] using hk
  match k, hk' with
{arms}
  | _ + {cnt}, h => omega

end {mod}

theorem {mod} : {stmt} :=
  PEqualNP.Library.LRAT.Promise.rep_lower_mask_of_cubes {n} {m} {M} {s} (by decide) {mod}.cubes
"""
    open(out, "w").write(text)
    b = len(text.encode())
    print(f"wrote {out}: {cnt} cubes, {b:,} bytes" + ("  WARNING > 512 KiB, the desk will refuse it" if b > MAX_BYTES else ""))


def main(a):
    opt = {"--module": "RepLowerTest", "--cores": "14", "-m": "2G", "--work": None}
    pos = []
    while a:
        x = a.pop(0)
        if x in opt:
            opt[x] = a.pop(0)
        else:
            pos.append(x)
    if len(pos) != 6:
        sys.exit(__doc__)
    wt, out = os.path.abspath(pos[0]), os.path.abspath(pos[5])
    n, m, M, s = map(int, pos[1:5])
    if s < 1:
        sys.exit("s must be >= 1 (the cubes split the last gate)")
    d = os.path.abspath(opt["--work"] or out + ".d")
    os.makedirs(d, exist_ok=True)
    cubes = dump(wt, n, m, M, s, d)
    solve_all(wt, d, cubes, int(opt["--cores"]), opt["-m"])
    write_lean(d, n, m, M, s, cubes, out, opt["--module"])


if __name__ == "__main__":
    main(sys.argv[1:])
