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
