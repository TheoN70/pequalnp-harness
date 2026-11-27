"""Cube and conquer for one hard CNF: split it into 2^K cubes, solve them one per free core, restart-safe.

  python3 -I cube.py split <f.cnf> <K> <dir> [--vars 12,40,...]   write dir/body.cnf (one copy) + dir/cubes.txt
  python3 -I cube.py run <dir> <cores> [-m 2G] [--lrat]             solve the cubes without an `s ` line, <cores> at once
  python3 -I cube.py status <dir>                                   counts, and the SAT cube if any

Split: cube i fixes the K split variables to the bits of i (2^K cubes, so their union covers every assignment: all
UNSAT = f.cnf UNSAT). Split variables: --vars, else the K variables in the most clauses (a cheap heuristic; pick
structural ones, e.g. the op of the last gates, with --vars when you know them). Cube i is body.cnf + K unit clauses,
streamed to CaDiCaL on stdin, so the disk holds one copy of the formula.
Run: cores come from `slots <cores>` (fails if there is no room), each cube runs as `taskset -c <core> capmem -m <mem>`
with the CaDiCaL of the Lean toolchain (2.1.2, the one whose LRAT replays in Lean; env CADICAL overrides). Results in
dir/c_<i>.out (`s SATISFIABLE` + `v` lines, or `s UNSATISFIABLE`); --lrat also writes dir/c_<i>.lrat (text, as lrat/lower.sh; each proves body + its units UNSAT, a Lean proof still needs
the cover lemma joining the 2^K cubes, not written yet). The first SAT
stops every other cube. Rerun `run` after a crash or reboot: finished cubes are skipped.
ponytail: one cube per core and no re-splitting of a slow cube; split it again by hand (split its body with more K).
"""
import os, signal, subprocess, sys, time
from collections import Counter

HERE = os.path.dirname(os.path.realpath(__file__))
TOOLCHAIN = open(os.path.join(HERE, "../../pequalnp-proofs/lean-toolchain")).read().strip() \
    if os.path.exists(os.path.join(HERE, "../../pequalnp-proofs/lean-toolchain")) else "leanprover/lean4:v4.36.0"
CADICAL = os.environ.get("CADICAL") or os.path.expanduser(
    "~/.elan/toolchains/" + TOOLCHAIN.replace("/", "--").replace(":", "---") + "/bin/cadical")


def read_cnf(path):
    nv = nc = None
    clauses = []
    for line in open(path):
        t = line.split()
        if not t or t[0] == "c":
            continue
        if t[0] == "p":
            nv, nc = int(t[2]), int(t[3]); continue
        clauses.append(line if line.endswith("\n") else line + "\n")
    return nv, nc, clauses


def propagate(cls):
    """Variables fixed by unit propagation from the formula's own clauses (empty set if it hits a conflict: no pruning).
    ponytail: plain repeated passes over the clauses, fine for the few-100k-clause CNFs here; watched literals if slow."""
    val, changed = {}, True
    while changed:
        changed = False
        for c in cls:
            if any(val.get(abs(l)) == (l > 0) for l in c):
                continue
            free = [l for l in c if abs(l) not in val]
            if not free:
                return set()
            if len(free) == 1:
                val[abs(free[0])] = free[0] > 0; changed = True
    return set(val)


def split(cnf, k, d, vars_=None):
    nv, nc, clauses = read_cnf(cnf)
    if vars_ is None:  # the most frequent variables that unit propagation leaves free (L-meta-17390: the top ones were
        fixed = propagate([list(map(int, c.split()[:-1])) for c in clauses])  # symmetry vars fixed by units, 30/32 cubes trivial)
        occ = Counter(abs(int(x)) for c in clauses for x in c.split()[:-1] if abs(int(x)) not in fixed)
        vars_ = [v for v, _ in occ.most_common(k)]
    if len(vars_) != k or len(set(vars_)) != k or not all(1 <= v <= nv for v in vars_):
        sys.exit(f"need {k} distinct split variables in 1..{nv}, got {vars_}")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "body.cnf"), "w") as h:
        h.writelines(clauses)
    with open(os.path.join(d, "cubes.txt"), "w") as h:
        h.write(f"# {cnf}: {nv} variables, {nc} clauses; cube i sets variable vars[b] to bit b of i\n")
        h.write(f"nv {nv}\nnc {nc}\nvars {' '.join(map(str, vars_))}\n")
    print(f"{d}: {2 ** k} cubes on variables {vars_}")


def load(d):
    meta = dict(l.split(None, 1) for l in open(os.path.join(d, "cubes.txt")) if not l.startswith("#"))
    vars_ = list(map(int, meta["vars"].split()))
    return int(meta["nv"]), int(meta["nc"]), vars_


def units(vars_, i):
    return [v if i >> b & 1 else -v for b, v in enumerate(vars_)]


def verdict(d, i):
    try:
        for line in open(os.path.join(d, f"c_{i}.out")):
            if line.startswith("s "):
                return line.split(None, 1)[1].strip()
    except OSError:
        pass
    return None


