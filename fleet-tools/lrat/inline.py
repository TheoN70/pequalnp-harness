"""Inline the LRAT library into one step file, for steps that may import only PEqualNP.Defs.

Usage: python3 -I inline.py <worktree> <Module>   (Module e.g. L_meta_9436) > body.lean
Prints the library (Shannon helper, Checker, LinkN, LinkN2) with its namespaces moved under
PEqualNP.Outside.<Module>, to paste right after `namespace PEqualNP.Outside.<Module>`:
  PEqualNP.Library.LRAT          -> PEqualNP.Outside.<Module>.LRAT
  PEqualNP.MetaComplexity.Helpers -> PEqualNP.Outside.<Module>.Helpers
Credit goes in the step file header (the library is by its authors, see git log of Library/LRAT).
About 115 KB, which leaves ~390 KB of the 512 KiB limit for the certificate.
ponytail: textual renaming; if a later library version adds another import, add it to FILES.
"""
import re, sys

FILES = ["lean/PEqualNP/MetaComplexity/Helpers/Shannon.lean",
         "lean/PEqualNP/Library/LRAT/Checker.lean",
         "lean/PEqualNP/Library/LRAT/LinkN.lean",
         "lean/PEqualNP/Library/LRAT/LinkN2.lean"]
OK_IMPORTS = {"PEqualNP.Defs", "PEqualNP.Defs.MetaComplexityLgpMono",
              "PEqualNP.Library.LRAT.Checker", "PEqualNP.Library.LRAT.LinkN",
              "PEqualNP.MetaComplexity.Helpers.Shannon"}


def main(wt, mod):
    full = f"PEqualNP.Outside.{mod}"
    out = [f"-- Inlined from PEqualNP.Library.LRAT (Checker, LinkN, LinkN2) and",
           f"-- PEqualNP.MetaComplexity.Helpers.Shannon, unchanged but for the namespaces.", ""]
    for f in FILES:
        src = open(f"{wt}/{f}").read()
        for imp in re.findall(r"^import (\S+)", src, re.M):
            assert imp in OK_IMPORTS, f"{f} imports {imp}: add it to FILES or check it is in Defs"
        src = re.sub(r"^import .*\n", "", src, flags=re.M)
        # namespace blocks: relative names, so they nest inside the step's namespace
        src = re.sub(r"^(namespace|end) PEqualNP\.Library\.LRAT", r"\1 LRAT", src, flags=re.M)
        src = re.sub(r"^(namespace|end) PEqualNP\.MetaComplexity\.Helpers", r"\1 Helpers", src, flags=re.M)
        # every other mention (open, qualified names): absolute, under the step's namespace
        src = src.replace("PEqualNP.Library.LRAT", f"{full}.LRAT")
        src = src.replace("PEqualNP.MetaComplexity.Helpers", f"{full}.Helpers")
        out += [f"-- ==== {f.split('lean/PEqualNP/')[1]} ====", src.strip(), ""]
    sys.stdout.write("\n".join(out) + "\n")


if __name__ == "__main__":
    main(*sys.argv[1:3])
