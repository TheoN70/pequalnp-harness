#!/usr/bin/env bash
# Usage: grab.sh [interval_s]   (default 30)
# Reads desk/stats every interval; when a lane looks free and is not busy, asks desk/next for it
# (same query as tools/pnp.sh next --another [--hard]). On a lease: saves the raw JSON to leases/<id>.json,
# marks the lane busy (leases/busy-<lane>) and appends "LEASED <lane> <id> <path>" to leases/events.log.
# A busy lane is skipped until its busy file is removed (when the session says the step is finished).
# Every 10 min it also renews the lease of each busy lane, so a step survives a session that stops beating;
# it stops renewing a lease (and logs BEAT-END) once the desk refuses the beat (released, submitted, expired).
DESK=https://pequalnp.com/desk
OUT=$(dirname "$(readlink -f "$0")")/leases; mkdir -p "$OUT"
LOG="$OUT/events.log"; touch "$LOG"
# One collector at a time, including when Master restarts it.
exec 9>"$OUT/collector.lock"
flock -n 9 || { echo "collector already running" >&2; exit 0; }
exec 8>"$OUT/manager.lock"
H=TheoN70; N=${1:-30}; NORMAL_LANES=${NORMAL_LANES:-normal normal2 normal3 normal4 hard normal5 normal6}   # Théo 2026-11-25 18:40: Hard takes ordinary steps   # ponytail: the desk caps a handle at 5 held steps, so 4 normal + 1 hard is the max
next_normal=0; next_hard=0; hourly=$(( $(date +%s) + 3600 ))
log() { echo "$(date -u +%H:%M:%S) $*" >> "$LOG"; }
try_unlocked() { # $1 = lane, $2 = extra query; returns 1 when the desk had nothing for us
  [ -e "$OUT/busy-$1" ] && return 1
  f="$OUT/.last.json"
  curl -sS --max-time 20 "$DESK/next?handle=$H&another=1&model=${PNP_MODEL:-claude-sonnet-5-5}$2" > "$f" 2>/dev/null || return 1
  # a step this handle already holds (note "already hold") belongs to the other session: never hand it on
  id=$(python3 -c 'import json,re,sys; d=json.load(open(sys.argv[1])); g=d.get("gap"); ok=g and re.fullmatch(r"L-[a-z]+-\d+", g.get("id","")); print(g["id"] if ok else "")' "$f" 2>/dev/null)
  [ -z "$id" ] && return 1
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
  if [ -n "$why" ] && [ -n "$blockers" ]; then
    open_b=""
    for b in $blockers; do
      gh api "repos/open-goat/pequalnp-proofs/contents/lean/PEqualNP/Outside/${b//-/_}.lean" --silent 2>/dev/null || open_b="$open_b $b"
    done
    [ -z "$open_b" ] && { log "UNBLOCKED $1 $id ($blockers merged)"; why=; unblocked=1; }
  fi
  # open families (always released missing_lemma by Master on 2026-11-25): match on the title
  [ -z "$why" ] && [ -z "$unblocked" ] && python3 -c 'import json,re,sys; t=json.load(open(sys.argv[1]))["gap"]["title"]; sys.exit(0 if re.search(r"[Pp]lane of order [34]|Order-[34] plane|plane of order q|Fano plane: no circuit of at most 27|4-cycle-free|No-4-cycle|no cycle shorter than 5|G11|Petersen|Cubic piece, cycles|^Conjecture|^No AND/OR(/NOT)? circuit .* computes the edge function|^Resolution on the pigeonhole formula with 5 pigeons and 4 holes: (no refutation has at most 1[1-5][0-9]|some refutation has at most (1[1-4][0-9]|15[0-8])) lines|^Res\(⊕\) on the pigeonhole formula with 5 pigeons and 4 holes: (some|no) refutation has at most (1[0-4][0-9]|15[0-6]) lines", t) else 1)' "$OUT/$id.json" && why=missing_lemma
  # FoldExtra/SyntacticFold defs absent from main (2026-11-26, 17774/17746): drop this line once they merge
  [ -z "$why" ] && python3 -c 'import json,sys; s=str(json.load(open(sys.argv[1]))["gap"].get("statement","")); sys.exit(0 if ("FoldExtra." in s or "SyntacticFold." in s) else 1)' "$OUT/$id.json" && why=does_not_elaborate
  # a negated step whose twin is merged upstream with exactly the negated statement is false (Théo's go, 2026-11-25)
  if [ -z "$why" ] && python3 -I "$(dirname "$(readlink -f "$0")")/twin_merged.py" "$OUT/$id.json"; then
    why=statement_seems_false
  fi
  # a step whose own PR is already open (someone else's) cannot be submitted by us: hand it back at once
  if [ -z "$why" ] && [ "$(gh pr list -R open-goat/pequalnp-proofs --state open --search "$id in:title" --json title --jq "[.[]|select(.title==\"$id\")]|length" 2>/dev/null)" -gt 0 ] 2>/dev/null; then
    why=other
  fi
  # Théo 2026-11-25 ~21:10: a negation whose positive twin (id - 1) already has someone else's open PR cannot give us a PR:
  # hand it back unjudged ("other") instead of spending a lane on it
  if [ -z "$why" ] && python3 -c 'import json,sys; t=json.load(open(sys.argv[1]))["gap"]["title"]; sys.exit(0 if t.startswith(("False:","It is false that")) else 1)' "$OUT/$id.json"; then
    twin="L-meta-$(( ${id#L-meta-} - 1 ))"
    [ "$(gh pr list -R open-goat/pequalnp-proofs --state open --search "$twin in:title" --json title --jq "[.[]|select(.title==\"$twin\")]|length" 2>/dev/null)" -gt 0 ] 2>/dev/null && why=other
  fi
  # Théo 2026-11-26 06:50: prioritise lower/reshape. upper (0/37 merged) and neg (0/169) go back unjudged ("other"), never to a lane.
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
  log "LEASED $1 $id $OUT/$id.json"
}
beat_unlocked() { # renew the lease of each busy lane; stop renewing it once the desk says it is over (410 etc.)
  for b in "$OUT"/busy-*; do
    [ -e "$b" ] || continue
    id=$(cat "$b"); [ -n "$id" ] && [ -e "$OUT/$id.json" ] || continue
    lease=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["lease"]["id"])' "$OUT/$id.json" 2>/dev/null)
    code=$(curl -sS --max-time 20 -o /dev/null -w '%{http_code}' -X POST "$DESK/beat?lease=$lease" 2>/dev/null)
    if [ "$code" = 410 ]; then
      : > "$b"; log "BEAT-END ${b##*/busy-} $id http=$code"
    elif [ "$code" != 200 ]; then log "BEAT-ERROR ${b##*/busy-} $id http=$code"; fi
  done
}
next_free() { # round robin: first lane without a busy file, after the last one assigned
  local last l on=
  last=$(cat "$OUT/last-assigned" 2>/dev/null)
  case " $NORMAL_LANES " in *" $last "*) ;; *) on=1;; esac
  for l in $NORMAL_LANES $NORMAL_LANES; do
    [ -n "$on" ] && [ ! -e "$OUT/busy-$l" ] && { echo "$l"; return; }
    [ "$l" = "$last" ] && on=1
  done
}
try() { flock 8; try_unlocked "$@"; local rc=$?; flock -u 8; return "$rc"; }
beat() { flock 8; beat_unlocked; flock -u 8; }
next_beat=0
log "START interval=${N}s"
beat
next_beat=$(( $(date +%s) + 300 ))
while true; do
  now=$(date +%s)
  r=$(curl -sS --max-time 15 "$DESK/stats" 2>/dev/null | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["offerable_now_ordinary"], d["offerable_now"]-d["offerable_now_ordinary"])' 2>/dev/null)
  set -- $r; n=${1:-0}; h=${2:-0}
  # normal lanes: one per session working on normal steps (normal = session Normal, normal2 = the next one)
  free=$(next_free)
  if [ -n "$free" ] && [ "$n" -gt 0 ] && [ "$now" -ge "$next_normal" ]; then
    try "$free" ""; [ $? -eq 1 ] && next_normal=$(( now + 300 ))   # desk asks for 300 s between next calls
  fi
  if [ -n "${HARD_STEPS:-}" ] && [ ! -e "$OUT/busy-hard" ] && { [ "$h" -ge 5 ] || [ "$now" -ge "$hourly" ]; } && [ "$now" -ge "$next_hard" ]; then
    hourly=$(( now + 3600 )); try hard "&hard=1" || next_hard=$(( now + 300 ))
  fi
  if [ "$now" -ge "$next_beat" ]; then beat; next_beat=$(( now + 300 )); fi   # lease lasts 20 min, renew every 10
  sleep "$N"
done
