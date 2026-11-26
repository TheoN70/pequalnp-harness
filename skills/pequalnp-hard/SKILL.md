---
name: pequalnp-hard
description: Attack one hard step of the P vs NP (pequalnp.com) desk with several subagents in parallel (search, proof, Lean), for GitHub account TheoN70. Use when the owner asks to work on, prove or search a hard step, e.g. "on attaque L-meta-17389" or /pequalnp-hard L-meta-17389.
---

# Hard step with parallel subagents

`$PENP` is the fleet root: the folder that holds `harness/`, the `pequalnp-*` clones and `work/` (sessions start in it). In a shell where it is unset, `export PENP=<that folder>` first.

The argument is a step id from https://pequalnp.com/desk (level `hard`). This session coordinates; subagents do the work. Started 2026-11-26 (the owner): the method is updated as we learn what works, in the **Lessons** section at the end. Add a line there after every attempt, success or not.

## 0. Pick and check (coordinator, no subagent)

- Check the step: `curl -sG https://pequalnp.com/desk/step --data-urlencode gap=<id>` (state, `holders`, open `prs`; read-only, takes no lease), and/or read the desk page (https://pequalnp.com/desk, get_page_text). The card says `free · 1 holder` (leasable), `Leased by … · N min left` (slot open) or `Full`. Only start on a step that is free or has a free slot.
- Do **not** lease yet. A lease lives about 20 min between beats; a search can take hours. Lease only once a candidate proof or object exists. Leasing goes through Master or `tools/pnp.sh` from a worktree, never from a subagent, and never `tools/pnp.sh next` from a lane.
- Look for prior verdicts: `grep <id> master/verdicts.txt results.tsv master/leases/events.log`, and for merged neighbours (`git grep` the title words in `upstream/main:lean/PEqualNP/Outside`). Sibling steps (same family, other bound) tell where the true value lies: if 12 and 13 are held or merged, 11 is the frontier.
- Tell Master the fleet must not lease this step meanwhile (it is skipped anyway if its category is `upper`/`neg`).

## 1. Know the kind before choosing the team

| Kind (desk tag) | What a proof is | Where the work is | Team |
|---|---|---|---|
| `search` (exists a circuit of <= k gates) | the circuit written out + `decide` over all rows | finding it | 2 searchers with different methods, then 1 Lean writer |
| `prove` lower bound, n <= 5 | LRAT certificate (`fleet-tools/lrat/`) | SAT solving + certificate size | 1 SAT agent, then Lean |
| `prove` lower bound, n >= 6 | a mathematical argument formalised | an idea | 1 mathematician (reads literature, merged proofs of the family) + 1 skeptic; Lean only once the argument is checked |
| `cut` (step k of m) | depends on the parent | read the parent's other steps first | as above |

Lower bounds for "Plane of order 3/4", "G11", "4-cycle-free", "Petersen" have so far always been open research: do not start them without a concrete idea.

## 2. Workspace

`$PENP/work/<id>/`, one subfolder per agent (`sat/`, `heur/`, `math/`, `lean/`), each with a `STATUS.md` the agent keeps current (timestamped lines: what runs, what was validated, what was found). Shared stop file: `FOUND.txt` (the object, verified), or `REFUTED.txt` (the statement is false, with the evidence). Every agent checks both before each long run and stops if one exists. Read the STATUS files to answer "où en est-on", never the agents' transcripts.

## 3. Briefs (each subagent sees nothing of this conversation)

Start them in one message, `run_in_background: true`, `subagent_type: "general-purpose"`. Model: **Opus** for search and mathematical work (encoding, symmetry breaking, arguments), **Fable** only for writing the final Lean proof. Every brief carries:

- the statement in plain words, exactly (gate model: fan-in, whether NOT gates count, distinct inputs or not; input order: row r, input i = bit i of r, `tableIndex`), and that input relabelings do not change minimum sizes;
- its method and the other agents' methods (so they diverge), its folder, the STATUS/FOUND/REFUTED convention;
- its **CPU set and process cap** (see "Load budget" below), written as a command, e.g. "run every solver as `taskset -c 0-7 capmem -m 6G <cmd>`, at most 8 solver processes at once", and a time budget (3 h by default);
- the pipeline check first: validate on small cases with a known answer before the real run;
- the ready tools: the repo `$PENP/pequalnp-proofs` read-only (Defs, `PEqualNP.Library.LRAT` encodings `LinkN.enc2` = AND/OR/NOT, `Defs.LratEncoding.enc2` = AND/OR only), the toolchain CaDiCaL (`$(dirname $(cd lean && elan which lean))/cadical`), `fleet-tools/` (playbook README, lrat/);
- for circuit searches, **Cirbo** (exact SAT circuit synthesis, Kulikov et al.), installed in `$PENP/work/tools/cirbo-venv` (run `$PENP/work/tools/cirbo-venv/bin/python -I script.py`). Model of pequalnp's AND/OR/NOT circuits with NOT counted: `CircuitFinderSat(TruthTable([[...]]), s, basis=[Operation.lnot_, Operation.and_, Operation.or_]).find_circuit(time_limit=...)`; AND/OR only: drop `lnot_`. Cirbo row j = binary of j with input 0 the most significant bit (a relabeling of pequalnp's order: sizes unchanged, but re-map inputs before writing Lean). Example: `work/L-meta-17389/cirbo/run.py`;
- for the Lean writer, the `lean-lsp` MCP tools (see the lane skill, step 3b);
- the rules: never call desk endpoints, never run `tools/pnp.sh`, never touch `master/` or a `pequalnp-*` lane folder, no commit, no `.env`/secrets; report at the end with result, what ran, paths.

