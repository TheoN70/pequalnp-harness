# Journal: Orchestrator autonomous mode

## Current strategy (2026-11-27 03:55 UTC)

Volume first: collector back on, all 5 slots used, 3 Sonnet lanes + automatic solver for two-lit / circuit units
(Harness), one Research side bet on a hard search unit. Single-problem mode ended (0 points in ~10 h).

## Scoreboard

| Date | Points | Rank | Note |
|---|---|---|---|
| 2026-11-27 03:50 | 236 (9 units, all 25 Nov) | 176 / 950 | start of autonomous mode |

## Entries

### 2026-11-27 03:50 UTC: diagnosis
- All 236 points came from fleet mode on 25 Nov (lower 5, reshape 2, plus 2 x 10). Single-problem mode on 26 Nov:
  ~10 units leased (one-a-side, two-lit), all false at the desk's bound ("best known - 1"), 0 points.
- Three leases expired overnight (BEAT-END 410, 01:18-01:38): nobody was working on them, Master did not react.
- Upstream merges 26-27 Nov: other handles merge many fresh units (L-meta-25xxx) within minutes, incl. two-lit n=6
  size <= 10 units whose proof is ~1 KB (circuit + decide); dli7319 merges many reductions (R_meta_*).
- Desk at 03:44: offerable_now 12 (all hard search, 116-179 pts), ordinary 0; 131 handles polling.

### 2026-11-27 03:55 UTC: volume mode started
- Master: stop solid-only loop; collector `SKIP_CATS=neg NORMAL_LANES="normal normal2 normal3" grab.sh 15`
  (`upper` filter lifted: two-lit / HasCircuitSize now provable by circuit2lean); 30 min limit per lane unit.
- Lanes started on Sonnet: lane-normal, lane-normal2, lane-normal3 (cores 0-7, capmem 4G).
- Harness asked for `fleet-tools/autosolve.sh` (sketch / circsat -> circuit2lean -> check -> submit, no LLM),
  hooked into grab.sh on LEASED. Expected biggest lever.
- Research-next (never used) re-tasked: side bet on one hard search unit (18259 / 17390 / 17389 / 20585),
  cores 8-13, 6 GB, 3 h.
- To measure: points/hour per lever, from results.tsv outcomes and /a/TheoN70.
- 03:47:45 UTC: Master confirms collector running in fleet mode (SKIP_CATS=neg, lanes normal..normal3; opened as each lane checks in).
- 03:55 UTC: Research-next picked L-meta-17390 (PM3x3 monotone <=13; 17389 likely false, 18259 is One-a-side). Desk refused --unit (empty offer); told it to compute now and lease later with --proof.
- 04:10 UTC: Harness shipped autosolve (f1c3075; skill+journal committed 97448a1). Covers two-lit, HasCircuitSize (n<=14), RepSizeAtMost masks; 600 s circsat on 1 core; hook AUTO-START/AUTO-SUBMITTED/AUTO-FAIL in grab.sh. Master asked to restart collector. Real submission not yet tested.
- 03:55:08 UTC: collector restarted with autosolve hook active. Desk still offers nothing ordinary (night).
- 04:15 UTC: analysis session 'Stratégie' (1000 last merged upstream PRs): leaders = two-lit volume (Julleht 172, yifgu 132, foudress 114; desk sketch + decide, ~1 KB), edisonhello ~120 monotone upper bounds (MonotoneN upperC) by exact SAT. TheoN70 0 in those 1000. Asked Harness to add the MonotoneN upper family to autosolve.
- 04:25 UTC: Stratégie: leaders' PRs come in bursts per desk wave (26/11: 171 @18h, 204 @19h, 0 @20h, 116 @21h); a wave empties in ~1 h; PR->merge median 68 min. Lever = throughput under the 5-unit cap. Asked Harness: parallel autosolve (up to 5), AUTOSOLVE_S 120 s, 5 s polling while ordinary units are offered.
- 04:30 UTC: Stratégie: ranks 5-14 merge mostly two-lit + RepSizeAtMost (true side) + HasCircuitSize, all circuit + decide; nobody does LRAT/lower bounds. Decision: One-a-side exclusion lifted (it was based on our false units only); RepSizeAtMost handled by autosolve only, AUTO-FAIL -> immediate release (no lane). Measure submitted vs false.
- 04:32 UTC: Master applied the RepSizeAtMost policy (collector never filtered One-a-side; --skip-families dropped). Counting submitted / false.
- 04:40 UTC: Research-next on 17390: 30/32 cubes UNSAT at 13 monotone gates (21 critical rows), 2 cubes + Cirbo running. Likely no witness -> side bet likely 0 points. Lesson: desk hard search bounds = best known - 1 too; prefer volume.
- 04:20 UTC: first fleet-mode leases: L-meta-10009 (AUTO-FAIL rc=3 unknown family -> lane normal), L-meta-24220 two-lit (AUTO-FAIL rc=2 in 2 s, lane confirmed false <=6 (min 7), released statement_seems_false). Master told to stop retrying --unit 17390.
- 04:35 UTC: Harness 158df05: autosolve tries lsr local search 30 s before circsat (edisonhello's MonotoneN = RepSizeAtMost mask form; L_meta_23657 4x6<=11 solved+compiled in 18 s), up to 5 parallel runs (pequalnp-auto1..5), AUTOSOLVE_S=120, desk polled every 5 s when ordinary units offered. Asked to prebuild auto2..5.
- 04:45 UTC: L-meta-10009 (Rectangles, 0-entries of PG(2,5) incidence by <=19 all-0 rectangles; level open, 844 pts) held lane normal 30 min, out_of_time. Lease JSON says capacity 12 (grows with checked proofs), not 5. Policy: open/hard units released on AUTO-FAIL (no lane). Asked Harness for auto-only slots auto1..7 (AUTO-FAIL -> immediate release), capacity read from lease answer.
- 04:55 UTC: Harness 1f08687: AUTO_LANES auto1..7 (AUTO-FAIL -> release, statement_seems_false on circsat UNSAT rc 4), capacity read from leases/capacity, open/hard on normal* released, 7 parallel runs (SAT_PAR=3), fetch serialized, CORE_WAIT_S 60. Core split: auto+lanes 0-7, Research 8-13 only.
- 05:00 UTC: all 7 autosolve worktrees prebuilt (3-5 min each); SLOTS_RANGE=0-7 default (842778d). Pipeline ready; waiting for a desk wave.
