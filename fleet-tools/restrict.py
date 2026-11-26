# For a 6-input table (hex), print the exact signed size (two-input gates, NOT free) of each restriction x_i := c,
# using ./live. Restrictions on inputs 3,4,5 keep the symmetry in inputs 0-2; input 0 is done without symmetry.
import subprocess, sys
T = int(sys.argv[1], 16)
def restr(T, i, c):
    t = 0
    for m in range(64):
        mm = (m | (1 << i)) if c else (m & ~(1 << i))
        if (T >> mm) & 1: t |= 1 << m
    return t
def size(t, vm, mode, sym):
    out = subprocess.run(["./live", "%016x" % t, hex(vm), str(mode), str(sym), "1", "11", "24"], capture_output=True, text=True).stdout
    for l in out.splitlines():
        if l.startswith("N=") and "FOUND" in l: return int(l.split()[0][2:])
    return None
for i in (5, 4, 3, 0):
    row = []
    for c in (0, 1):
        t = restr(T, i, c)
        dep = [j for j in range(6) if restr(t, j, 0) != restr(t, j, 1)]
        vm = sum(1 << j for j in dep)
        sym = 1 if i >= 3 else 0
        row.append("x%d:=%d table %016x depends on %s signed %s and/or %s" % (i, c, t, dep, size(t, vm, 1, sym) if dep else 0, size(t, vm, 0, sym) if dep else 0))
    print("\n".join(row))
