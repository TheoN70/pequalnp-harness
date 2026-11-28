#!/usr/bin/env bash
# Usage: grab.sh [interval_s]   (default 30)
# Reads desk/stats every interval; when a lane looks free and is not busy, asks desk/next for it
# (same query as tools/pnp.sh next --another [--hard]). On a lease: saves the raw JSON to leases/<id>.json,
# marks the lane busy (leases/busy-<lane>) and appends "LEASED <lane> <id> <path>" to leases/events.log.
# A busy lane is skipped until its busy file is removed (when the session says the step is finished).
# Every 10 min it also renews the lease of each busy lane, so a step survives a session that stops beating;
# it stops renewing a lease (and logs BEAT-END) once the desk refuses the beat (released, submitted, expired);
# BEAT-WITHDRAWN when that 410 says withdrawn: true (the unit was settled or stood down: do NOT submit it).
# When desk/next has nothing (gap null) it waits the retry_after_s the answer names (1..3600 s) before asking again.
#
# grab.sh --unit <id> [--proof] <lane|research>   (Master only; one shot, works beside a running collector)
#   leases that exact unit (desk/next &gap=<id>, as `pnp.sh next --unit`; with --proof, &have=proof as
#   `pnp.sh next --proof-of`: only with a checked proof in hand, passes even if another agent holds it, except one
#   that took it under 30 min ago). Writes leases/<id>.json and busy-<lane>, logs LEASED; the collector beats it.
#   No auto-release filter: Master chose this unit. Exit 4 = not leased (the desk's reason is printed).
#
# grab.sh --next <lane|researchN> [--kind prove|refute|search|cut|value] [--level warmup|solid|hard|open]
#   (Master only; one shot) leases the desk's next unit (desk/next &another=1 + filters) into that slot: writes
#   leases/<id>.json and busy-<slot>, logs LEASED. Nothing offered: logs EMPTY with retry_after_s, exit 5 (the caller
#   waits that long). A unit we already hold: UNIT-HELD, exit 6, never released. No auto-release filter, except
#   --skip-false-siblings: a RepSizeAtMost unit that `rep_lower_gen.py --is-false` shows false (counting, read-once DP,
#   or the generated Lean compiling; any doubt keeps it) is
#   released (other), logged SKIPPED-FALSE, its negation written to backup-proofs/refutes/<id>.lean; up to 5 asks, exit 7.
#   --skip-families: a unit whose title matches the regex SKIP_FAMILIES (default "One-a-side promise") is released (other),
#   logged SKIPPED-FAMILY, and the desk asked again (same 5 asks, exit 7).
DESK=${DESK:-https://pequalnp.com/desk}
OUT=$(dirname "$(readlink -f "$0")")/leases; mkdir -p "$OUT"
LOG="$OUT/events.log"; touch "$LOG"
H=TheoN70
NORMAL_LANES=${NORMAL_LANES:-normal normal2 normal3 normal4 hard normal5 normal6}   # The owner 2026-11-25 18:40: Hard takes ordinary steps
# AUTO_LANES (Orchestrator 2026-11-27, e.g. "auto1 auto2 auto3 auto4 auto5 auto6 auto7"): slots with no session; their
# unit goes to autosolve only and is released at once when it fails. Never more held units than the desk's `capacity`.
AUTO_LANES=${AUTO_LANES:-}
export SLOTS_RANGE=${SLOTS_RANGE:-0-13}   # autosolve runs (and lanes): all 14 cores; SLOTS_RANGE=0-7 when a Research session holds 8-13
log() { echo "$(date -u +%H:%M:%S) $*" >> "$LOG"; }
# After each LEASED: fleet-tools/autosolve.sh in the background (AUTO=0 to stop). Logs AUTO-START, then AUTO-SUBMITTED
# (PR sent, lease released by submit, busy file removed: the slot is free) or AUTO-FAIL rc=1|2|3 (unit left to its lane).
auto() { # $1 = lane, $2 = id
  # the desk's capacity, from every lease answer (12 on 2026-11-27, "grows as your proofs are checked")
  python3 -I -c 'import json,sys; c=json.load(open(sys.argv[1])).get("capacity"); print(int(c)) if type(c) is int and 0 < c < 1000 else sys.exit(1)' \
    "$OUT/$2.json" > "$OUT/.cap" 2>/dev/null && mv "$OUT/.cap" "$OUT/capacity"
  [ "${AUTO:-1}" = 0 ] && return
  # on AUTO-FAIL: an AUTO_LANES slot always releases; a NORMAL_LANES lane releases an open/hard unit (no LLM time on
  # it, Orchestrator 2026-11-27: L-meta-10009 open blocked a lane 30 min); any other slot (research...) keeps it
  local mode=keep
  case " $NORMAL_LANES " in *" $1 "*) mode=normal;; esac
  case " $AUTO_LANES " in *" $1 "*) mode=auto;; esac
  log "AUTO-START $1 $2"
  # setsid: survives the end of a --unit / --next call; fds 8 and 9 closed so the locks stay with the collector
  setsid bash -c 'o=$1 l=$2 i=$3 mode=$4 desk=$5 normal=$6
    lg() { echo "$(date -u +%H:%M:%S) $*" >> "$o/events.log"; }
    "$o/../../fleet-tools/autosolve.sh" "$o/$i.json" > "$o/auto-$i.log" 2>&1; rc=$?
    if [ $rc = 0 ]; then [ "$(cat "$o/busy-$l" 2>/dev/null)" = "$i" ] && rm -f "$o/busy-$l"; lg "AUTO-SUBMITTED $l $i"; exit; fi
    lg "AUTO-FAIL $l $i rc=$rc (log leases/auto-$i.log)"
    # rc 4 (false at the bound): its Lean negation when a generator covers it, beside the release (not delaying it)
    [ $rc = 4 ] && { r=$o/../backup-proofs/refutes; mkdir -p "$r" && "$o/../../fleet-tools/refutable.sh" "$o/$i.json" "$r/$i.lean" &&
      lg "REFUTABLE $l $i (negation in backup-proofs/refutes/$i.lean, not compiled)"; } &
    read -r lease lvl < <(python3 -I -c "import json,sys; d=json.load(open(sys.argv[1])); print(d[\"lease\"][\"id\"], ((d[\"lease\"].get(\"terms\") or {}).get(\"level\") or d[\"gap\"].get(\"level\") or \"-\"))" "$o/$i.json")
    [ "$mode" = auto ] || { [ "$mode" = normal ] && { [ "$lvl" = open ] || [ "$lvl" = hard ]; }; } || exit
    [ "$(cat "$o/busy-$l" 2>/dev/null)" = "$i" ] || exit   # Master already moved it on
    # rc 2 or 3 (nothing found in 2 min, or a family autosolve does not know) on an auto slot: a free NORMAL_LANES lane
    # takes it (30 min, Master BAILs on the LEASED line) instead of a release (Orchestrator 2026-11-27: L-meta-20213,
    # 65 pts, released with 3 lanes free)
    if [ "$mode" = auto ] && { [ $rc = 2 ] || [ $rc = 3 ]; }; then
      exec 8>"$o/manager.lock"; flock 8
      for n in $normal; do [ -s "$o/busy-$n" ] && continue
        echo "$i" > "$o/busy-$n"; rm -f "$o/busy-$l"; lg "AUTO-HANDOFF $l $n $i (rc=$rc)"; lg "LEASED $n $i $o/$i.json"; exit; done
      exec 8>&-
    fi
    why=other; [ $rc = 4 ] && why=statement_seems_false   # rc 4: circsat UNSAT, no circuit within the bound
    [[ "$lease" =~ ^[0-9a-f-]{36}$ ]] && curl -sS --max-time 20 -X POST "$desk/release?lease=$lease&reason=$why" >/dev/null 2>&1
    rm -f "$o/busy-$l"; lg "AUTO-RELEASED $l $i $why (level $lvl, rc=$rc)"' _ "$OUT" "$1" "$2" "$mode" "$DESK" "$NORMAL_LANES" 9>&- 8>&- </dev/null >/dev/null 2>&1 &
}
if [ "${1:-}" = --unit ]; then
  id=${2:-}; shift 2 2>/dev/null; q="&gap=$id"; how=unit
  [ "${1:-}" = --proof ] && { q="$q&have=proof"; how=proof; shift; }
  lane=${1:-}
  [[ "$id" =~ ^L-[a-z]+-[0-9]+$ ]] && [[ "$lane" =~ ^[a-z0-9]+$ ]] || { echo "usage: grab.sh --unit <L-xxx-N> [--proof] <lane|research>" >&2; exit 1; }
  [ -s "$OUT/busy-$lane" ] && { echo "busy-$lane already holds $(cat "$OUT/busy-$lane")" >&2; exit 1; }
  exec 8>"$OUT/manager.lock"; flock 8
  f="$OUT/.unit.json"
  curl -sS --max-time 20 "$DESK/next?handle=$H&another=1&value=1&model=${PNP_MODEL:-claude-sonnet-5-5}$q" > "$f" 2>/dev/null || { echo "desk unreachable" >&2; exit 1; }
  got=$(python3 -I -c 'import json,re,sys; g=json.load(open(sys.argv[1])).get("gap"); print(g["id"] if isinstance(g,dict) and re.fullmatch(r"L-[a-z]+-\d+", str(g.get("id",""))) else "")' "$f" 2>/dev/null)
  if [ "$got" != "$id" ]; then
    if [ -n "$got" ] && grep -qxF "$got" "$OUT"/busy-* 2>/dev/null; then  # a unit we already hold: never release it
      log "UNIT-HELD $lane $got (asked $id)"
    elif [ -n "$got" ]; then  # the desk answered another unit: never keep it
      lease=$(python3 -I -c 'import json,sys; print(json.load(open(sys.argv[1]))["lease"]["id"])' "$f" 2>/dev/null)
      curl -sS --max-time 20 -X POST "$DESK/release?lease=$lease&reason=other" >/dev/null 2>&1; log "RELEASED $lane $got other (asked $id)"
    fi
    why=$(python3 -I -c 'import json,re,sys; d=json.load(open(sys.argv[1])); print(re.sub(r"[^ -~]"," ",str(d.get("note") or d.get("error") or "no reason given"))[:300])' "$f" 2>/dev/null)
    log "UNIT-REFUSED $lane $id ($how)"; echo "not leased: $id: $why" >&2; exit 4
  fi
  mv "$f" "$OUT/$id.json"; echo "$id" > "$OUT/busy-$lane"
  log "LEASED $lane $id $OUT/$id.json (Master, --unit $how)"; auto "$lane" "$id"
  echo "leased $id for $lane: $OUT/$id.json"; pgrep -f "master/grab.sh [0-9]" >/dev/null || echo "collector not running: start it (bash master/grab.sh 15) so the lease is beaten" >&2
  exit 0
