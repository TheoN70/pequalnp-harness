# Journal: Orchestrator autonomous mode

## Current strategy (2026-11-27 03:55 UTC)

PAUSED by the owner at 07:56 UTC on 2026-11-27 (collector off, lanes closed, lanes sessions idle). On resume, around 12 h UTC before the 14-19 h UTC waves: collector with NORMAL_LANES normal..normal3 + AUTO_LANES auto1..7, SKIP_CATS=neg.
(Harness), one Research side bet on a hard search unit. Single-problem mode ended (0 points in ~10 h).

## Scoreboard

| Date | Points | Rank | Note |
|---|---|---|---|
| 2026-11-27 03:50 | 236 (9 units, all 25 Nov) | 176 / 950 | start of autonomous mode |
| 2026-11-27 07:00 | 236 | - | hard search bet 17390: 0 (undecided); auto slots: 0 submitted (night units recycled, false) |

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
- 05:10 UTC: lever 5 (refute twins): a false unit pays only via its refute twin (kind refute) with a Lean negation. Asked Harness to log REFUTABLE <id> + keep negation when UNSAT falls in rep_lower_gen / lower.sh scope; Master leases the twin with --proof when the desk lists one. Measure REFUTABLE -> twin rate before investing more.
- 05:15 UTC: Harness d3c6830: refutable.sh on AUTO-FAIL rc 4 (rep_lower_gen <1 s; lower.sh n<=4, <=120 s), logs REFUTABLE. Caveats: lower.sh output not in refute-twin statement form; no two-lit negation generator. Master asked to restart collector.
- 06:00 UTC: auto slots 04:37-05:56: 5 units (42-65 pts, all recycled one-a-side/monotone), 0 submitted: 3 rc=4 UNSAT (false), 21050 rc=2, 20213 rc=3 (8x8 rep form unknown) released while lanes idle. Asked Harness: rc=3 on auto slot -> free lane, recognise 8x8 rep + 5-input monotone truth-table form (live mode 0), check 21050 timeout. Night desk serves recycled, mostly false units; real test = next fresh wave.
- 06:15 UTC: Harness deb82ec: AUTO-HANDOFF of rc 3 to a free lane; Fin-n variable forms (8x8) recognised; 5-input monotone truth-table family via live mode 0 (exact both ways); --is-false before lsr for 3x5/4x5/5x5 (21050 false, negation compiles); lsr 60 s, up to 4 seeds. Decision: rc 2 also handed to a free lane.
- 06:25 UTC: Harness 1e508dc/bb81d2f: rc 2/3 on auto slot -> free lane (AUTO-HANDOFF); unit already on main -> rc 5, released. Master restarting collector.
- 06:35 UTC: rule conflict settled: rc 2 of any family (RepSizeAtMost included) -> free lane via AUTO-HANDOFF; immediate release only for rc 4 (false) and rc 5 (on main). L-meta-21143 had been released by hand before this.
- 07:00 UTC: Research-next final on L-meta-17390: undecided after 3 h (2 real cubes open, Cirbo timeout 9000 s; no generic method even finds the known 14). Session deleted. Hard-search lever: 0 points, ~3 h x 6 cores; paused (needs a structural idea, not more SAT). Cores 0-13 back to autosolve/lanes.
- 07:10 UTC: Harness 6b19151/a121abf/cfe7a9b (cube.py skips unit-propagated vars)/1d645d9 (SLOTS_RANGE 0-13 default). Lanes told 0-13. Rule: when a Research takes 8-13, Master restarts with SLOTS_RANGE=0-7 and lanes export 0-7.
- 08:35 UTC: 0 PR overnight (lanes: 10009, 16081, 19384, 19696 out_of_time; auto: all false). Machine saturated: 7 circsat from a lane (3 orphaned, 31 min) + an unrelated project (~/Bureau/Boulot/penplike, lean ReplayAll, unpinned). Normal2 asked to kill its orphans; Harness asked for a hard solver timeout in capmem + lane rule. Lesson: lanes must kill their solvers on release.
- 08:40 UTC: Normal2 killed its 7 solvers, released 17732 out_of_time; max 3 solvers + timeout per lane from now.
- 08:45 UTC: Harness 662fe68: capmem -t (default 30 min, kills the whole systemd scope); lane skill: timeout 25m per background solver, pkill on release; Research uses -t 6h / -t 0.
- 07:56 UTC: STOP by the owner (relayed by Stratégie, confirmed in events.log): collector stopped, lanes closed, no lease held. Nothing restarts and no session is created until the owner asks.
- Resume plan (Stratégie, upstream PRs 24-26/11): waves arrive 14-19 h UTC (peaks 17 h on 25/11, 16 h on 26/11); nights and mornings empty. Restart ~12 h UTC with lanes + auto slots ready. The overnight run only met recycled false units, so the pipeline is still untested on a fresh wave.

### 2026-11-27 16:10 UTC: Reprise (new Orchestrator session)
- Fleet restarted by the owner 16:05 UTC mid-wave (366 ordinary units offered). Collector `grab.sh 15` running (SKIP_CATS=neg, auto1..7, SLOTS_RANGE=0-13); capacity 12.
- Found: lane sessions normal and normal3 gone while the collector filled busy-normal (L-meta-25899, 30 pts) and busy-normal3 (L-meta-25623, 36 pts); 25600 and 19144 already released "no lane session". Only Lane normal2 alive.
- Wave content: solid prose theorems (ciphers/key schedules, rank-one outputs, affine partitions), 30-36 pts, all autosolve rc=3; "A step toward" units auto-released missing_lemma. So lanes (LLM) are the lever on this wave, not autosolve.
- Action: started Lane normal and Lane normal3 (Sonnet, shared checkout); Master keeps both units beaten and BAILs on check-in. Master says the Owner had asked to keep normal/normal3 closed: asked the Owner session to confirm; will stop both lanes if so.
- Asymptotic family (binary address selector / pooled OR / rematching; 25715, 25702 out_of_time): no Research, lanes release in <=5 min.
- Score 236, rank 178/972 (unchanged since 25 Nov).
- 16:10 UTC: Owner confirms: keep normal/normal3 (closed only for lack of sessions), carte blanche on lanes; penplike at nice 19, ours first, keep 4 GB free. Solid rc=3 units are AUTO-RELEASED when all 3 lanes are full: proposed Lane normal4 (card, needs the owner's click; the app refuses session starts on a peer message). Master adds normal4 to NORMAL_LANES on check-in.
- 16:20 UTC: normal2 released 3 in a row (25715, 25702 asymptotic; 25560 "greedy row scan" after 15 s although its sibling L-meta-25558 is merged). Rule to lanes: triage-release only the asymptotic lower-bound family; any other solid unit gets a real try of up to 30 min from its merged sibling/template. Asked Master to re-lease 25560 to normal2. No Research for 30-pt solid units.
- 16:25 UTC: re-lease of 25560 refused (UNIT-REFUSED "not free to you now (held)"). Lesson: a released unit cannot be taken back at once, so a hasty release is a unit lost; the 30-min rule now reaches all lanes.
- 16:30 UTC: grab.sh auto-released every re-offered unit with ANY verdict, out_of_time/other included (29 ids blocked). Fixed 4288f7f (those two reasons ignored); Master restarts the collector. No pequalnp Harness session alive: small fix done here.
