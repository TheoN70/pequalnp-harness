#!/usr/bin/env python3
"""harvest.py: merged proofs by OTHER handles for the families we release most, read-only on upstream/main.

usage: python3 -I harvest.py [clone] [--family onenot|onenot-refute|table2|false6] [--all] [--tsv]
  clone: a pequalnp-proofs clone with an `upstream` remote (default $PENP/pequalnp-proofs); run `git fetch upstream main` first.
Per file: id, handle (noreply login, else author name), PR, bytes, vertices/M (one-NOT) or table/m (six-input), technique
(markers found in the file), imports. Default: other handles only, sorted by M descending. Classification is by the
statement's shape, not the desk title (PR titles are just the id).
"""
import os, re, subprocess, sys
from collections import Counter

here = os.path.dirname(os.path.realpath(__file__))
args = [a for a in sys.argv[1:] if not a.startswith("--")]
clone = args[0] if args else os.path.join(here, "..", "..", "pequalnp-proofs")
fam_only = sys.argv[sys.argv.index("--family") + 1] if "--family" in sys.argv else None
if fam_only in args: args.remove(fam_only)
ME = "TheoN70"
D = "lean/PEqualNP/Outside/"
git = lambda *a: subprocess.run(["git", "-C", clone, *a], capture_output=True, text=True, check=True).stdout

# who added each file: "@name|email|subject" then the path
who = {}
cur = None
for l in git("log", "--diff-filter=A", "--format=@%an|%ae|%s", "--name-only", "upstream/main", "--", D).splitlines():
    if l.startswith("@"):
        name, email, subj = l[1:].split("|", 2)
        m = re.match(r"(?:\d+\+)?([^@]+)@users\.noreply\.github\.com", email)
        pr = re.search(r"\(#(\d+)\)", subj)
        cur = (m.group(1) if m else name, pr.group(1) if pr else "-")
    elif l.endswith(".lean") and cur:
        who.setdefault(l, cur)

MARK = ["inductive Sol", "ForestCore", "Certificate", "bigNat_", "CoreSearch", "Prog ", "live_separates", "no_build", "LRAT", "Ledger", "good_at", "replay_split",
        "native_decide", "Mathlib", "BitVec"]
def grep(pat, *flags):   # {path: first match line} over upstream/main, fast (git grep), never reading whole files
    out = {}
    r = subprocess.run(["git", "-C", clone, "grep", "-P", *flags, pat, "upstream/main", "--", D], capture_output=True, text=True)
    for l in r.stdout.splitlines():
        path, _, rest = l[len("upstream/main:"):].partition(":")
        out.setdefault(path, rest)
    return out
stmt = grep(r"^theorem PEqualNP\.Outside\.\w+ :", "-h") and grep(r"^theorem PEqualNP\.Outside\.\w+ :")
size = {l.split("\t")[1]: int(l.split()[3]) for l in git("ls-tree", "-l", "upstream/main", D).splitlines()}
def family(t):
    neg = re.match(r"theorem PEqualNP\.Outside\.\w+ : \(?¬", t) is not None
    if "GateOp.not → (gates.get j).op" in t or "GateOp.not → i = j" in t:
        return "onenot-refute" if neg else "onenot"
    if "HasCircuitSize 6" in t and "Monotone2" in t:
        return "false6" if neg else "table2"
    return None
fams = {f: family(t) for f, t in stmt.items()}
fams = {f: x for f, x in fams.items() if x and (not fam_only or x == fam_only)}
nv = grep(r"Fin \d+ → Bool", "-o"); low = grep(r"Low \d+ target", "-o"); hs = grep(r"\b\d+ ≤ gates\.length", "-o")
gl = grep(r"gs\.length = \d+|wit\.size ≤ \d+|size ≤ \d+ := by decide", "-o"); tb = grep(r"Nat\.testBit \(\d+ \* 2 \^ 32 \+ \d+\)", "-o")
marks = {k: set(grep(re.escape(k), "-l", "-F").keys()) if False else set(
    subprocess.run(["git", "-C", clone, "grep", "-l", "-F", k, "upstream/main", "--", D], capture_output=True, text=True)
    .stdout.replace("upstream/main:", "").split()) for k in MARK}
num = lambda d, f: int(re.search(r"\d+", d[f]).group()) if f in d else None
rows, count = [], Counter()
for f, fam in fams.items():
    h, pr = who.get(f, ("?", "-"))
    count[(fam, h == ME)] += 1
    if h == ME and "--all" not in sys.argv: continue
    if fam.startswith("onenot"):
        M = num(hs, f) or ((num(low, f) or -1) + 1) or None
        desc, key = "n=%s M=%s" % (num(nv, f) or "?", M or "?"), M or 0
    else:
        m = num(gl, f)
        desc, key = "table=%s m=%s" % (tb.get(f, "?")[13:-1].replace(" ", ""), m or "?"), m or 0
    tech = ",".join(k.strip() for k in MARK if f in marks[k])
    rows.append((fam, key, f.rsplit("/", 1)[1][:-5], h, pr, size.get(f, 0), desc, tech))
rows.sort(key=lambda r: (r[0], -r[1], r[5]))
sep = "\t" if "--tsv" in sys.argv else "  "
for r in rows: print(sep.join(map(str, r[:1] + r[2:])))
for (fam, mine), c in sorted(count.items()): print("# %-14s %s: %d" % (fam, "TheoN70" if mine else "others", c), file=sys.stderr)
