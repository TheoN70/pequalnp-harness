#!/usr/bin/env bash
# Usage: lower.sh <worktree> <n> <s> <table> <out.lean> [module name]
# Proves "every fan-in-two AND/OR/NOT circuit for f has at least s+1 gates" (HasCircuitSize, NOT
# gates counted) for the n-input f whose truth table is <table> (bit r = f on row r, input i = bit i
# of r), with an LRAT certificate replayed by the library checker (PEqualNP.Library.LRAT).
# Steps: Lean dumps LinkN.enc2 n s (the NOT-gate encoding, not Defs.LratEncoding.enc2, which is AND/OR only) (rowFun n f) (all 2^n rows) as DIMACS (so the CNF is exactly Lean's),
# CaDiCaL (the toolchain's) proves it UNSAT with LRAT, lrat2lean.py packs the certificate, and the
# Lean file states `lower` through size_of_unsat2. Exit 3 if the formula is SAT (a circuit of
# <= s gates exists, the bound is false).
# The output imports PEqualNP.Library.LRAT.LinkN2: fine for steps that list it (value steps);
# for a step that may import only PEqualNP.Defs, the library must be inlined (inline.py, TODO).
# ponytail: all 2^n rows; cube splitting (enc2Cube) and segment cuts (checkFirst/checkSeg) are the
# upgrade path when one certificate gets too big for one theorem or the 512 KiB file limit.
set -euo pipefail
wt=$(readlink -f "$1"); n=$2; s=$3; tab=$4; out=$(readlink -f "$5"); mod=${6:-LratTest}
here=$(dirname "$(readlink -f "$0")")
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
cad=$(dirname "$(cd "$wt/lean" && elan which lean)")/cadical
rows=$((1 << n))
cat > "$tmp/dump.lean" <<E
import PEqualNP.Defs
import PEqualNP.Library.LRAT.LinkN2
open PEqualNP.Library.LRAT PEqualNP.Library.LRAT.LinkN
def fn (x : Fin $n → Bool) : Bool := ($tab : ℕ).testBit (PEqualNP.MetaComplexity.tableIndex x)
def F : List (List ℕ) := enc2 $n $s (rowFun $n fn) (List.range $rows)
def lit (l : ℕ) : Int := if l % 2 == 0 then ((l / 2 : ℕ) : Int) else -((l / 2 : ℕ) : Int)
#eval do
  let mx := F.foldl (fun (m : ℕ) (c : List ℕ) => c.foldl (fun (m l : ℕ) => max m (l / 2)) m) 0
  let h ← IO.FS.Handle.mk "$tmp/f.cnf" .write
  h.putStrLn s!"p cnf {mx} {F.length}"
  for c in F do
    h.putStrLn (" ".intercalate (List.map (fun l => toString (lit l)) c) ++ " 0")
E
(cd "$wt/lean" && lake env lean "$tmp/dump.lean")
set +e; "$cad" -q --lrat --binary=false "$tmp/f.cnf" "$tmp/f.lrat"; rc=$?; set -e
[ $rc -eq 10 ] && { echo "SAT: a circuit of at most $s gates exists" >&2; exit 3; }
[ $rc -eq 20 ] || { echo "cadical rc=$rc" >&2; exit 1; }
python3 -I "$here/lrat2lean.py" "$tmp/f.cnf" "$tmp/f.lrat" "$tmp/cert.lean" --name c
{
cat <<E
import PEqualNP.Defs
import PEqualNP.Library.LRAT.LinkN2

namespace $mod
open PEqualNP.Library.LRAT PEqualNP.Library.LRAT.LinkN

def fn (x : Fin $n → Bool) : Bool := ($tab : ℕ).testBit (PEqualNP.MetaComplexity.tableIndex x)

def rows : List ℕ := List.range $rows

def F : List (List ℕ) := enc2 $n $s (rowFun $n fn) rows

E
cat "$tmp/cert.lean"
cat <<E

set_option maxRecDepth 1000000 in
set_option maxHeartbeats 0 in
theorem unsat : ¬ FormulaSat F :=
  checkW_sound F (unpack c_W c_Kw) c_W c_Pw (by decide +kernel)

theorem lower : ∀ t : ℕ, PEqualNP.MetaComplexity.HasCircuitSize $n fn t → $((s + 1)) ≤ t :=
  size_of_unsat2 $n $s fn rows (by decide) unsat

end $mod
E
} > "$out"
echo "wrote $out ($(wc -c < "$out") bytes)"
