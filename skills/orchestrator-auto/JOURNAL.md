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
