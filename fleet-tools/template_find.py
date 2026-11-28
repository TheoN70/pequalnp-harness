#!/usr/bin/env python3
"""template_find.py: merged proofs of the SAME family as a unit, by other handles, on upstream/main (read-only).

usage: python3 -I template_find.py <lease.json | "title"> [--clone DIR] [--all-handles] [-n 3]
  Run `git -C $PENP/pequalnp-proofs fetch upstream main` first (not done here: the tool stays read-only).
  Heavy-ish (git grep over ~30k files, ~30 s on one core): fleet-tools/capmem -m 2G taskset -c "$(fleet-tools/slots 1)" ...
Family key: the theorem statement with every number replaced by N (edge lists, masks, bounds, tables vanish), so
two units match when their statements differ only in data. A title alone is resolved to a statement through any
lease in master/leases/ whose title has the same title key (title_key below, also used by family_watch.py).
Output: both keys, merged count per handle, the n smallest merged files (path, handle, PR, bytes, engine markers),
and the lines that differ between the two smallest (the data a generator must substitute).
"""
import difflib, functools, glob, json, os, re, subprocess, sys
from collections import Counter

HERE = os.path.dirname(os.path.realpath(__file__))
PENP = os.path.join(HERE, "..", "..")
D = "lean/PEqualNP/Outside/"
ME = "TheoN70"
MARKS = ["inductive Sol", "def roots", "CoreSearch", "ForestCore", "Certificate", "LRAT", "Ledger", "replay_split",
         "native_decide", "decide +kernel", "BitVec", "Mathlib"]

def title_key(t):   # numbers and runs of numbers (edge lists "0-3 1-4", masks) -> one N
    t = re.sub(r"^(It is false that: )?A step toward: ", r"\1", t)
    t = re.sub(r"\d+", "N", t)
    return re.sub(r"N(?:[-x×,/ ]+N)+", "N", t).strip()

def stmt_key(s):   # also folds a negation onto its positive twin: "¬ (P)" and "P" share a key
    s = re.sub(r"\s+", " ", s).strip()
    while True:
        t = re.sub(r"^¬ ?", "", s)
        if t.startswith("(") and t.endswith(")"): t = t[1:-1].strip()
        if t == s: break
        s = t
    return re.sub(r"\d+", "N", s)

def git(clone, *a):
    return subprocess.run(["git", "-C", clone, *a], capture_output=True, text=True).stdout

@functools.lru_cache(None)   # family_watch calls find() once per family: grep once
def theorems(clone):
    return git(clone, "-c", "grep.threads=1", "grep", "-h", "-A12", "-P", r"^theorem PEqualNP\.Outside\.\w+ :", "upstream/main", "--", D)

def lease_for_title(title):
    k = title_key(title)
    for p in sorted(glob.glob(os.path.join(PENP, "master", "leases", "*.json")), key=os.path.getmtime, reverse=True):
        try: g = json.load(open(p))["gap"]
        except Exception: continue
        if title_key(g.get("title", "")) == k and g.get("statement"): return g
    return None

def find(gap, clone=None, n=3, others=True):
    clone = clone or os.path.join(PENP, "pequalnp-proofs")
    sk = stmt_key(re.sub(r"(let \w+) :=", r"\1 ≔", gap["statement"]))
    # one-line theorem statements: "theorem PEqualNP.Outside.<mod> : <statement> := by"
    # the statement may span lines: take 12 lines of context and cut at ":= by"
    out = theorems(clone)
    mods = []
    for blk in re.split(r"\n(?=theorem PEqualNP\.Outside\.)", out):
        blk = re.sub(r"(let \w+) :=", r"\1 ≔", blk)   # a `let x :=` inside the statement is not its end
        m = re.match(r"theorem PEqualNP\.Outside\.(\w+) :(.*?)(:=|$)", blk, re.S)
        if m and stmt_key(m.group(2)) == sk: mods.append(m.group(1))
    paths = [D + m + ".lean" for m in dict.fromkeys(mods)]
    # ponytail: author from the squash subject "L-meta-123 (#456)" (0.5 s); `git log --name-only` took 112 s.
    # Files whose module is not the plain id (e.g. V_meta_9980__k13) show handle "?".
    who = {}
    for l in git(clone, "log", "--format=%ae|%an|%s", "upstream/main").splitlines():
        email, name, subj = l.split("|", 2)
        m = re.search(r"\b([A-Za-z]+-meta-\d+)\b.*\(#(\d+)\)", subj)
        if not m: continue
        h = re.match(r"(?:\d+\+)?([^@]+)@users\.noreply", email)
        who.setdefault(D + m.group(1).replace("-", "_") + ".lean", (h.group(1) if h else name, m.group(2)))
    size = {}
    for l in git(clone, "ls-tree", "-l", "upstream/main", "--", *paths).splitlines() if paths else []:
        f = l.split("\t"); size[f[1]] = int(f[0].split()[3])
    rows = [(size.get(p, 0), p, *who.get(p, ("?", "-"))) for p in paths]
    if others: rows = [r for r in rows if r[2] != ME]
    rows.sort()
    best = []
    for b, p, h, pr in rows[:n]:
        txt = git(clone, "show", "upstream/main:" + p)
        best.append({"path": p, "handle": h, "pr": pr, "bytes": b, "markers": [k for k in MARKS if k in txt], "text": txt})
    return {"title_key": title_key(gap.get("title", "")), "stmt_key": sk, "per_handle": Counter(r[2] for r in rows),
            "best": best, "recent": sorted((r for r in rows if r[3] != "-"), key=lambda r: -int(r[3]))[:n]}

def diff_hint(a, b, k=12):
    d = [l for l in difflib.unified_diff(a.splitlines(), b.splitlines(), lineterm="", n=0)
         if l[:1] in "+-" and not l.startswith(("+++", "---"))]
    return len(d), [l[:160] for l in d[:k]]

if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0].startswith("-"): sys.exit(__doc__)
    opt = lambda o, d: a[a.index(o) + 1] if o in a else d
    src = a[0]
    gap = json.load(open(src))["gap"] if src.endswith(".json") else lease_for_title(src)
    if not gap: sys.exit("no lease in master/leases/ with that title key: pass a lease json")
    r = find(gap, opt("--clone", None), int(opt("-n", 3)), "--all-handles" not in a)
    print("title key :", r["title_key"]); print("stmt key  :", r["stmt_key"][:200])
    print("merged    :", sum(r["per_handle"].values()), dict(r["per_handle"].most_common()))
    for x in r["best"]:
        print(f"  {x['bytes']:>8} B  {x['handle']:<18} #{x['pr']:<6} {x['path']}  [{', '.join(x['markers'])}]")
    for b, p, h, pr in r["recent"]: print(f"  recent {b:>8} B  {h:<18} #{pr:<6} {p}")
    if len(r["best"]) >= 2:
        nd, ls = diff_hint(r["best"][0]["text"], r["best"][1]["text"])
        print(f"diff of the two smallest: {nd} changed lines (few = data-only template)")
        for l in ls: print("   ", l)
