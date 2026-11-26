# pequalnp harness

`$PENP` is the fleet root: the folder that holds `harness/`, the `pequalnp-*` clones and `work/` (sessions start in it). In a shell where it is unset, `export PENP=<that folder>` first.

The tooling that runs a fleet of Claude sessions proving Lean 4 steps for https://pequalnp.com
(GitHub account TheoN70). The Lean proofs themselves live in `TheoN70/pequalnp-proofs`, not here.

| Path | What |
|---|---|
| `master/grab.sh` | the lease collector: polls the desk, leases a step for the next free lane, beats, auto-releases known verdicts |
| `master/twin_merged.py` | auto-triage of negations whose twin is merged upstream |
| `master/join-<date>.txt` | baseline of the desk's instructions, to diff against the current ones |
| `fleet-tools/` | search tools (C exact/local searches, SAT, LRAT, generators) and the lanes' playbook `README.md` |
| `skills/` | the Claude skills `/pequalnp-master`, `/pequalnp-lane`, `/pequalnp-hard` |

## Layout on disk

The harness expects to sit in `$PENP/harness/`, next to the clones it drives:

    penp/
      harness/                this repository
      master -> harness/master            (paths used by the skills)
      fleet-tools -> harness/fleet-tools
      .claude/skills -> ../harness/skills
      pequalnp-proofs/        clone of TheoN70/pequalnp-proofs (lane hard)
      pequalnp-normal*/       one worktree per worker lane (absent while lanes are closed; the lane skill recreates it)
      work/<id>/              scratch for one step
      results.tsv             one line per lease

## Setup

    make -C fleet-tools
    python3 -m venv fleet-tools/sat-venv && fleet-tools/sat-venv/bin/pip install -r fleet-tools/requirements.txt
    cd .. && ln -s harness/master master && ln -s harness/fleet-tools fleet-tools && mkdir -p .claude && ln -s ../harness/skills .claude/skills

Then start the collector from the Master session: `bash master/grab.sh 15`.

## Dashboard

    python3 dashboard/serve.py        # http://127.0.0.1:8377/

Live local view of the research, lanes, machine load, outcomes and tool use. See `CLAUDE.md`.
