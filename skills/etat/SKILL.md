---
name: etat
description: Read-only report, in French, of where the pequalnp fleet's research stands now - collector, units held per lane, today's PRs and points, outcomes, machine load, research and the Orchestrator's latest decisions. Use when the user types /etat [YYYY-MM-DD].
---

# /etat

Read-only: change nothing, take or release no lease, message no session.

1. Run `bash $PENP/fleet-tools/etat.sh [date]` (the argument, default today UTC). It prints the collector, the held
   units (slot, unit, points, level, kind, lease time, title), today's PRs with points merged / pending, today's
   outcomes from `results.tsv`, memory, load and solvers, recent `work/*/STATUS.md`, `master/long-true.txt` and the
   end of the Orchestrator journal.
2. Answer in French, short, in this order:
   - **Points**: merged today, pending in open PRs (with links `https://github.com/open-goat/pequalnp-proofs/pull/<n>`).
   - **En cours**: one table, lane | unité | points | depuis | sujet (title shortened).
   - **Bilan du jour**: submitted vs released, main release reasons.
   - **Machine**: available memory (warn under 8 GB), solvers, whether `heavy.lock` is held.
   - **Décisions récentes**: 2-4 lines from the journal, and the long true units kept for later.
   - Anything abnormal: collector stopped, a held unit with no lease time, memory under 4 GB, a lane holding a unit
     for more than 40 min.
3. No advice unless something is abnormal; then one line saying what and who should act (Master, Orchestrator, Harness).
