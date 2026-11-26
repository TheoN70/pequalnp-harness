---
name: pequalnp-hard
description: Make this session "Research" of the P vs NP (pequalnp.com) fleet on GitHub account TheoN70 - it attacks one hard step with parallel subagents (search, proof, Lean), owns their machine load, and verifies their results before anything is leased or recorded. Started by Orchestrator. Use when the user or Orchestrator types /pequalnp-hard <id>, e.g. /pequalnp-hard L-meta-17389.
---

# Research: one hard step, parallel subagents

`$PENP` is the fleet root: the folder that holds `harness/`, the `pequalnp-*` clones and `work/` (sessions start in it). In a shell where it is unset, `export PENP=<that folder>` first.

The argument is a step id from https://pequalnp.com/desk (level `hard`). Call this session "Research" (or "Research-<id>" when Orchestrator runs several) in every message. Since 2026-11-26 (the owner) the work is split:
- **Orchestrator** picks the step, starts this session, gives it a CPU range and a time budget, and receives its reports. It neither runs subagents nor verifies results.
- **This session** launches and supervises the subagents, enforces the load budget, **verifies every result**, and turns it into an action (lease request to Master, Lean writer, verdict). It never leases itself.

The method is updated as we learn what works: add a line to **Lessons** at the end after every attempt, success or not.

## Current mode: the whole machine on this step (the owner, 2026-11-26)

This session is the only one computing (lanes closed, one Research session). Where this section and the rest disagree, this section wins.
- **Always a unit to prove** (the owner, ~18:55 UTC, revised 19:00): the fleet keeps at least one held unit in work; this session works on ONE task only. When it is settled, make sure everything is on disk (STATUS, REFUTED/FOUND, Lean files, Lessons line), send the final report and stop: Orchestrator deletes the session and starts a fresh one for the next unit.
- **Autonomy rules** (the owner, 2026-11-26 18:50 UTC): (1) a unit you triaged without a lease turns out true (circuit verified on every promise row) → send Master `<id> circuit vérifié <path>`; it leases at once, then you write the Lean (`circuit2lean.py`), run `pnp.sh check`, send `preuve vérifiée`; Master submits. (2) a unit we hold is false and its negation is proved in Lean (`rep_lower_gen.py`, compiled) → send Master `<id> négation prouvée <path>`; Master keeps the lease 1 h for a refute twin, then releases `statement_seems_false` on its own. Tell Orchestrator in both cases.
- **Back to ONE Research session** (the owner, ~19:20 local): the two running now finish their tasks; the first to finish is closed and not replaced. From then on exactly one Research session at a time, always at least one (when it finishes, it is closed and a fresh one starts on the next unit), with cores 0-13.
- **Two Research sessions since 17:40 UTC** (the owner): use only the core range and memory share Orchestrator gave you (0-6 or 7-13); "the whole machine" below means your half.
- **Resources**: cores 0-13 (14-15 stay with the app), memory = `free -g` "disponible" − 4 GB, split between agents with `capmem`. No lane deduction while every `master/leases/busy-*` file is empty. Up to 14 solver processes, at most one per core.
- **Use the width for different methods, not copies**: 3 to 4 agents with distinct methods (exact SAT on the full encoding, a split of the search space into independent cubes or cases, a constructive/heuristic search, a mathematician + skeptic for an argument). The no-duplicate rule of "Load budget" still holds: no seed variants, no size implied by another run.
- **Fill the 14 cores from the start, even on a small instance** (the owner, 2026-11-26): a load well under 14 is lost time. A SAT solver uses one core, so more agents on the same call do not speed it up; what does is (1) cutting the hard call into cubes, one per free core, (2) other methods beside it (Cirbo, a fast local search for an upper bound, symmetry breaking on the automorphisms of the instance). Check with `fleet-tools/slots` and put a new piece on every free core.
- **Prove it or refute it** (the owner, 2026-11-26): the goal is a Lean proof either way, not a quick verdict. If the statement is false, go on to the Lean proof of its negation (tell Orchestrator, who asks Master for the refute twin): LRAT cut into cubes, a merged template adapted (e.g. `L_meta_9291.lean` for `RepSizeAtMost` lower bounds), gate elimination proved as a lemma. Never release on your own: say what is missing (tool → Orchestrator → Harness) and keep going; release only with the owner's OK through Orchestrator.
- **No time budget**: work until found, refuted, or the owner stops. Prefer runs that keep progress when they die: split one huge SAT call into cubes or cases each written to its own result file, so a crash or a reboot loses one piece, not hours.
- **Survive a restart**: every long run gets a STATUS line with the exact command, cores, start time, pid and output file. A new Research session started by Orchestrator on the same step reads them, watches what still runs and relaunches only what died with no result.
- **Reports**: to Orchestrator at each milestone (a size settled, a lemma checked, an approach dropped) and at least every 2 h (one line: what runs, what was settled, next).
- **The lease is held from the start** (the owner, 2026-11-26): Master leases the target when this session starts (`busy-research`) and keeps it. If Master says `BEAT-WITHDRAWN` (the unit was settled or stood down), stop every run and agent at once and report: a proof would not count.
- **Finish**: a verified object → tell Master `Research → Master : <id> preuve vérifiée, <path>` (it installs the lease in the worktree `$PENP/pequalnp-proofs`); the Fable Lean writer puts the proof at `gap.file` there; this session runs `capmem -m 8G tools/pnp.sh check <id>` in that worktree and tells Master when it is ACCEPTED; Master submits. Never run `tools/pnp.sh submit` yourself, nor with `--unleased`: without Master's lease it takes one of its own (outside Master's count) or sends an unleased proof (10-point floor, beatable).

