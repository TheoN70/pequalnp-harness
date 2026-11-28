# Install a desk answer (gap + lease) handed over by the Master session into a clone, the way
# `tools/pnp.sh next` does: same shape checks, same skeleton. Usage: take.py <answer.json> <clone root>
import json, os, re, sys

def install(src, root):
    d = json.load(open(src))
    g, lease = d.get("gap"), d.get("lease")
    if not isinstance(g, dict) or not isinstance(lease, dict):
        sys.exit("no gap or no lease in this answer; nothing written")
    gid, path, module = g["id"], g["file"], g["module"]
    if (not re.fullmatch(r"L-[a-z]+-\d+", gid)
            or not re.fullmatch(r"lean/PEqualNP/Outside/[A-Za-z0-9_]+\.lean", path)
            or not re.fullmatch(r"PEqualNP\.Outside\.[A-Za-z0-9_]+", module)
            or not re.fullmatch(r"[0-9a-f-]{36}", str(lease.get("id", "")))):
        sys.exit("the answer has an unexpected shape; nothing written")
    full = os.path.join(root, path)
    existed = os.path.exists(full)   # an existing file usually means: already merged upstream
    os.makedirs(os.path.join(root, ".pnp"), exist_ok=True)
    json.dump(d, open(os.path.join(root, ".pnp", gid + ".json"), "w"), indent=1)
    if not existed:
        imports = [m for m in (g.get("imports") or []) if re.fullmatch(r"[A-Za-z0-9_.]+", m)]
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as f:
            f.write("import Mathlib\n" + "".join("import %s\n" % m for m in imports)
                    + "\ntheorem %s : (%s) := by\n  sorry\n" % (module, g["statement"]))
    print("STEP ", gid, "-", g.get("title", ""))
    print("FILE ", path, "(ALREADY EXISTED, not overwritten)" if existed else "(skeleton written)")
    print("LEASE", lease["id"], "until", lease.get("expires_at"))
    for k in ("weight", "parallel", "imports", "shard_spec"):
        if g.get(k) is not None: print(k.upper(), g[k])
    if "shard" in d: print("RANGE", d["shard"], "of", d.get("shards"))
    return gid, existed

if __name__ == "__main__":
    install(sys.argv[1], sys.argv[2])
