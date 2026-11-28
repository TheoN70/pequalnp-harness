#!/usr/bin/env python3
"""family_watch.py: flag a desk family we keep releasing or autosolve does not cover (read-only, sends nothing).

usage: python3 -I family_watch.py [--min 20] [--minutes 60] [--no-find] [--dry]
  Reads master/leases/events.log (last --minutes, times HH:MM:SS UTC) and master/leases/<id>.json titles. A unit counts
  for its family (template_find.title_key) when it was RELEASED, AUTO-RELEASED or AUTO-FAIL rc=3 in the window.
  A family with >= --min such units not alerted before: one line appended to master/leases/family-alerts.log, an alert
  printed with template_find's smallest upstream file (skip with --no-find). Idempotent: alerted keys in
  master/leases/family-alerts.state (both gitignored). --dry: print, write nothing. The Orchestrator decides what to do.
  Cron / Master loop: fleet-tools/capmem -m 2G taskset -c "$(fleet-tools/slots 1)" python3 -I fleet-tools/family_watch.py
"""
import json, os, re, sys, time
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import template_find as tf

L = os.path.join(tf.PENP, "master", "leases")
a = sys.argv[1:]
opt = lambda o, d: a[a.index(o) + 1] if o in a else d
MIN, MINUTES, DRY = int(opt("--min", 20)), int(opt("--minutes", 60)), "--dry" in a

def window(lines, minutes):   # walk back from the end; the log has no date, so stop at the first wrap past midnight too
    sec = lambda l: int(l[:2]) * 3600 + int(l[3:5]) * 60 + int(l[6:8])
    out, last = [], None
    for l in reversed(lines):
        if not re.match(r"\d\d:\d\d:\d\d ", l): continue
        s = sec(l)
        if last is None: last = s
        if (last - s) % 86400 > minutes * 60: break
        out.append(l)
    return out

def units(lines):   # family key -> set of ids that failed us
    fam, titles = defaultdict(set), {}
    for l in lines:
        f = l.split()
        if len(f) < 4: continue
        ev, uid = f[1], f[3]
        if ev in ("RELEASED", "AUTO-RELEASED") or (ev == "AUTO-FAIL" and "rc=3" in l):
            if uid not in titles:
                try: titles[uid] = json.load(open(os.path.join(L, uid + ".json")))["gap"]["title"]
                except Exception: titles[uid] = None
            if titles[uid]: fam[tf.title_key(titles[uid])].add(uid)
    return fam

if __name__ == "__main__":
    if "-h" in a or "--help" in a: sys.exit(__doc__)
    if "--demo" in a:   # self-check on a synthetic log
        log = ["23:50:00 RELEASED n x1 other", "00:10:00 AUTO-FAIL n x2 rc=3", "00:20:00 AUTO-FAIL n x3 rc=2"]
        assert [l[:8] for l in window(log, 60)] == ["00:20:00", "00:10:00", "23:50:00"]
        assert len(window(log, 15)) == 2
        assert tf.title_key("A step toward: Fano plane: no circuit of at most 27 gates on 0-3 1-4") == "Fano plane: no circuit of at most N gates on N"
        sys.exit(print("demo ok"))
    state_p = os.path.join(L, "family-alerts.state")
    seen = set(open(state_p).read().split("\n")) if os.path.exists(state_p) else set()
    fam = units(window(open(os.path.join(L, "events.log")).read().splitlines(), MINUTES))
    for k, ids in sorted(fam.items(), key=lambda kv: -len(kv[1])):
        if len(ids) < MIN or k in seen: continue
        best = "-"
        if "--no-find" not in a:
            r = tf.find(json.load(open(os.path.join(L, sorted(ids)[-1] + ".json")))["gap"])
            n = sum(r["per_handle"].values())
            if r["best"]:
                b = r["best"][0]
                best = f"{n} merged by others; smallest {b['path']} ({b['bytes']} B, {b['handle']} #{b['pr']}, {','.join(b['markers'])})"
            else: best = "no merged file of this statement shape upstream"
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}\t{len(ids)} units/{MINUTES}min\t{k}\t{best}\te.g. {sorted(ids)[-1]}"
        print("FAMILY-ALERT", line)
        if not DRY:
            open(os.path.join(L, "family-alerts.log"), "a").write(line + "\n")
            open(state_p, "a").write(k + "\n")