def status(d):
    _, _, vars_ = load(d)
    v = [verdict(d, i) for i in range(2 ** len(vars_))]
    c = Counter(x or "open" for x in v)
    sat = [i for i, x in enumerate(v) if x == "SATISFIABLE"]
    print(f"{d}: {len(v)} cubes: " + ", ".join(f"{n} {k}" for k, n in sorted(c.items())))
    if sat:
        print(f"SAT in cube {sat[0]}: {d}/c_{sat[0]}.out (units {units(vars_, sat[0])})")
    elif c.get("UNSATISFIABLE") == len(v):
        print("all cubes UNSAT: the formula is UNSAT")
    return c


def run(d, ncores, mem="2G", lrat=False):
    nv, nc, vars_ = load(d)
    if not os.access(CADICAL, os.X_OK):
        sys.exit(f"no CaDiCaL at {CADICAL} (set CADICAL)")
    todo = [i for i in range(2 ** len(vars_)) if verdict(d, i) is None]
    if not todo or any(verdict(d, i) == "SATISFIABLE" for i in range(2 ** len(vars_))):
        return status(d)
    got = subprocess.run([os.path.join(HERE, "slots"), str(ncores)], capture_output=True, text=True)
    if got.returncode:
        sys.exit(got.stderr.strip())
    cores = [c for part in got.stdout.strip().split(",") for c in
             (range(int(part.split("-")[0]), int(part.split("-")[-1]) + 1))]
    body = os.path.abspath(os.path.join(d, "body.cnf"))
    free, live = list(cores), {}  # live: pid -> (Popen, cube, core)
    print(f"{len(todo)} cubes to solve on cores {got.stdout.strip()}", flush=True)
    try:
        while todo or live:
            while todo and free:
                i, core = todo.pop(0), free.pop(0)
                head = f"p cnf {nv} {nc + len(vars_)}\\n" + "".join(f"{u} 0\\n" for u in units(vars_, i))
                proof = f" {os.path.abspath(os.path.join(d, f'c_{i}.lrat'))} --lrat --binary=false" if lrat else ""
                sh = f"{{ printf '{head}'; cat {body}; }} | {CADICAL} -q -{proof}"
                out = open(os.path.join(d, f"c_{i}.out"), "w")
                p = subprocess.Popen(["taskset", "-c", str(core), os.path.join(HERE, "capmem"), "-m", mem,
                                      "sh", "-c", sh], stdout=out, stderr=subprocess.STDOUT, start_new_session=True)
                live[p.pid] = (p, i, core)
            time.sleep(1)
            for pid, (p, i, core) in list(live.items()):
                if p.poll() is None:
                    continue
                del live[pid]; free.append(core)
                v = verdict(d, i)
                print(f"cube {i}: {v or f'no answer (exit {p.returncode})'}", flush=True)
                if v == "SATISFIABLE":
                    todo = []
                    for q, _, _ in live.values():
                        os.killpg(q.pid, signal.SIGTERM)
    finally:  # Ctrl-C or a crash: stop the cubes still running (their .out has no `s ` line: rerun picks them up)
        for q, _, _ in live.values():
            try:
                os.killpg(q.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
    return status(d)


def demo(tmp):
    assert propagate([[1], [-1, 2], [2, 3]]) == {1, 2} and propagate([[1], [-1]]) == set()  # fixed vars, conflict
    # pigeonhole 4 -> 3 (UNSAT): x(p,h) = 3p + h + 1
    x = lambda p, h: 3 * p + h + 1
    cl = [[x(p, h) for h in range(3)] for p in range(4)]
    cl += [[-x(p, h), -x(q, h)] for h in range(3) for p in range(4) for q in range(p + 1, 4)]
    f = os.path.join(tmp, "php.cnf")
    open(f, "w").write(f"c pigeonhole\np cnf 12 {len(cl)}\n" + "".join(" ".join(map(str, c)) + " 0\n" for c in cl))
    split(f, 3, os.path.join(tmp, "php"))
    assert run(os.path.join(tmp, "php"), 2) == Counter({"UNSATISFIABLE": 8})
    assert run(os.path.join(tmp, "php"), 2) == Counter({"UNSATISFIABLE": 8})  # rerun: nothing to do
    # 4 pigeons, 4 holes: SAT
    open(f, "w").write("p cnf 4 1\n1 2 3 4 0\n")
    split(f, 2, os.path.join(tmp, "sat"), [1, 2])
    assert run(os.path.join(tmp, "sat"), 2).get("SATISFIABLE", 0) >= 1
    print("demo ok")


if __name__ == "__main__":
    a = sys.argv[1:]
    mem = a[a.index("-m") + 1] if "-m" in a else "2G"
    if a[:1] == ["--demo"]:
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            demo(t)
    elif a[:1] == ["split"] and len(a) in (4, 6):
        split(a[1], int(a[2]), a[3], list(map(int, a[5].split(","))) if "--vars" in a else None)
    elif a[:1] == ["run"] and len(a) >= 3:
        run(a[1], int(a[2]), mem, "--lrat" in a)
    elif a[:1] == ["status"] and len(a) == 2:
        status(a[1])
    else:
        sys.exit(__doc__)