fi
if [ "${1:-}" = --next ]; then
  lane=${2:-}; shift 2 2>/dev/null; q=""; skip=0; skipfam=0
  while [ $# -gt 0 ]; do
    case "$1" in
      --kind) [[ "${2:-}" =~ ^(prove|refute|search|cut|value)$ ]] || { echo "--kind prove|refute|search|cut|value" >&2; exit 1; }; q="$q&kind=$2"; shift 2 ;;
      --level) [[ "${2:-}" =~ ^(warmup|solid|hard|open)$ ]] || { echo "--level warmup|solid|hard|open" >&2; exit 1; }; q="$q&level=$2"; shift 2 ;;
      --skip-false-siblings) skip=1; shift ;;
      --skip-families) skipfam=1; shift ;;
      *) echo "usage: grab.sh --next <lane|researchN> [--kind K] [--level L] [--skip-false-siblings] [--skip-families]" >&2; exit 1 ;;
    esac
  done
  [[ "$lane" =~ ^[a-z0-9]+$ ]] || { echo "usage: grab.sh --next <lane|researchN> [--kind K] [--level L]" >&2; exit 1; }
  [ -s "$OUT/busy-$lane" ] && { echo "busy-$lane already holds $(cat "$OUT/busy-$lane")" >&2; exit 1; }
  exec 8>"$OUT/manager.lock"; flock 8
  f="$OUT/.next.json"; here=$(dirname "$(readlink -f "$0")")
  for attempt in 1 2 3 4 5; do  # with --skip-false-siblings: up to 5 asks, each false sibling handed back at once
    curl -sS --max-time 20 "$DESK/next?handle=$H&another=1&model=${PNP_MODEL:-claude-sonnet-5-5}$q" > "$f" 2>/dev/null || { echo "desk unreachable" >&2; exit 1; }
    read -r got retry_s <<< "$(python3 -I -c 'import json,re,sys; d=json.load(open(sys.argv[1])); g=d.get("gap"); ok=isinstance(g,dict) and re.fullmatch(r"L-[a-z]+-\d+", str(g.get("id",""))); w=d.get("retry_after_s"); print(g["id"] if ok else "-", w if type(w) is int and 1 <= w <= 3600 else 300)' "$f" 2>/dev/null)"
    if [ "${got:--}" = - ]; then  # nothing offered: say when to ask again (the caller waits, this is one shot)
      log "EMPTY $lane retry_after_s=$retry_s ($q)"; echo "nothing offered; ask again in $retry_s s" >&2; exit 5
    fi
    if grep -qxF "$got" "$OUT"/busy-* 2>/dev/null; then  # a unit we already hold: never release it
      log "UNIT-HELD $lane $got (--next)"; echo "desk answered $got, already held: nothing new" >&2; exit 6
    fi
    lease=$(python3 -I -c 'import json,sys; print(json.load(open(sys.argv[1]))["lease"]["id"])' "$f" 2>/dev/null)
    # --skip-families: a unit whose title matches SKIP_FAMILIES (the owner, 2026-11-26: One-a-side is never worth it)
    if [ $skipfam = 1 ] && python3 -I -c 'import json,re,sys; sys.exit(0 if re.search(sys.argv[2], str(json.load(open(sys.argv[1]))["gap"].get("title",""))) else 1)' \
        "$f" "${SKIP_FAMILIES:-One-a-side promise}" 2>/dev/null; then
      curl -sS --max-time 20 -X POST "$DESK/release?lease=$lease&reason=other" >/dev/null 2>&1
      log "SKIPPED-FAMILY $lane $got other (title matches SKIP_FAMILIES)"; echo "skipped family unit $got" >&2
      [ $attempt = 5 ] && { echo "5 skipped units in a row: try again later" >&2; exit 7; }
      continue
    fi
    # A RepSizeAtMost sibling that rep_lower_gen.py --is-false shows false (not just k <= |R|: 541059:8 is true): keep the
    # negation's Lean (not compiled) for a refute unit, hand the unit back (other), ask again.
    [ $skip = 1 ] && mkdir -p "$here/backup-proofs/refutes" && \
      python3 -I "$here/../fleet-tools/rep_lower_gen.py" --is-false "$f" -o "$here/backup-proofs/refutes/$got.lean" 2>/dev/null || break
    curl -sS --max-time 20 -X POST "$DESK/release?lease=$lease&reason=other" >/dev/null 2>&1
    log "SKIPPED-FALSE $lane $got other (shown false; negation in backup-proofs/refutes/$got.lean)"
    echo "skipped false sibling $got" >&2
    [ $attempt = 5 ] && { echo "5 skipped units in a row: try again later" >&2; exit 7; }
  done
  mv "$f" "$OUT/$got.json"; echo "$got" > "$OUT/busy-$lane"
  log "LEASED $lane $got $OUT/$got.json (Master, --next$q)"; auto "$lane" "$got"
  echo "leased $got for $lane: $OUT/$got.json"; pgrep -f "master/grab.sh [0-9]" >/dev/null || echo "collector not running: start it (bash master/grab.sh 15) so the lease is beaten" >&2
  exit 0
