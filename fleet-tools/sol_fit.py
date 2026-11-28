#!/usr/bin/env python3
"""sol_fit.py: run sol_gen.py, compile, lower the restriction bounds the kernel rejects, repeat; then the final file.

usage: python3 -I sol_fit.py <lease.json> <out.lean> [--clone DIR] [--tries N] [--core C]
Each compile: `lake env lean` in <clone>/lean (default $PENP/pequalnp-proofs), under capmem -m 6G and master/heavy.lock,
pinned to one core (default: fleet-tools/slots 1 --range 8-13). Exit 0 when the final file compiles with no error.
"""
import os, re, subprocess, sys

HERE = os.path.dirname(os.path.realpath(__file__))
PENP = os.path.join(HERE, "..", "..")
arg = lambda k, d: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
lease, out = sys.argv[1:3]
clone = arg("--clone", os.path.join(PENP, "pequalnp-proofs"))
tries = int(arg("--tries", "6"))

def compile_(path):
    core = arg("--core", None) or subprocess.run([os.path.join(HERE, "slots"), "1", "--range", "8-13"],
                                                 capture_output=True, text=True).stdout.strip() or "13"
    r = subprocess.run(["flock", os.path.join(PENP, "master", "heavy.lock"), "taskset", "-c", core,
                        os.path.join(HERE, "capmem"), "-m", "6G", "-t", "25m", "lake", "env", "lean", os.path.abspath(path)],
                       cwd=os.path.join(clone, "lean"), capture_output=True, text=True)
    errs = [int(m) for m in re.findall(r"^\S+?:(\d+):\d+: error", r.stdout + r.stderr, re.M)]
    return r.returncode, errs, (r.stdout + r.stderr)[-2000:]

def gen(extra):
    cmd = [sys.executable, "-I", os.path.join(HERE, "sol_gen.py"), lease, out, "--clone", clone] + extra
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode: sys.exit(r.stderr or r.stdout)
    print(r.stdout.strip(), flush=True)

fix = {}
for k in range(tries):
    rtarg = ["--rt", ",".join("%d:%d" % kv for kv in fix.items())] if fix else []
    gen(rtarg + ["--diag"])
    lines = open(out, encoding="utf-8").read().split("\n")
    rc, errs, tail = compile_(out)
    bad = [re.search(r"-- RT (\d+) (\d+)$", lines[e - 1]) for e in errs if "-- RT " in lines[e - 1]]
    print("try %d: rc=%d, %d errors, %d rt entries rejected: %s" % (k, rc, len(errs), len(bad), [b.groups() for b in bad]), flush=True)
    if not bad: break
    for b in bad: fix[int(b.group(1))] = max(0, int(b.group(2)) - 1)
rtarg = ["--rt", ",".join("%d:%d" % kv for kv in fix.items())] if fix else []
gen(rtarg)
rc, errs, tail = compile_(out)
print("final: rc=%d errors at lines %s" % (rc, errs), flush=True)
if rc or errs: print(tail); sys.exit(1)
print("OK", out, "rt fixes", fix)