### Load budget (the coordinator owns it; the owner, 2026-11-26)

On 2026-11-26 the machine hit load 21 on 16 cores: the briefs said "~10 / ~6 cores" as advice, the agents ran 12 + 9 processes, and the coordinator added its own Cirbo run on top, which duplicated theirs. Rules:
- **Total cap 14 solver processes**, 2 cores left for the desktop app, Lean and the lanes; take 2 more off per open lane that may build (`ls master/leases/busy-*`: a missing file is an open lane). Memory: the sum of the `capmem` caps stays under `free -g` "disponible" minus 4 GB.
- **Disjoint CPU sets, enforced, not advised**: give each agent a `taskset -c a-b` range (e.g. 0-7 SAT, 8-13 heuristic; 14-15 never handed out). With `taskset`, an agent that overcommits only slows itself. The brief also states the process cap as a number.
- **No duplicates**: a portfolio on one CNF has at most 3 configurations (default, `--sat`, `--unsat`); no seed variants. Never run a size whose answer follows from another run (s-1 when s is being proved UNSAT, s+1 when a sibling already shows it SAT), nor the same question with a second tool. Before launching anything itself (a tool test, a check), the coordinator reads the STATUS files and runs only what nobody runs, inside the reserved range.
- **Check at every progress question**: `uptime` and `ps -eo pid,pcpu,args --sort=-pcpu | head -25`. If the 1-minute load is above 15, find the duplicates, stop them (kill the `timeout` wrapper, `kill -9` only if it survives), tell each agent what was stopped and not to relaunch, and note it in its STATUS.

## 4. While they run

Answer progress questions from the STATUS files, after the load check above. A claimed impossibility from a heuristic or a hand argument is a lead, not a verdict: it counts once an exact solver finishes UNSAT on the full encoding, or a second agent (skeptic, fresh brief with the argument only) fails to break it.

## 5. Finish

- **Object found**: verify it yourself (script over all rows), lease the step (Master), copy the JSON, then ONE Fable subagent writes the Lean file (brief: worktree, `gap.file`, exact `gap.statement`, allowed imports, the object, checker rules: no `sorry`, only `propext`/`Classical.choice`/`Quot.sound`, helpers inside `namespace <module>`, 512 KiB, 20 min build on 2 cores) until `tools/pnp.sh check <id>` is ACCEPTED; then submit, record in `results.tsv` (with category).
- **Refuted**: if the step is leased, `fleet-tools/release.sh <id> statement_seems_false`; otherwise add the line to `master/verdicts.txt` by hand with the same format, so no lane re-triages it. Check whether the twin (negation) step is now provable with what was found.
- **Nothing in budget**: keep the work folder, write what was ruled out in its STATUS, add a Lessons line.
- Always: one line in `fleet-tools/README.md` if a tool or trick is reusable, and a Lessons line below.

## Lessons (newest last; date, step, what worked or not)

- 2026-11-26 L-meta-17389 (3x3 perfect matching, <= 11 AND/OR/NOT gates, `search`): 2 Opus agents, SAT portfolio (10 cores) + constructive/heuristic (6 cores). The SAT agent ported `LinkN.enc2` to Python because the LRAT library had no build in the shared clone (build it first next time, or port and validate on small cases as it did). Within 25 min the heuristic agent produced a gate-elimination argument that 11 gates is impossible (NOT gates useless at 11, monotone needs 12), cross-checked on restrictions; s = 11 portfolio still undecided at 25 min. At 50 min, load 21/16: 6 seed variants on s=11, two s=12 runs, two CEGAR seeds, an unsplit monosat 11 next to its AND/OR split, and the coordinator's Cirbo s=12 → stopped 9 duplicates, kept 8 runs (origin of the Load budget rules). Outcome: pending.