fi
# One collector at a time, including when Master restarts it.
exec 9>"$OUT/collector.lock"
flock -n 9 || { echo "collector already running" >&2; exit 0; }
exec 8>"$OUT/manager.lock"
N=${1:-30}; LANES="$NORMAL_LANES $AUTO_LANES"   # round robin over both; capacity (leases/capacity) caps the held units
next_normal=0; next_hard=0; hourly=$(( $(date +%s) + 3600 ))
try_unlocked() { # $1 = lane, $2 = extra query; returns 1 when the desk had nothing for us
  [ -e "$OUT/busy-$1" ] && return 1
  f="$OUT/.last.json"; retry_s=300
  curl -sS --max-time 20 "$DESK/next?handle=$H&another=1&model=${PNP_MODEL:-claude-sonnet-5-5}$2" > "$f" 2>/dev/null || return 1
  # a step this handle already holds (note "already hold") belongs to the other session: never hand it on
  # gap null: the answer names when to ask again (retry_after_s, 1..3600 s); the caller waits that long
  read -r id retry_s <<< "$(python3 -c 'import json,re,sys; d=json.load(open(sys.argv[1])); g=d.get("gap"); ok=g and re.fullmatch(r"L-[a-z]+-\d+", g.get("id","")); w=d.get("retry_after_s"); print(g["id"] if ok else "-", w if type(w) is int and 1 <= w <= 3600 else 300)' "$f" 2>/dev/null)"
  [ -z "$id" ] || [ "$id" = - ] && return 1
  # at its cap the desk hands back a step we already hold (note "release one to get another"): never give it to a 2nd lane
  # the desk re-issues that step under a NEW lease id (the old one then answers 410): keep the new one so beats keep working
  grep -qxF "$id" "$OUT"/busy-* 2>/dev/null && { mv "$f" "$OUT/$id.json"; log "CAPPED $1 $id already held, lease re-issued"; return 1; }
  if python3 -c 'import json,sys; sys.exit(0 if "already hold" in str(json.load(open(sys.argv[1])).get("note","")) else 1)' "$f"; then
    cp "$f" "$OUT/unassigned-$id.json"; log "RECONCILE $id held outside known lanes"; return 1
  fi
  mv "$f" "$OUT/$id.json"
  # verdicts (master/verdicts.txt, "<id> <reason> [blocker ids]"), read on every lease, no restart needed.
  # Lanes append their own releases there (fleet-tools/release.sh). A verdict with blockers (missing_lemma
  # waiting on other steps) stops applying once every blocker's file is on upstream main: the step goes to a lane.
  vline=$(awk -v i="$id" '$1==i{print; exit}' "$(dirname "$OUT")/verdicts.txt" 2>/dev/null)
  read -r _ why blockers <<< "$vline"; unblocked=
  # out_of_time / other say nothing about the statement: a re-offered unit goes to a lane again (Orchestrator 2026-11-27)
  case "$why" in out_of_time|other) why=; blockers= ;; esac
  if [ -n "$why" ] && [ -n "$blockers" ]; then
    open_b=""
    for b in $blockers; do
      gh api "repos/open-goat/pequalnp-proofs/contents/lean/PEqualNP/Outside/${b//-/_}.lean" --silent 2>/dev/null || open_b="$open_b $b"
    done
    [ -z "$open_b" ] && { log "UNBLOCKED $1 $id ($blockers merged)"; why=; unblocked=1; }
  fi
  # open families (always released missing_lemma by Master on 2026-11-25): match on the title
  [ -z "$why" ] && [ -z "$unblocked" ] && python3 -c 'import json,re,sys; t=json.load(open(sys.argv[1]))["gap"]["title"]; sys.exit(0 if re.search(r"[Pp]lane of order [34]|[Oo]rder[- ][34] plane|plane of order q|Fano plane: no circuit of at most 27|4-cycle-free|No-4-cycle|no cycle shorter than 5|G11|Petersen|Cubic piece, cycles|^Conjecture|^No AND/OR(/NOT)? circuit .* computes the edge function|^Resolution on the pigeonhole formula with 5 pigeons and 4 holes: (no refutation has at most 1[1-5][0-9]|some refutation has at most (1[1-4][0-9]|15[0-8])) lines|^Res\(⊕\) on the pigeonhole formula with 5 pigeons and 4 holes: (some|no) refutation has at most (1[0-4][0-9]|15[0-6]) lines", t) else 1)' "$OUT/$id.json" && why=missing_lemma
  # PM 3x3 lower-bound cases (Orchestrator 2026-11-27): true or not, no Lean route fits (LRAT at n=9 >> 512 KiB), and
  # they filled all 6 lanes. OFF by default since merged templates exist (L_meta_27743, L_meta_27763): SKIP_PM3=1 to skip.
  [ -z "$why" ] && [ "${SKIP_PM3:-0}" = 1 ] && python3 -c 'import json,sys; t=json.load(open(sys.argv[1]))["gap"]["title"]; sys.exit(0 if t.startswith("Perfect matching on a 3 by 3 graph: no normal-form circuit") else 1)' "$OUT/$id.json" && why=other
  # FoldExtra/SyntacticFold defs absent from main (2026-11-26, 17774/17746): drop this line once they merge
  [ -z "$why" ] && python3 -c 'import json,sys; s=str(json.load(open(sys.argv[1]))["gap"].get("statement","")); sys.exit(0 if ("FoldExtra." in s or "SyntacticFold." in s) else 1)' "$OUT/$id.json" && why=does_not_elaborate
  # a negated step whose twin is merged upstream with exactly the negated statement is false (the owner's go, 2026-11-25)
  if [ -z "$why" ] && python3 -I "$(dirname "$(readlink -f "$0")")/twin_merged.py" "$OUT/$id.json"; then
    why=statement_seems_false
  fi
  # a step whose own PR is already open (someone else's) cannot be submitted by us: hand it back at once
  if [ -z "$why" ] && [ "$(gh pr list -R open-goat/pequalnp-proofs --state open --search "$id in:title" --json title --jq "[.[]|select(.title==\"$id\")]|length" 2>/dev/null)" -gt 0 ] 2>/dev/null; then
    why=other
  fi
  # The owner 2026-11-25 ~21:10: a negation whose positive twin (id - 1) already has someone else's open PR cannot give us a PR:
  # hand it back unjudged ("other") instead of spending a lane on it
  if [ -z "$why" ] && python3 -c 'import json,sys; t=json.load(open(sys.argv[1]))["gap"]["title"]; sys.exit(0 if t.startswith(("False:","It is false that")) else 1)' "$OUT/$id.json"; then
    twin="L-meta-$(( ${id#L-meta-} - 1 ))"
    [ "$(gh pr list -R open-goat/pequalnp-proofs --state open --search "$twin in:title" --json title --jq "[.[]|select(.title==\"$twin\")]|length" 2>/dev/null)" -gt 0 ] 2>/dev/null && why=other
  fi
  # The owner 2026-11-26 06:50: prioritise lower/reshape. upper (0/37 merged) and neg (0/169) go back unjudged ("other"), never to a lane.
  # ponytail: category.py title regexes; set SKIP_CATS= to lift the rule.
  if [ -z "$why" ] && [ -z "$unblocked" ]; then cat=$(python3 -I "$(dirname "$OUT")/../fleet-tools/category.py" "$OUT/$id.json" 2>/dev/null); case " ${SKIP_CATS-upper neg} " in *" ${cat#cut/} "*) why=other; log "SKIPPED $1 $id category=$cat";; esac; fi
  if [ -n "$why" ]; then
    lease=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["lease"]["id"])' "$OUT/$id.json")
    curl -sS --max-time 20 -X POST "$DESK/release?lease=$lease&reason=$why" >/dev/null 2>&1
    log "RELEASED $1 $id $why"
    [ "$id" = "$last_rel" ] && return 1   # the desk re-offers the same step: back off as usual
    last_rel=$id; return 2   # the desk did offer something: ask again on the next tick, no backoff
  fi
  echo "$id" > "$OUT/busy-$1"   # the busy file names the step, so beat() knows which lease to renew
  echo "$1" > "$OUT/last-assigned"
  log "LEASED $1 $id $OUT/$id.json"; auto "$1" "$id"
}
beat_unlocked() { # renew the lease of each busy lane; stop renewing it once the desk says it is over (410 etc.)
  for b in "$OUT"/busy-*; do
    [ -e "$b" ] || continue
    id=$(cat "$b"); [ -n "$id" ] && [ -e "$OUT/$id.json" ] || continue
    lease=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["lease"]["id"])' "$OUT/$id.json" 2>/dev/null)
    code=$(curl -sS --max-time 20 -o "$OUT/.beat.json" -w '%{http_code}' -X POST "$DESK/beat?lease=$lease" 2>/dev/null)
    if [ "$code" = 410 ]; then
      : > "$b"
      if python3 -c 'import json,sys; sys.exit(0 if json.load(open(sys.argv[1])).get("withdrawn") is True else 1)' "$OUT/.beat.json" 2>/dev/null; then
        log "BEAT-WITHDRAWN ${b##*/busy-} $id (settled or stood down: do not submit)"
      else log "BEAT-END ${b##*/busy-} $id http=$code"; fi
    elif [ "$code" != 200 ]; then log "BEAT-ERROR ${b##*/busy-} $id http=$code"; fi
  done
}
orphans_unlocked() { # an auto slot whose autosolve died (killed at 04:50 on 2026-11-28: 5 slots beaten 2.5 h, nobody
  # working): busy file older than 10 min and no autosolve.sh for its unit -> a free NORMAL_LANES lane takes it, else released
  local s b id n lease
  for s in $AUTO_LANES; do b=$OUT/busy-$s; [ -s "$b" ] || continue; id=$(cat "$b")
    [ -n "$(find "$b" -mmin +10)" ] && ! pgrep -f "autosolve.sh .*$id\.json" >/dev/null || continue
    log "AUTO-ORPHAN $s $id"
    for n in $NORMAL_LANES; do [ -s "$OUT/busy-$n" ] && continue
      echo "$id" > "$OUT/busy-$n"; rm -f "$b"; log "AUTO-HANDOFF $s $n $id (orphan)"; log "LEASED $n $id $OUT/$id.json"; continue 2; done
    lease=$(python3 -I -c 'import json,sys; print(json.load(open(sys.argv[1]))["lease"]["id"])' "$OUT/$id.json" 2>/dev/null)
    [[ "$lease" =~ ^[0-9a-f-]{36}$ ]] && curl -sS --max-time 20 -X POST "$DESK/release?lease=$lease&reason=other" >/dev/null 2>&1
    rm -f "$b"; log "AUTO-RELEASED $s $id other (orphan)"
  done
}
next_free() { # round robin: first lane without a busy file, after the last one assigned; none at the desk's capacity
  local last l on= cap
  cap=$(cat "$OUT/capacity" 2>/dev/null)
  [ -n "$cap" ] && [ "$(cat "$OUT"/busy-* 2>/dev/null | grep -c .)" -ge "$cap" ] && return
  last=$(cat "$OUT/last-assigned" 2>/dev/null)
  case " $LANES " in *" $last "*) ;; *) on=1;; esac
  # all NORMAL_LANES busy: no lease for an auto slot either, its rc 2/3 would be released and lost for 1 h
  # (Owner/Orchestrator 2026-11-27: 6 solid units lost in a minute). ponytail: also pauses autosolve families then.
  local lane_free= n; for n in $NORMAL_LANES; do [ -e "$OUT/busy-$n" ] || lane_free=1; done
  for l in $LANES $LANES; do
    [ -z "$lane_free" ] && case " $AUTO_LANES " in *" $l "*) [ "$l" = "$last" ] && on=1; continue;; esac
    [ -n "$on" ] && [ ! -e "$OUT/busy-$l" ] && { echo "$l"; return; }
    [ "$l" = "$last" ] && on=1
  done
}
try() { flock 8; try_unlocked "$@"; local rc=$?; flock -u 8; return "$rc"; }
beat() { flock 8; orphans_unlocked; beat_unlocked; flock -u 8; }
next_beat=0
log "START interval=${N}s"
beat
next_beat=$(( $(date +%s) + 300 ))
while true; do
  now=$(date +%s)
  r=$(curl -sS --max-time 15 -w '\n%{http_code}' "$DESK/stats" 2>/dev/null); code=${r##*$'\n'}; r=$(printf '%s' "${r%$'\n'*}" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["offerable_now_ordinary"], d["offerable_now"]-d["offerable_now_ordinary"])' 2>/dev/null)
  set -- $r; n=${1:-0}; h=${2:-0}
  # normal lanes: one per session working on normal steps (normal = session Normal, normal2 = the next one)
  free=$(next_free)
  if [ -n "$free" ] && [ "$n" -gt 0 ] && [ "$now" -ge "$next_normal" ]; then
    try "$free" ""; [ $? -eq 1 ] && next_normal=$(( now + ${retry_s:-300} ))   # the desk's retry_after_s, else 300 s
  fi
  if [ -n "${HARD_STEPS:-}" ] && [ ! -e "$OUT/busy-hard" ] && { [ "$h" -ge 5 ] || [ "$now" -ge "$hourly" ]; } && [ "$now" -ge "$next_hard" ]; then
    hourly=$(( now + 3600 )); try hard "&hard=1" || next_hard=$(( now + ${retry_s:-300} ))
  fi
  if [ "$now" -ge "$next_beat" ]; then beat; next_beat=$(( now + 300 )); fi   # lease lasts 20 min, renew every 10
  # Fast poll during a wave (Orchestrator 2026-11-27): 5 s while ordinary units are offered and a lane is free, the
  # usual N otherwise; a 429 from the desk (rate limit) waits 60 s. ponytail: FAST_S=5, raise it if 429s show up.
  if [ "$code" = 429 ]; then log "RATE-LIMITED stats http=429"; sleep 60
  elif [ -n "$(next_free)" ] && [ "$n" -gt 0 ]; then sleep "${FAST_S:-5}"; else sleep "$N"; fi
done
