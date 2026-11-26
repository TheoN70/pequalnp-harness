"""Exit 0 when a negated step ("It is false that: ...") is refuted by its merged twin, else exit 1.

The twin is the step numbered one lower (L-meta-11853 / L-meta-11854 ...). It counts only when its file is on
open-goat/pequalnp-proofs main AND that file states exactly the body of our negation, so a wrong guess of the
twin id can never release a step. ponytail: id-1 pairing is what the desk does today; if it changes, nothing is
released (the statement check fails), the step just goes to a session as before.
"""
import base64, json, re, subprocess, sys


def norm(s):
    return re.sub(r"\s+", " ", s).strip()


def main(path):
    g = json.load(open(path))["gap"]
    if not g.get("title", "").startswith("It is false that:"):
        return 1
    st = norm(g["statement"])
    if not (st.startswith("¬ (") and st.endswith(")")):
        return 1
    body = norm(st[3:-1])
    m = re.fullmatch(r"L-([a-z]+)-(\d+)", g["id"])
    twin_file = "lean/PEqualNP/Outside/L_%s_%d.lean" % (m.group(1), int(m.group(2)) - 1)
    r = subprocess.run(["gh", "api", "repos/open-goat/pequalnp-proofs/contents/" + twin_file, "--jq", ".content"],
                       capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        return 1  # not merged (404) or GitHub unreachable: hand the step to a session
    text = norm(base64.b64decode(r.stdout).decode())
    return 0 if body in text else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
