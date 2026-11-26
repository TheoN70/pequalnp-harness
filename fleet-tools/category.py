"""Print a coarse category for a desk step, from its lease JSON (or a bare title with --title).

Usage: python3 -I category.py <lease.json>   |   python3 -I category.py --title "<title>"
Categories: upper (a small circuit/refutation exists), lower (none of size <= k / at least k),
reshape (every circuit has a no-larger one of some form), neg (negation of a twin), proof (proof complexity),
other; prefixed "cut/" for "A step toward:" sub-steps. Used for the category column of results.tsv.
ponytail: regexes on titles, wrong on odd phrasings; refine the rules when a category looks mixed.
"""
import json, re, sys


def category(title, gid=""):
    t = title.strip()
    cut = t.startswith("A step toward:")
    if cut:
        t = t[len("A step toward:"):].strip()
    if re.match(r"(It is false that|False:)", t):
        k = "neg"
    elif gid.startswith("L-pcx") or re.search(r"\brefut|\bResolution\b|\bproof system|\bCutting planes\b", t):
        k = "proof"
    elif re.search(r"\b(no|No)\b[^.:]*\b(circuit|list)\b|\bat least\b|\bneeds?\b|\btakes more than\b|\bsaves (at least|nothing)", t):
        k = "lower"
    elif re.search(r"(replaced by|no-larger|no larger|can be (made|turned))", t):
        k = "reshape"
    elif re.search(r"\b(at most|under) \d+|\b(some|Some|there is)\b[^.]*\bcircuit\b", t):
        k = "upper"
    else:
        k = "other"
    return ("cut/" if cut else "") + k


if __name__ == "__main__":
    if sys.argv[1] == "--title":
        print(category(sys.argv[2]))
    else:
        g = json.load(open(sys.argv[1]))["gap"]
        print(category(g.get("title", ""), g.get("id", "")))
    assert category("An AND/OR circuit of fan-in at most two with at most 16 gates computes the edge function") == "upper"
    assert category("A step toward: Petersen graph: no circuit of AND, OR (fan-in two) and NOT gates with at most 19 gates computes") == "cut/lower"
    assert category("It is false that: One NOT gate saves nothing") == "neg"
    assert category("4-cycle-free incidence: every AND/OR fan-in-two circuit has a no-larger one whose ANDs are false") == "reshape"
    assert category("x", "L-pcx-130") == "proof"
