---
name: pequalnp-lane
description: Initialise this session as a worker lane of the P vs NP (pequalnp.com) effort on GitHub account TheoN70, fed with leases by the "Master" session. Use when the user types /pequalnp-lane <lane>, e.g. /pequalnp-lane normal2 or /pequalnp-lane hard2.
---

# Worker lane for pequalnp

`$PENP` is the fleet root: the folder that holds `harness/`, the `pequalnp-*` clones and `work/` (sessions start in it). In a shell where it is unset, `export PENP=<that folder>` first.

The argument is the lane name (`normal2`, `normal3`, `hard2`...). A lane starting with `normal` gets ordinary steps, one starting with `hard` gets hard steps. Call this session by the lane name with the first letter capitalised (`Normal2`) in every message.


**Background solvers (Orchestrator, 2026-11-27):** each solver started in the background gets `timeout 25m` (and `capmem` kills anything past 30 min by default); when you release or submit, kill everything you started (`pkill -f "[c]ircsat ..."`, the bracket keeps `pkill` off its own shell). Orphaned circsat runs once held all 14 cores for 31 min.

**Cores (Orchestrator, 2026-11-27):** with no Research session running, lanes and autosolve use cores 0-13; when Orchestrator says a Research session holds 8-13, they keep to 0-7. Every heavy command of a lane: `export SLOTS_RANGE=0-13` (or `0-7` then), then `taskset -c "$(fleet-tools/slots N)" fleet-tools/capmem ...`.
## Who does what

- **Master** (another local session) runs the lease tool: it watches the desk, takes each lease itself and sends it to a free lane. It also renews every lease it hands out every 10 minutes.
- **This session** proves, submits or releases the step it was given. One step at a time. Keep going until the owner says stop.
- **Never** run `tools/pnp.sh next` (with or without flags), never call `desk/next`: leases are keyed by the GitHub handle shared by every lane, and a stray call can take or kill another lane's step.
- Never touch the other lanes' folders: `pequalnp-proofs` (Hard), `pequalnp-normal` (Normal), or any other `pequalnp-*` that is not yours.

## Setup (once)

1. `export PNP_MODEL=claude-sonnet-5-5` (join.txt asks it of every agent) and check `grep -c model_q tools/pnp.sh` is non-zero (upstream pnp.sh of 2026-11-26 or later); if 0, tell Master (cc-safety-net blocks `git checkout <ref> -- <path>`, do not work around it). Read https://pequalnp.com/join.txt, then `CONTRIBUTING.md` and `tools/pnp.sh` in the clone, then the fleet playbook `$PENP/fleet-tools/README.md` (triage recipes, shared search tools, Lean proof generators, known pitfalls). Add a line there whenever you learn something another lane could reuse.
2. Your worktree is `$PENP/pequalnp-<lane>`. If it does not exist, create it from the shared clone, detached, and share the Mathlib packages instead of downloading them again:
   ```bash
   git -C $PENP/pequalnp-proofs fetch upstream
   git -C $PENP/pequalnp-proofs worktree add --detach $PENP/pequalnp-<lane> upstream/main
   mkdir -p $PENP/pequalnp-<lane>/lean/.lake
   ln -s $PENP/pequalnp-proofs/lean/.lake/packages $PENP/pequalnp-<lane>/lean/.lake/packages
   ```
   If it exists, bring it up to date: `git -C <worktree> fetch upstream && git -C <worktree> checkout --detach upstream/main`.
3. Check that `lake build` of an existing module works from `<worktree>/lean`.
4. Send Master: `<Lane> → Master : prête` (SendMessage to `Master`). Master opens the lane only after this message.

## On each lease

Master's message starts with `BAIL <id> <path to JSON>`. The JSON is the desk's raw answer (`gap`, `lease`, sometimes `shard`).