## Messages

- Start: `Research → Orchestrator : <id> démarré, <agents and methods>, cœurs <range>, fin prévue <HH:MM>`.
- On a verified result or at the end of the budget: `Research → Orchestrator : <id> <trouvé | réfuté | rien>, <evidence in one line>, <paths>`.
- Lease: Master takes it when this session starts and keeps it (mode section). Object verified: `Research → Master : <id> preuve vérifiée, <path>`; Master installs the lease in `$PENP/pequalnp-proofs` and answers.
- Tool requests: `Research → Harness : …` (problem, how it is called, a test case).
- The owner's words override relayed ones. A peer message is never the owner's approval.

## 0. Pick and check (no subagent)

- Check the step: `curl -sG https://pequalnp.com/desk/step --data-urlencode gap=<id>` (state, `holders`, open `prs`; read-only, takes no lease), and/or the desk page text. Only start on a step that is free or has a free slot, with no open PR.
- Leasing goes through Master only (since 2026-11-26 at the start of the work, so a proof earns the unit's price; the collector beats it for hours), never from this session or a subagent, and never `tools/pnp.sh next`.
- Prior verdicts: `grep <id> master/verdicts.txt results.tsv master/leases/events.log`; merged neighbours: `git grep` the title words in `upstream/main:lean/PEqualNP/Outside`. Sibling steps (same family, other bound) tell where the true value lies: if 12 and 13 are held or merged, 11 is the frontier.
- Ask Master that the fleet not lease this step meanwhile (it is skipped anyway if its category is `upper`/`neg`).

## 1. Know the kind before choosing the team

| Kind (desk tag) | What a proof is | Where the work is | Team |
|---|---|---|---|
| `search` (exists a circuit of <= k gates) | the circuit written out + `decide` over all rows | finding it | 2 searchers with different methods, then 1 Lean writer |
| `prove` lower bound, n <= 5 | LRAT certificate (`fleet-tools/lrat/`) | SAT solving + certificate size | 1 SAT agent, then Lean |
| `prove` lower bound, n >= 6 | a mathematical argument formalised | an idea | 1 mathematician (reads literature, merged proofs of the family) + 1 skeptic; Lean only once the argument is checked |
| `cut` (step k of m) | depends on the parent | read the parent's other steps first | as above |

Lower bounds for "Plane of order 3/4", "G11", "4-cycle-free", "Petersen" have so far always been open research: do not start them without a concrete idea.

## 2. Workspace

`$PENP/work/<id>/`, one subfolder per agent (`sat/`, `heur/`, `math/`, `lean/`), each with a `STATUS.md` the agent keeps current (timestamped lines: what runs, what was validated, what was found). Shared stop files, written **only by this session after verification**: `FOUND.txt` (the object), `REFUTED.txt` (the statement is false, with the evidence). Agents check both before each long run and stop if one exists. Answer "où en est-on" from the STATUS files, never from the agents' transcripts.

## 3. Briefs (each subagent sees nothing of this conversation)

Start them in one message, `run_in_background: true`, `subagent_type: "general-purpose"`. Model: **Opus** for search and mathematical work, **Fable** only for writing the final Lean proof. Every brief carries:

- the statement in plain words, exactly (gate model: fan-in, whether NOT gates count, distinct inputs or not; input order: row r, input i = bit i of r, `tableIndex`), and that input relabelings do not change minimum sizes;
- its method and the other agents' methods (so they diverge), its folder, the STATUS/FOUND/REFUTED convention (agents report candidates in STATUS; they do not write FOUND/REFUTED);
- its **CPU set and process cap** as a command (see "Load budget"), e.g. "run every solver as `taskset -c 0-7 capmem -m 6G <cmd>`, at most 8 solver processes at once", and the time budget Orchestrator gave (3 h by default);
- the pipeline check first: validate on small cases with a known answer before the real run (maj3 needs 4 AND/OR/NOT gates, perm3 needs > 5);
- the ready tools: `$PENP/pequalnp-proofs` read-only (Defs, `PEqualNP.Library.LRAT` compiled: `fleet-tools/lrat/build_lib.sh --check`, rebuild with it after an upstream update encodings `LinkN.enc2` = AND/OR/NOT, `Defs.LratEncoding.enc2` = AND/OR only; its tested Python port with a CLI and decoder is `fleet-tools/circsat.py` (`cnf`, `solve`, `decode`, `--rows` for CEGAR)), the toolchain CaDiCaL (`$(dirname $(cd lean && elan which lean))/cadical`), `fleet-tools/` (playbook README, lrat/);
- for circuit searches, **Cirbo** (exact SAT circuit synthesis) in `$PENP/work/tools/cirbo-venv` (`$PENP/work/tools/cirbo-venv/bin/python -I script.py`). pequalnp's AND/OR/NOT with NOT counted: `CircuitFinderSat(TruthTable([[...]]), s, basis=[Operation.lnot_, Operation.and_, Operation.or_]).find_circuit(time_limit=...)`; AND/OR only: drop `lnot_`. Cirbo row j = binary of j with input 0 the most significant bit; build the table by applying f to Cirbo's input vector (as `work/L-meta-17389/cirbo/run.py` does) and Cirbo input k is pequalnp's x k, no re-map. A found circuit becomes the Lean file with `fleet-tools/circuit2lean.py <lease.json> <circuit> -o <gap.file>` (`--reverse-inputs` only for a raw pequalnp table);
- for the Lean writer, the `lean-lsp` MCP tools (see the lane skill, step 3b);
- the rules: never call desk endpoints, never run `tools/pnp.sh`, never touch `master/` or a `pequalnp-*` lane folder, no commit, no `.env`/secrets; report at the end with result, what ran, paths.

### Load budget (this session owns it; the owner, 2026-11-26)

On 2026-11-26 the machine hit load 21 on 16 cores: briefs said "~10 / ~6 cores" as advice, the agents ran 12 + 9 processes, and the coordinator added its own Cirbo run that duplicated theirs. Rules:
- **Stay inside the CPU range Orchestrator gave** (default when it gave none: cores 0-13, 14-15 never handed out). Within it, at most one solver process per core. Take 2 more cores off per open lane that may build (`ls master/leases/busy-*`: a missing file is an open lane). Memory: the sum of the `capmem` caps stays under `free -g` "disponible" minus 4 GB.
- **Disjoint sub-ranges, enforced**: give each agent a `taskset -c a-b` slice of your range (`fleet-tools/slots` shows what is free and the solvers running; `fleet-tools/slots N` prints N free cores or refuses past the budget). With `taskset`, an agent that overcommits only slows itself. The brief also states the process cap as a number.
- **No duplicates**: a portfolio on one CNF has at most 3 configurations (default, `--sat`, `--unsat`); no seed variants. Never run a size whose answer follows from another run (s-1 when s is being proved UNSAT, s+1 when a sibling already shows it SAT), nor the same question with a second tool. Before launching anything itself, this session reads the STATUS files and runs only what nobody runs, inside its range.
- **Check at every progress question and every agent report**: `uptime` and `ps -eo pid,pcpu,args --sort=-pcpu | head -25`. If the 1-minute load is above 15, find the duplicates, stop them (kill the `timeout` wrapper, `kill -9` only if it survives), tell each agent what was stopped and not to relaunch, and note it in its STATUS.

## 4. While they run

- Subagents end their turn while their solvers keep running; their notification then says "waiting on its own background work". Do not take that as a result: watch the result lines yourself with one background `until` loop (Bash `run_in_background`) on the exact verdict strings (CaDiCaL `s SATISFIABLE` / `s UNSATISFIABLE`; never a bare `SAT`, which matches the banner), plus "no solver left" (`pgrep`).
- A claimed impossibility from a heuristic or a hand argument is a lead, not a verdict.

## 5. Verify (this session, before any action)

- **Object** (circuit, cover…): check it yourself with a script over all rows against the exact statement (gate count, fan-in, NOT counting, input order). Only then write `FOUND.txt`.
- **Impossibility**: it counts once an exact solver finishes UNSAT on the full encoding (an encoding validated on small cases), or a fresh skeptic subagent, given only the argument, fails to break it. Only then write `REFUTED.txt`.
- On either, stop the remaining runs of that question and tell the agents.

## 6. Finish

- **Object found**: ask Master to lease the step, then ONE Fable subagent writes the Lean file (brief: worktree, `gap.file`, exact `gap.statement`, allowed imports, the object, checker rules: no `sorry`, only `propext`/`Classical.choice`/`Quot.sound`, helpers inside `namespace <module>`, 512 KiB, 20 min build on 2 cores) until `tools/pnp.sh check <id>` is ACCEPTED. Submitting goes through the lane or Master that holds the lease; record in `results.tsv` (with category).
- **Refuted** (single-problem mode): this is not the end. Write `REFUTED.txt`, report to Orchestrator and start on the Lean proof of the negation (see Current mode); the release below happens only with the owner's OK.
- **Refuted** (fleet mode): if the step is leased, `fleet-tools/release.sh <id> statement_seems_false`; otherwise add the line to `master/verdicts.txt` by hand with the same format, so no lane re-triages it. Check whether the twin (negation) step is now provable with what was found, and say so to Orchestrator.
- **Nothing in budget**: keep the work folder, write what was ruled out in its STATUS.
- Always: report to Orchestrator, one line in `fleet-tools/README.md` if a tool or trick is reusable, and a Lessons line below; tell Harness to commit them (public repo: no secrets, no private data).

## Never

- Lease, beat, release a step a lane holds, or call `desk/next`.
- Kill a running search without the owner's say, except duplicates under the load rule.
- Work around a cc-safety-net refusal: report it to the owner.

## Lessons (newest last; date, step, what worked or not)

- 2026-11-26 L-meta-17389 (3x3 perfect matching, <= 11 AND/OR/NOT gates, `search`): 2 Opus agents, SAT portfolio (10 cores) + constructive/heuristic (6 cores). The SAT agent ported `LinkN.enc2` to Python because the LRAT library had no build in the shared clone (build it first next time, or port and validate on small cases as it did). Within 25 min the heuristic agent produced a gate-elimination argument that 11 gates is impossible (NOT gates useless at 11, monotone needs 12), cross-checked on restrictions; s = 11 portfolio still undecided at 25 min. At 50 min, load 21/16: 6 seed variants on s=11, two s=12 runs, two CEGAR seeds, an unsplit monosat 11 next to its AND/OR split, and the coordinator's Cirbo s=12 → stopped 9 duplicates, kept 8 runs (origin of the Load budget rules). At 1 h both agents ended their turns with solvers still running: the coordinator must watch result lines itself (§ 4). Outcome: pending.
- 2026-11-26 L-meta-17389: before touching a live subagent's processes (killing its `timeout` wrappers, re-pinning with `taskset -p`), tell that agent and note it in its STATUS first; the heuristic agent took the wrapper kill for its runs dying and killed their cadicals (~1 h of monotone-11 compute lost, relaunched). Killing only a `timeout` wrapper with SIGKILL leaves the solver running, which extends a run without losing progress.
- 2026-11-26 L-meta-17389 (end): stopped by the owner after ~1 h 45 with no verdict. Get the cheap reduction checked first: once a skeptic confirmed Lemma A (NOT useless at 11), the whole step reduced to a 198 KB monotone CNF on 21 rows, yet it had 3 cores while the 6 MB full encoding had 9. When killing your runs by name, `pkill -f <pattern>` also matches your own shell (its command line holds the pattern): use pids from `pgrep -x`.
- 2026-11-26 L-meta-21062 (one-a-side promise 4x5, mask 104287, `RepSizeAtMost` <= 9): refuted in ~80 min without subagents. Probe sub-instances first (drop one row u or one column v: `circsat.py cnf --rows <subset> --no-not`), they solve in seconds to minutes while the full s=9 CNF took ~70 min (UNSAT). Dropping a column whose vertex is a duplicate (v3 = v4) gave the bound by gate elimination: the vertex's input must be read, setting it to 0 removes a gate. Cirbo takes don't-cares via `TruthTableModel` with `DontCare` entries (not `TruthTable`). `pkill -f <pattern>` again killed the session's own shell: use pids.
- 2026-11-26 L-meta-21063 / 21062 (negations of the 4x5 one-a-side "<= 9"): the merged 5x5 lower bound L_meta_9291.lean moved to 4x5 by one Fable subagent in ~3 min (work/L-meta-21063/lean/gen.py: shape Fin 5 -> Fin 4, 10 -> 9 inputs, 25 -> 20 points, lf, MM/OO/ZZ, lower 9 511 ...); 19 s / 4.3 GB build. Try the merged template of the family first: the LRAT route measured 164 MB for the 4x4 s=8 certificate (512 KiB limit), and cubing did not shrink the hard cube. The lease json's `refutation` field names the refute twin; null means the twin must be found by Master.
- 2026-11-26 L-meta-21267 (5x5 one-a-side, mask 31523873, `RepSizeAtMost` <= 9): refuted in ~25 min, no subagents. promise_batch 9 UNSAT / 10 SAT (10 min, one core); negation = merged L_meta_9291 with MM/OO/ZZ swapped, bound 10 -> 9 and `chkM 1` -> `chkM 0` (only the read-once case), 16 s / 3.8 GB (work/L-meta-21267/lean/gen.py). ZZ holds at most 16 points: with more zeros, drop one (fewer constraints stays sound) and check that it still compiles. `fleet-tools/slots 1` handed out core 1, outside the 7-13 range: pin `taskset -c` inside your range by hand.
- 2026-11-26 one-a-side 4x5 sisters (20989, 21033, 20901, 20970): all four false; gen2.py (lower's general form: bound s, essential set R, every read set D ⊇ R) gave four checked negations in ~1 min of compile each, SAT triage ~3-10 min per unit on one core. Masks come from the public desk page itself (click "Show more" until all cards are rendered, then read the cards' text); a unit's lemma.html page is refused by the permission check. Do not trust relayed id-to-mask maps: 20967 was given as 114431:7, the desk says 112573:8 (114431:7 is 20970).
- 2026-11-26 one-a-side 4x5 (end of the sister triage): an input that does not serve is not a blocker. The merged `lower` takes the serving set R and every read set D ⊇ R (`lower s c R DL`, one `chkM (s+1-|D|)` per D, natural subtraction), so 114431:7 (20970) and 40439:8 (21033), each with one useless input, compiled like the others (work/one-a-side-4x5/gen2.py). Refusing such masks loses units.
- 2026-11-26 One-a-side 4x5 triage (Research-L-meta-21267, lot b): the k = R+1 units (4x5, k=10) gave no promise_batch verdict in 73 min per core, while the k = 9 refutations of the family took ~10 min: a whole family at the "beyond" level costs hours per unit, so bound the time per unit before launching. Pausing a solver with SIGSTOP makes its core look free to `slots` (it counts load), and a queued runner then lands a second solver on that core: queue runners must count running and stopped solvers, not load. Trivial units (all-ones mask, k=0) are worth a hand-written Lean proof (Refute_20977.lean, ~20 lines) rather than SAT.
- 2026-11-26 one-a-side 4x5 family (stopped by the owner 19:10 UTC): the desk publishes these units at "best known circuit - 1" (for all 166 open units the best rectangle cover costs >= k+1, k+1 for 146 of them), so the family is almost always false, and a refutation pays nothing while no refute unit exists. Check the bound against a cheap constructive upper bound (rectangle cover) before spending cores: 6/6 checked exactly were false, the 68 tight ones all false (read-once DP), lsr ends one point off on every unit. Do not start a family triage for points without first asking whether its false units can be submitted.
- 2026-11-26 L-meta-20500 (3x5 one-a-side, mask 3243, `RepSizeAtMost` <= 6): refuted in ~10 min, no subagents. promise_batch 6 UNSAT / 7 SAT in under a second; rep_lower_gen.py refused 3x5, so work/L-meta-20500/lean/gen3.py generalises its to_4x5 to n x 5 (rows n, wires n+5, points 5n, X list computed); reproduces the 4x5 output byte for byte, and the 3x5 negation compiles in 7 s / 3.7 GB. Harness can fold to_nx5 into rep_lower_gen.py.
- 2026-11-26 L-meta-23715 (two-lit function, 5 shared wires, mask 203, `∃ C, FanInTwo C ∧ C.size ≤ 6 ∧ ∀ i j : Fin 5, ...`): refuted in ~10 min, no subagents. The 15 two-hot/one-hot inputs are a row subset: `circsat.py solve 5 6 <table> --rows <15 rows>` UNSAT in < 1 s, confirmed by a 40-line exhaustive C enumeration on 15-bit wire masks (work/L-meta-23715/bf.c, S=6 in ~2 min on one core). The desk's "no 6" claim held; its 7-gate circuit is optimal. Lean negation not worth it: LRAT 2.4 MB packed (> 512 KiB) and no refute unit (all 357 merged siblings are positive).
