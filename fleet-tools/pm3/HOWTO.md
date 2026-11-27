# PM 3x3 "no normal-form circuit of <= k gates opens with G0 then G1" — which merged proof to adapt (Normal4, 2026-11-27)

Statement is `¬ ∃ C ...`: SAT circuit = FALSE (statement_seems_false); otherwise prove it in Lean from one of these:

1. **k = 11, x0 := 1 turns G0 into a constant and G1 into a literal or constant** (27543 OR(0,1)/AND(5,9), 27539 OR(0,1)/AND(3,9), 27551 OR(0,4)/AND(0,5)):
   adapt `L_meta_27743` (gate elimination). Keep Lower26514 / Pin26514 / Alternate27743 (`lower`: the x0=1 cofactor needs >= 10 gates, certificate tree).
   In Prefix: change `orig`/`bank` to the two opening functions; tail <= 9, so `Lower26514.project` with plug x0 := true is enough (no `save`); 10 <= 9 is the contradiction.
   (27743 itself is k = 12 with OR(0,1)/OR(0,3), both constant under x0=1, plus `save` for one extra gate.)
2. **k = 12, both opening gates read inputs only** (27763 OR(0,1)/OR(3,8); 27406 AND(0,4)/OR(1,5); 27408 AND(0,4)/OR(1,8)):
   adapt `L_meta_27763` (rigidity + Ledger). occRigid: the circuit is exactly 12 AND/OR gates, every wire other than the 4 opening inputs is read at most once.
   Ledger.impossible: inputs P, Q (not read by the opening) carry atoms p, q; every other input is constant on each side s; side 0 must make
   matching = p&q, side 1 matching = p|q. Change `occFirst`/`occSecond`, the opening input numbers {0,1,3,8} everywhere, `start` and `index`.
   `start` vectors: `python3 -I ledger_start.py <opening inputs>` here. 27406/27408: P=2, Q=3; side0 x7=1 (rest 0); side1 x1=x4=x6=x8=1 (rest 0).
   Column per input i = (side0 value, side1 value) with off/on atoms; P = (.p,.p), Q = (.q,.q); index t = if t then Q else P.
3. **G1 reads G0's wire** (27462 AND(0,4)/OR(8,9)): 27763's rigidity is a count. occTailInput says the tail reads all 9 inputs, and hlive says every non-output gate wire is read; 2*10+1 = 21 slots for 21 distinct reads, so it is tight.
   Here wire 9 is read by G1 itself, so the tail only needs 20 distinct reads in 21 slots: slack 1 (one NOT gate, or one wire read twice). The Ledger needs read-once AND/OR, so this does NOT adapt as is (Normal4: out_of_time unless someone extends the Ledger).

Search tools: `pm3c.py <k> op,a,b op,a,b` (CEGAR, sound UNSAT; no fLex once gates are pinned), `pm3.py` (full table).

## Twin rule (Orchestrator, 2026-11-27 17:40 UTC)
A "some normal-form circuit ... opens with X" unit shown false (no circuit with that opening) means its twin
"no normal-form circuit ... opens with X" (usually id+1) is TRUE, and the same argument proves it. Tell Master at
once: it leases the twin to you with `grab.sh --unit`, and you write that proof (27743 or 27763 route). Others are
fast on this family (27685 was sent within minutes of 27684), so do not wait.