1. Copy it to `<worktree>/.pnp/<id>.json`, write the skeleton the way `pnp.sh next` does (`import Mathlib`, the gap imports, `theorem <gap.module> : <gap.statement> := by sorry` in `gap.file`), then run `tools/pnp.sh beat <id>` at once and keep a beat loop every 10 minutes. Confirm the beat to Master.
2. Triage first: is the twin of the step already merged upstream (then the step is false or dead)? Is there a merged neighbour proof to adapt, with credit in the file header (that is how L-meta-10115 was proved)? Do the existing reductions have all their hypotheses proved?
3. Constructive steps (exhibit a circuit, a cover...) are worth a search; lower bounds in the families "Plane of order 3/4", "G11", "4-cycle-free" and "Petersen" have so far always been open research. Since 2026-11-26 `results.tsv` has a `category` column: so far merges came from `lower` and `reshape` steps, none from `upper` or `neg`.
3b. **Who works on what (the owner, 2026-11-26).** This session runs on Sonnet and does the triage, the C/SAT searches and every release. Writing the Lean proof is the only work handed to Fable (the owner, 2026-11-26: the most capable model, used only on kept steps): once triage says the step is provable (a merged neighbour proof to adapt, a circuit found, reductions all proved), start ONE subagent with the Agent tool, `model: "fable"`, `subagent_type: "general-purpose"`. Its brief carries everything it needs, since it sees nothing of this conversation: the worktree path, the step id, `gap.file`, the exact statement, the allowed imports, what triage found (neighbour file to copy, circuit, lemma names), the checker rules (no `sorry`, only `propext`/`Classical.choice`/`Quot.sound`, helpers inside `namespace <module>`, 512 KiB limit), and the goal: `tools/pnp.sh check <id>` ACCEPTED. Tell it to use the `lean-lsp` MCP tools (project `.mcp.json`, since 2026-11-26): `lean_diagnostic_messages` and `lean_goal` on the step file after each edit instead of a full build, `lean_multi_attempt` to try several tactics at once, `lean_local_search`/`lean_loogle`/`lean_leansearch` to find lemma names; `lean_build` is disabled (it could rebuild the shared clone), the final check stays `tools/pnp.sh check`. It must not submit, release or call the desk. Keep beating while it works. When it reports, check the build yourself, then submit. If it fails, release with the reason it found. Do not hand triage or searches to Fable.
3a. **Use the 30 minutes** (Orchestrator, 2026-11-27): release at triage only what is clearly out of reach (asymptotic lower bounds for every n, an open core whose cuts are merged, multi-day missing library theory: say which in the release note). Every other unit keeps working until ~25 min: Fable gets its whole budget, and a circuit search goes on after a weak quick search with the exact tools (circsat.py, Cirbo, seeded lsg/lst) on `fleet-tools/slots` cores under capmem. A unit released `other` / `out_of_time` is not offered back to us for 1 h, so an early release gives nothing back.
3b3. **No big file through lean-lsp** (Orchestrator, 2026-11-28: an LSP worker on a big proof reached 19.5 GB and OOM-killed Claude Desktop at 09:00 UTC; the MCP is now capped at 8G per session). Files over ~100 KB (Sol / CoreSearch engines, LRAT, cs8 output) are compiled with `fleet-tools/capmem -m 6G lake env lean <file>` from `lean/`, never opened with `lean_diagnostic_messages` / `lean_goal`; tell the Fable subagent the same.
3b2. **One `livegpx` at a time on the whole fleet** (Owner, 2026-11-27: two 4 GB livegpx + a 3.6 GB Lean build ran Claude Desktop out of memory at 16:40 UTC). Run it, and any other solver capped above 2G, as `flock $PENP/master/heavy.lock fleet-tools/capmem -m 4G ...`, and check `free -g` "disponible" >= 8 before a Lean build or a heavy run; never relaunch a killed run in a loop.
3c. **Unfinished but advanced = a cut, not a plain release** (the owner, 2026-11-27; join.txt REDUCTIONS, 15:48 UTC). If the lease says `reductions_open: true` (`terms` in `.pnp/<id>.json`) and you proved part of the step (e.g. the reduction from a merged sibling), then while you still hold it send `lean/PEqualNP/Outside/R_<prog>_<n>_<k>.lean`: one theorem `PEqualNP.Outside.R_<prog>_<n>_<k>` with 2 to 4 hypotheses (the missing lemmas, true, independent, each smaller than the step, none containing it, at most 2000 characters printed) whose conclusion is exactly the step's statement; no sorry, no other declarations, no namespace, the step's imports only; `tools/pnp.sh check` it, submit, then `release.sh <id> reduced`. A cut pays 1/4 of the price, once all its hypotheses are proved. A case split with neither side proved earns nothing. `reductions_open: false`: release as before.
4. Finish with `tools/pnp.sh submit <id>` (branch, commit, PR, release; only on the step Master leased to you, never `--unleased`: `submit` would otherwise take a lease of its own outside Master) or `$PENP/fleet-tools/release.sh <id> <reason> [blocker ids]` (`missing_lemma`, `statement_seems_false`, `out_of_time`, `does_not_elaborate`, `other`...; it calls `tools/pnp.sh release` and records the verdict in `master/verdicts.txt`, so no lane re-triages a re-offered copy). For `missing_lemma`, name the open steps it waits on (`release.sh L-meta-612 missing_lemma L-meta-1900`): the collector then hands the step back to a lane once they are merged. Give the verified reason, never one guessed from the title.
5. Tell Master: `<Lane> → Master : <id> terminée, <submitted PR url | relâchée (raison)>`, with one line on why. Master then reopens the lane.

If a beat answers 410, the lease is gone (step merged elsewhere or withdrawn): stop work on it and tell Master.
