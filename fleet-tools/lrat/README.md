# LRAT lower bounds (2026-11-26)

`lower.sh <worktree> <n> <s> <table> <out.lean> [module]` proves "every fan-in-two AND/OR/NOT
circuit (NOT counted, HasCircuitSize) for the n-input f with truth table <table> has >= s+1 gates":
Lean dumps `LinkN.enc2` (the NOT encoding; `Defs.LratEncoding.enc2` is AND/OR only, wrong one),
the toolchain's CaDiCaL (`elan which lean`/../cadical, 2.1.2, `--lrat`) refutes it, `lrat2lean.py`
trims the proof (backward pass) and packs it for `checkW` of PEqualNP.Library.LRAT.Checker.
The worktree needs the library compiled once: `fleet-tools/lrat/build_lib.sh` (shared clone by default; `--check`
says what is missing). It builds all `PEqualNP.Library.LRAT.*` modules on core 15 under capmem 6G, refuses while
another lake/lean works in the clone or the library sources are modified, and ends with an import smoke test (first build 2026-11-26: 9 modules + Shannon, 193 s on one core).
After an upstream update of the clone, run it again (only changed modules rebuild).

Measured:
- n=4, s=3, table 2184 (L-meta-9550): 1594 clauses, 12 KB file, kernel check 6 s, axioms ok.
- n=5, s=8, table 0xeaa8a880 (9 gates): CaDiCaL 30 s, but certificate 47 MB after trimming
  (69 MB raw): 100x over the 512 KiB file limit. So: only small cases (n = 4, s <= ~6), which is
  what the desk's value steps (V_meta_*, imports PEqualNP.Library.LRAT.LinkN2) already are.
- L-meta steps may import only PEqualNP.Defs: `inline.py` copies the library (114 KB) into the
  step's namespace, but that file did not finish elaborating in 15 min (the checker allows 20 min
  and replays the kernel a second time). Not usable as is.

Worth trying before a next attempt: rows = a small subset (size_of_unsat2 accepts any rows < 2^n;
fewer rows = smaller formula), symmetry breaking on inputs, a smaller inlined library (only the
lemmas `size_of_unsat2` needs).

## Pseudo-Boolean proofs instead of LRAT? Measured 2026-11-26: no

Same enc2 CNF (`circsat.py cnf 5 s 0xeaa8a880`; f needs 9 gates), CaDiCaL 2.1.2 `--lrat` vs Exact 2.2.1 (PB solver,
VeriPB proof logging), one core each, raw untrimmed proofs:

| s | LRAT | Exact, clauses | Exact + exactly-one on selector groups |
|---|---|---|---|
| 6 | 1.7 MB | 10.6 MB (6 s) | 13.1 MB |
| 7 | 9.1 MB | 197 MB (108 s) | 226 MB |
| 8 | 116 MB (92 s) | no answer in 30 min, proof already 3.3 GB | same, 3.9 GB |

PB proofs are 6-22x larger and grow faster, so a VeriPB checker in Lean would not get past the 512 KiB limit. The
proofs are sound (s = 6 checked by VeriPB 3.0.2: VERIFIED UNSATISFIABLE). Kit kept outside the repo in
`work/tools/pb/`: Exact venv, VeriPB 3 built with cargo, `pbmeasure.py` (CNF -> OPB -> Exact with proof log) and
`conv1to3.py` (Exact's 1.1 proof format -> VeriPB 3.0). The size limit needs fewer rows or symmetry breaking on
inputs (see above), not another proof format.

## Promise lower bounds by cubes: `rep_lower.py` (2026-11-26)

`python3 -I rep_lower.py <worktree> <n> <m> <M> <s> <out.lean> [--module MOD] [--cores K] [-m 2G] [--work DIR]` proves
`¬ RepSizeAtMost (fun (u : Fin n) (v : Fin m) => (M : ℕ).testBit (m * u.val + v.val)) s`, the refute side of a
one-a-side promise step. The cover lemma is upstream (`PEqualNP.Library.LRAT.Cube.enc2_cover`,
`Promise.rep_lower_mask_of_cubes`): 3(n+m+s) cubes = first source x operation of the last gate. The script has Lean
dump the formula and the cubes, refutes each piece with the toolchain's CaDiCaL on `slots` cores (restart-safe in
`<out>.d/`), packs each LRAT (`lrat2lean.py`) and writes one theorem per cube, a `match` over k, and the bound.
Exit 3 if a piece is SAT (the bound is false). Imports `PEqualNP.Library.LRAT.PromiseCube`.

Measured (one CaDiCaL per cube, all pieces UNSAT in seconds):

| instance | cubes | file | Lean |
|---|---|---|---|
| 2x2 identity (M=9), s=2 | 18 | 29 KB | 9 s, axioms propext / Classical.choice / Quot.sound |
| 4x5 M=104287, s=5 | 42 | 2.5 MB | not run (> 512 KiB) |
| 4x5 M=104287, s=6 | 45 | 7.5 MB | not run |

The file grows ~3x per gate: cubes split the solving, not the total proof. A real refute (4x5 at s=9) would be
hundreds of MB, far over the 512 KiB limit. Usable only where s is small; past that the proof needs a smaller
argument (gate elimination as a lemma, symmetry breaking, a merged template such as `L_meta_9291.lean`).
