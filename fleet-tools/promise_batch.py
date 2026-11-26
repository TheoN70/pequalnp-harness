"""Triage a family of one-a-side promise steps (`RepSizeAtMost (fun (u : Fin n) (v : Fin m) => (mask : ℕ).testBit
(m * u.val + v.val)) s`) without a lease: for each mask, is there an AND/OR circuit of <= s gates on the n*m promise rows?

Usage: fleet-tools/sat-venv/bin/python -I promise_batch.py --one-a-side <n> <m> <mask>:<s> ... [-d outdir]
  prints one line per mask: `<mask>:<s> SAT <gates> gates -> <outdir>/rep_<mask>_<s>.json` or `<mask>:<s> UNSAT`.
  The JSON feeds circuit2lean.py (a lease of that step + the circuit -> the Lean proof).

SAT is a real circuit (checked on every promise row). UNSAT is triage, not a Lean proof: it is circsat's enc2 with NOT
forbidden, whose gates read exactly two wires; a fan-in-0/1 gate of `Monotone2` (constant or copy) never helps except
for a constant output, which this reports separately. CaDiCaL runs in this process: one core, cap it with capmem.
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import json
from circsat import solve
from circuit2lean import check_rows, one_a_side


def triage(n, m, mask, s):
    """('SAT', circuit) / ('UNSAT', None) / ('CONST', None) for an empty or complete graph."""
    rows = one_a_side(n, m, mask)
    if all(v for _, v in rows) or not any(v for _, v in rows):
        return "CONST", None  # repSize 0 (empty) or 1 (complete: one AND gate reading nothing)
    table = sum(1 << r for r, v in rows if v)
    c = solve(n + m, s, table, [r for r, _ in rows], no_not=True)
    if c is None:
        return "UNSAT", None
    check_rows(c, rows)
    return "SAT", c


def main(argv):
    out, args = ".", argv[1:]
    if "-d" in args:
        i = args.index("-d"); out = args[i + 1]; del args[i:i + 2]
    if len(args) < 4 or args[0] != "--one-a-side":
        sys.exit(__doc__)
    n, m = int(args[1]), int(args[2])
    os.makedirs(out, exist_ok=True)
    for spec in args[3:]:
        mask, s = map(int, spec.split(":"))
        res, c = triage(n, m, mask, s)
        if res == "SAT":
            path = os.path.join(out, f"rep_{mask}_{s}.json")
            json.dump(c, open(path, "w"))
            print(f"{spec} SAT {len(c['gates'])} gates -> {path}", flush=True)
        else:
            print(f"{spec} {res}" + (" (empty or complete graph: size 0 or 1)" if res == "CONST" else ""), flush=True)


def demo():
    # 2x2 identity matrix (mask 0b1001): u0-v0, u1-v1. Wires u0 u1 v0 v1; AND(u0,v0) OR AND(u1,v1) = 3 gates
    assert triage(2, 2, 0b1001, 2)[0] == "UNSAT" and triage(2, 2, 0b1001, 3)[0] == "SAT"
    # one left vertex joined to everything: the output is wire u0, 0 gates
    assert triage(2, 2, 0b0011, 0)[0] == "SAT"
    assert triage(2, 2, 0b1111, 0)[0] == "CONST"
    print("demo ok")


if __name__ == "__main__":
    demo() if sys.argv[1:] == ["--demo"] else main(sys.argv)
