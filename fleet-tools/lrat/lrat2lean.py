"""Turn a CaDiCaL LRAT proof of a CNF into the packed certificate of PEqualNP.Library.LRAT.Checker.

Usage: python3 -I lrat2lean.py <formula.cnf> <proof.lrat> <out.lean-fragment> [--name NAME]
The CNF must be the formula exactly as Lean builds it, clause for clause and in order (dump it
with dump_enc2.lean), since `checkW` reads formula clause i under the key given by entry i of fk.

Writes Lean definitions `<NAME>_W`, `<NAME>_Kw` (packed formula keys) and `<NAME>_Pw` (packed
steps); the proof is then `checkW_sound F (unpack W Kw) W Pw (by decide +kernel)`.
Token format (Checker.lean): per step `key lits.. 0 h1 u1 h2 u2 .. hk`, each `u` the literal hint
`h` makes unit, `hk` the falsified hint. Keys are reused after deletions so they stay small.
Literal of DIMACS v: 2v (positive), 2v+1 (negative).
"""
import sys
sys.set_int_max_str_digits(0)  # packed words run to ~5000 digits


def read_cnf(path):
    cls = []
    for line in open(path):
        t = line.split()
        if not t or t[0] in ("c", "p"):
            continue
        xs = list(map(int, t))
        assert xs[-1] == 0, "one clause per line expected"
        cls.append(xs[:-1])
    return cls


def L(d):
    return 2 * d if d > 0 else 2 * (-d) + 1


def trim(lrat):
    """Keep only the steps the empty clause depends on (backward pass); deletions are recomputed:
    a clause's key is freed right after its last use, so keys stay small."""
    steps = []
    for line in open(lrat):
        t = line.split()
        if len(t) > 1 and t[1] != "d":
            xs = list(map(int, t[1:])); z = xs.index(0)
            steps.append((int(t[0]), xs[:z], xs[z + 1:-1]))
            if z == 0:
                break
    need = {steps[-1][0]}
    keep = []
    for cid, lits, hints in reversed(steps):
        if cid in need:
            keep.append((cid, lits, hints)); need.update(hints)
    keep.reverse()
    last = {}
    for i, (cid, lits, hints) in enumerate(keep):
        for h in hints:
            last[h] = i
    out = []
    for i, (cid, lits, hints) in enumerate(keep):
        out.append(f"{cid} {' '.join(map(str, lits + [0] + hints + [0]))}")
        dead = [h for h in hints if last[h] == i]
        if dead:
            out.append(f"{cid} d {' '.join(map(str, dead))} 0")
    return out


def convert(cnf, lrat):
    neg = lambda l: l ^ 1
    clause = {}            # LRAT id -> frozenset of Lean literals
    key = {}               # LRAT id -> checker key
    free = []              # keys freed by deletions
    nxt = 0
    def alloc():
        nonlocal nxt
        if free:
            return free.pop()
        nxt += 1
        return nxt - 1
    fk = []
    for i, c in enumerate(cnf, 1):
        clause[i] = frozenset(L(d) for d in c)
        key[i] = alloc()
        fk.append(key[i] + 1)
    toks = []
    done = False
    for line in trim(lrat):
        t = line.split()
        if not t:
            continue
        cid = int(t[0])
        if t[1] == "d":                       # deletion: free the keys (cadical deletes only dead clauses)
            for x in map(int, t[2:-1]):
                if x in key:
                    free.append(key.pop(x)); clause.pop(x, None)
            continue
        xs = list(map(int, t[1:]))
        z = xs.index(0)
        lits, hints = xs[:z], xs[z + 1:-1]
        assert all(h > 0 for h in hints), "RAT hint: not supported by the checker"
        C = frozenset(L(d) for d in lits)
        k = alloc()
        step = [k] + [L(d) for d in lits] + [0]
        Fset = set(C)
        ok = False
        for h in hints:
            D = clause[h]
            rem = [l for l in D if l not in Fset]
            step.append(key[h])
            if not rem:
                ok = True
                break
            assert len(rem) == 1, f"hint {h} of step {cid} is not unit"
            step.append(rem[0])
            Fset.add(neg(rem[0]))
        assert ok, f"step {cid}: no falsified hint"
        toks += step
        clause[cid] = C
        key[cid] = k
        if not C:
            done = True
            break
    assert done, "the proof never derives the empty clause"
    return fk, toks


def pack(toks, W):
    words = []
    for i in range(0, len(toks), 1024):
        part = toks[i:i + 1024]
        w = 1
        for x in reversed(part):
            assert 0 <= x < (1 << W)
            w = (w << W) | x
        words.append(w)
    return words


def lean_list(name, words):
    body = ",\n".join(str(w) for w in words)
    return f"def {name} : List Nat := [\n{body}]\n"


if __name__ == "__main__":
    cnf, lrat, out = sys.argv[1:4]
    name = sys.argv[sys.argv.index("--name") + 1] if "--name" in sys.argv else "c"
    fk, toks = convert(read_cnf(cnf), lrat)
    W = max(max(fk), max(toks)).bit_length()
    s = f"def {name}_W : Nat := {W}\n" + lean_list(name + "_Kw", pack(fk, W)) + lean_list(name + "_Pw", pack(toks, W))
    open(out, "w").write(s)
    print(f"W={W} formula={len(fk)} tokens={len(toks)} bytes={len(s)}")
