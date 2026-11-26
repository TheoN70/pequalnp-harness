"""Local dashboard of the pequalnp fleet: research in flight, lanes, outcomes, machine load, tools and their use.

Usage: python3 harness/dashboard/serve.py [port]      (default 8377, listens on 127.0.0.1 only)
       python3 harness/dashboard/serve.py --demo      (self-check of the parsers)
Env:   DESK=0 stops the read-only call to pequalnp.com/desk/stats (one call per minute at most).

Reads only: results.tsv, master/leases/, master/verdicts.txt, work/*/, fleet-tools/, /proc, and the Claude
transcripts of this folder (to count which tools the sessions ran; commands themselves are never served).
"""
import glob, json, os, re, subprocess, sys, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.realpath(__file__))
HARNESS = os.path.dirname(HERE)
PENP = os.path.dirname(HARNESS)
TOOLS = os.path.join(HARNESS, "fleet-tools")
LEASES = os.path.join(HARNESS, "master", "leases")
TRANSCRIPTS = os.path.join(os.path.expanduser("~/.claude/projects"), PENP.replace("/", "-"))
SOLVER_BUDGET = 14  # "Load budget" of the pequalnp-hard skill
WRAPPERS = {"timeout", "time", "bash", "sh", "systemd-run", "taskset", "nice", "capmem"}


def read(path, tail=None):
    try:
        with open(path, errors="replace") as f:
            if tail:
                f.seek(0, 2)
                f.seek(max(0, f.tell() - tail))
            return f.read()
    except OSError:
        return ""


# ---------------------------------------------------------------- tools catalogue

FAMILIES = [  # first match wins
    (r"^(live|mincirc|allmin)", "Recherche exacte"),
    (r"^(ls|pm/lsdnf)", "Recherche locale"),
    (r"^lrat/", "Bornes inférieures (LRAT)"),
    (r"(_gen8?\.py|^circuit2lean|^six_cert)", "Générateurs Lean"),
    (r"^(pm/satpm|rect_cover)", "SAT"),
    (r"^(take_|release|n2_triage|category|capmem)", "Lanes et triage"),
    (r"", "Aides"),
]
EXTRA = [  # tools outside fleet-tools: (name, family, what, regex on a shell command)
    ("cadical", "SAT", "Solveur SAT CaDiCaL (celui de la toolchain Lean, ou python-sat)", r"\bcadical\b"),
    ("cirbo", "SAT", "Synthèse exacte de circuits par SAT (work/tools/cirbo-src)", r"\bcirbo\b"),
    ("lake build / lean", "Lean", "Compilation Lean (à lancer sous capmem)", r"\blake\s+(build|env)\b"),
    ("pnp.sh check", "Lean", "Vérificateur du projet sur l'étape en cours", r"pnp\.sh\s+check\b"),
    ("pnp.sh submit", "Lean", "Ouverture de la pull request d'une étape prouvée", r"pnp\.sh\s+submit\b"),
    ("grab.sh", "Collecteur", "Collecteur de baux de Master", r"\bgrab\.sh\b"),
    ("twin_merged.py", "Collecteur", "Négation réfutée par sa jumelle déjà mergée", r"\btwin_merged\.py\b"),
    ("desk/step", "Collecteur", "État d'une étape au guichet (lecture seule)", r"desk/step\b"),
]


def describe(path):
    """First meaningful line of the file's docstring or leading comment."""
    for line in read(path)[:1500].splitlines():
        s = line.strip().strip('"').strip("/*#").strip()
        if s.startswith(("!", "usr/bin", "bin/")) or len(s) < 12 or s.lower().startswith(("usage", "set -")):
            continue
        return s[:220]
    return ""


def catalogue():
    out = []
    for rel in sorted(glob.glob("*", root_dir=TOOLS) + glob.glob("pm/*", root_dir=TOOLS) + glob.glob("lrat/*", root_dir=TOOLS)):
        p = os.path.join(TOOLS, rel)
        base, ext = os.path.splitext(rel)
        if not os.path.isfile(p) or ext not in (".c", ".py", ".sh") and rel != "capmem":
            continue
        name = base if ext == ".c" else rel
        fam = next(f for rx, f in FAMILIES if re.search(rx, rel))
        # a C tool is called by its binary (after a slash); a script by its file name
        rx = r"/" + re.escape(os.path.basename(base)) + r"(?=[\s\"';|&)]|$)" if ext == ".c" else r"(?<![\w-])" + re.escape(os.path.basename(rel)) + r"\b"
        out.append({"name": name, "family": fam, "what": describe(p), "kind": ext.lstrip(".") or "sh",
                    "built": os.path.exists(os.path.join(TOOLS, base)) if ext == ".c" else None,
                    "mtime": os.path.getmtime(p), "rx": rx})
    for name, fam, what, rx in EXTRA:
        out.append({"name": name, "family": fam, "what": what, "kind": "ext", "built": None, "mtime": None, "rx": rx})
    return out


# ---------------------------------------------------------------- tool use, from the sessions' transcripts

class Usage:
    """Counts, per tool, the Bash commands of the Claude sessions that call it. Incremental: the files only grow."""

    def __init__(self):
        self.lock = threading.Lock()
        self.offsets, self.titles, self.done = {}, {}, False
        self.count = {}  # tool -> {"n": int, "last": iso, "days": {date: n}, "by": {session: n}}
        self.mcp = {}    # lean-lsp tool -> n
        self.cat = catalogue()
        self.rx = [(t["name"], re.compile(t["rx"])) for t in self.cat]

    def scan(self):
        for path in glob.glob(os.path.join(TRANSCRIPTS, "**", "*.jsonl"), recursive=True):
            rel = os.path.relpath(path, TRANSCRIPTS)
            sid = rel.split(os.sep)[0].removesuffix(".jsonl")
            sub = os.sep in rel
            try:
                with open(path, "rb") as f:
                    f.seek(self.offsets.get(path, 0))
                    for raw in f:
                        if not raw.endswith(b"\n"):
                            break  # half-written line: next pass
                        self.offsets[path] = self.offsets.get(path, 0) + len(raw)
                        if b'"custom-title"' in raw and not sub:
                            try:
                                self.titles[sid] = json.loads(raw).get("customTitle") or sid[:8]
                            except ValueError:
                                pass
                        elif b'"tool_use"' in raw:
                            self.line(raw, sid)
            except OSError:
                continue
        self.done = True

    def line(self, raw, sid):
        try:
            d = json.loads(raw)
            blocks = d["message"]["content"]
        except (ValueError, KeyError, TypeError):
            return
        ts = d.get("timestamp") or ""
        for b in blocks if isinstance(blocks, list) else []:
            if not isinstance(b, dict) or b.get("type") != "tool_use":
                continue
            name = b.get("name") or ""
            if "lean" in name.lower() and name.startswith("mcp__"):
                with self.lock:
                    k = name.split("__")[-1]
                    self.mcp[k] = self.mcp.get(k, 0) + 1
                self.hit("lean-lsp (MCP)", ts, sid)
            elif name == "Bash":
                cmd = str((b.get("input") or {}).get("command") or "")
                for tool, rx in self.rx:
                    if rx.search(cmd):
                        self.hit(tool, ts, sid)

    def hit(self, tool, ts, sid):
        with self.lock:
            c = self.count.setdefault(tool, {"n": 0, "last": "", "days": {}, "by": {}})
            c["n"] += 1
            c["last"] = max(c["last"], ts)
            c["days"][ts[:10]] = c["days"].get(ts[:10], 0) + 1
            c["by"][sid] = c["by"].get(sid, 0) + 1

    def snapshot(self, running):
        with self.lock:
            tools = [{k: v for k, v in t.items() if k != "rx"} for t in self.cat]
            tools.append({"name": "lean-lsp (MCP)", "family": "Lean", "kind": "ext", "built": None, "mtime": None,
                          "what": "Diagnostics et buts Lean sans compilation complète. " +
                                  ", ".join(f"{k} ×{v}" for k, v in sorted(self.mcp.items(), key=lambda kv: -kv[1])[:5])})
            for t in tools:
                c = self.count.get(t["name"], {})
                t["n"], t["last"], t["days"] = c.get("n", 0), c.get("last", ""), dict(c.get("days", {}))
                by = {}  # several sessions can carry the same title (a lane reopened)
                for s, n in c.get("by", {}).items():
                    by[self.titles.get(s, s[:8])] = by.get(self.titles.get(s, s[:8]), 0) + n
                t["by"] = sorted(by.items(), key=lambda x: -x[1])[:4]
                t["running"] = running.get(t["name"], 0)
            return tools


# ---------------------------------------------------------------- machine and processes

class Machine(threading.Thread):
    daemon = True

    def __init__(self, usage):
        super().__init__()
        self.usage = usage
        self.cores, self.prev, self.pprev, self.procs, self.hist = [], {}, {}, [], []
        self.hz = os.sysconf("SC_CLK_TCK")

    def run(self):
        while True:
            try:
                self.sample()
            except Exception as e:  # a vanished pid must not stop the sampler
                print("sample:", e, file=sys.stderr)
            time.sleep(2)

    def sample(self):
        cores = []
        for line in read("/proc/stat").splitlines():
            m = re.match(r"cpu(\d+) (.*)", line)
            if m:
                v = list(map(int, m[2].split()))
                idle, tot = v[3] + v[4], sum(v[:8])
                pi, pt = self.prev.get(m[1], (idle, tot))
                self.prev[m[1]] = (idle, tot)
                cores.append(round(100 * (1 - (idle - pi) / (tot - pt))) if tot > pt else 0)
        mem = dict(re.findall(r"(\w+):\s+(\d+)", read("/proc/meminfo")))
        now, procs, seen = time.time(), [], {}
        uptime = float(read("/proc/uptime").split()[0])
        for pid in filter(str.isdigit, os.listdir("/proc")):
            if int(pid) == os.getpid():
                continue
            try:
                cwd = os.readlink(f"/proc/{pid}/cwd")
                args = read(f"/proc/{pid}/cmdline").split("\0")
                stat = read(f"/proc/{pid}/stat").rsplit(")", 1)[1].split()
            except (OSError, IndexError):
                continue
            exe = os.path.basename(args[0]) if args and args[0] else ""
            cmd = " ".join(a for a in args if a)
            if not exe or exe in WRAPPERS or not (cwd.startswith(PENP) or PENP in cmd) or exe in ("claude", "node"):
                continue
            ticks = int(stat[11]) + int(stat[12])
            pt, pw = self.pprev.get(pid, (ticks, now - 2))
            seen[pid] = (ticks, now)
            status = read(f"/proc/{pid}/status")
            rss = re.search(r"VmRSS:\s+(\d+)", status)
            aff = re.search(r"Cpus_allowed_list:\s+(\S+)", status)
            rel = os.path.relpath(cwd, PENP) if cwd.startswith(PENP) else cwd
            procs.append({"pid": int(pid), "exe": exe, "cmd": cmd.replace(PENP + "/", "").replace(os.path.expanduser("~"), "~")[:260],
                          "cwd": rel, "cpu": round(100 * (ticks - pt) / self.hz / max(now - pw, 0.5)),
                          "rss_mb": int(rss[1]) // 1024 if rss else 0, "cores": aff[1] if aff else "",
                          "age_s": int(uptime - int(stat[19]) / self.hz), "core": int(stat[36])})
        self.pprev = seen
        self.cores, self.procs = cores, sorted(procs, key=lambda p: -p["cpu"])
        self.mem = {"total_gb": int(mem.get("MemTotal", 0)) / 1048576, "used_gb": (int(mem.get("MemTotal", 0)) - int(mem.get("MemAvailable", 0))) / 1048576}
        self.hist = (self.hist + [{"t": int(now), "cpu": round(sum(cores) / max(len(cores), 1)), "mem": round(self.mem["used_gb"], 1),
                                   "solvers": sum(p["cpu"] >= 50 for p in procs)}])[-150:]

    def running_tools(self):
        out = {}
        for p in self.procs:
            for tool, rx in self.usage.rx:
                if rx.search(p["cmd"]) or rx.search("/" + p["exe"]):
                    out[tool] = out.get(tool, 0) + 1
        return out


# ---------------------------------------------------------------- fleet state

def results():
    rows = []
    for line in read(os.path.join(PENP, "results.tsv")).splitlines()[1:]:
        c = (line.split("\t") + [""] * 10)[:10]
        outcome, reason = c[6].strip(), c[7].strip()
        if outcome == "released" and reason in ("missing_lemma", "statement_seems_false"):
            outcome = reason  # Master's own releases carry the verdict in the next column
        pr = re.search(r"#(\d+)", reason)
        rows.append({"date": c[0], "lane": c[1], "session": c[2], "step": c[3], "leased": c[4], "ended": c[5], "outcome": outcome or "-",
                     "reason": reason, "note": c[8], "category": c[9].strip() or "-", "pr": int(pr[1]) if pr else None})
    return rows


def lanes():
    out = []
    for p in sorted(glob.glob(os.path.join(LEASES, "busy-*"))):
        step = read(p).strip()
        out.append({"lane": os.path.basename(p)[5:], "step": step, "since": os.path.getmtime(p), "state": "busy" if step else "closed"})
    return out


def research():
    out = []
    for d in sorted(glob.glob(os.path.join(PENP, "work", "*", ""))):
        sid = os.path.basename(d.rstrip("/"))
        if sid == "tools":
            continue
        methods = []
        for st in sorted(glob.glob(os.path.join(d, "**", "STATUS.md"), recursive=True)):
            folder = os.path.dirname(st)
            files = [os.path.join(folder, f) for f in os.listdir(folder)]
            methods.append({"name": os.path.relpath(folder, d).replace(".", "(racine)"), "status": read(st)[:20000],
                            "updated": os.path.getmtime(st), "touched": max(map(os.path.getmtime, files)), "files": len(files)})
        flags = {f: read(os.path.join(d, f))[:600] for f in ("FOUND.txt", "REFUTED.txt") if os.path.exists(os.path.join(d, f))}
        lease = read(os.path.join(LEASES, sid + ".json"))
        try:
            gap = json.loads(lease).get("gap", {}) if lease else {}
        except ValueError:
            gap = {}
        out.append({"step": sid, "title": str(gap.get("title", ""))[:300], "statement": str(gap.get("statement", ""))[:600],
                    "methods": methods, "flags": flags})
    return out


SESS = {}  # transcript path -> (mtime, parsed)
XMSG = re.compile(r'<cross-session-message[^>]*from-name="([^"]*)"[^>]*>\s*(.*?)\s*</cross-session-message>', re.S)


def first_line(s, n=240):
    return next((l.strip() for l in str(s).splitlines() if l.strip()), "")[:n]


def parse_session(path):
    """Timeline of one Research session: start, last activity, messages with other sessions, last words."""
    out = {"start": "", "last": "", "msgs": [], "said": "", "calls": 0}
    try:
        f = open(path, errors="replace")
    except OSError:
        return out
    with f:
        for raw in f:
            if '"message"' not in raw:
                continue
            try:
                d = json.loads(raw)
                c = d["message"]["content"]
            except (ValueError, KeyError, TypeError):
                continue
            ts = d.get("timestamp") or ""
            if ts:
                out["start"] = out["start"] or ts
                out["last"] = max(out["last"], ts)
            for b in [{"type": "text", "text": c}] if isinstance(c, str) else c if isinstance(c, list) else []:
                if not isinstance(b, dict):
                    continue
                if b.get("type") == "tool_use":
                    out["calls"] += 1
                    if b.get("name") == "SendMessage":
                        i = b.get("input") or {}
                        out["msgs"].append({"t": ts, "dir": "out", "who": str(i.get("to", ""))[:60], "text": first_line(i.get("message", ""))})
                elif b.get("type") == "text":
                    t = str(b.get("text", ""))
                    if d.get("type") == "user":
                        for who, body in XMSG.findall(t):
                            out["msgs"].append({"t": ts, "dir": "in", "who": who[:60], "text": first_line(body)})
                    elif d.get("type") == "assistant" and t.strip():
                        out["said"] = t.strip()[:500]
    out["msgs"] = out["msgs"][-8:]
    return out


def parse_subagent(meta_path):
    log = meta_path.removesuffix(".meta.json") + ".jsonl"
    try:
        meta = json.loads(read(meta_path) or "{}")
    except ValueError:
        meta = {}
    start, calls = "", 0
    for raw in read(log).splitlines():
        if not start:
            m = re.search(r'"timestamp":"([^"]+)"', raw)
            start = m[1] if m else ""
        calls += raw.count('"type":"tool_use"')
    return {"what": str(meta.get("description", ""))[:120], "model": str(meta.get("model", "")),
            "finished": bool(meta.get("finished")), "start": start, "calls": calls,
            "touched": os.path.getmtime(log) if os.path.exists(log) else 0}


def research_sessions(titles):
    out = []
    for sid, title in dict(titles).items():
        if not str(title).startswith("Research"):
            continue
        path = os.path.join(TRANSCRIPTS, sid + ".jsonl")
        try:
            mt = os.path.getmtime(path)
        except OSError:
            continue
        if SESS.get(path, (None,))[0] != mt:
            SESS[path] = (mt, parse_session(path))
        s = dict(SESS[path][1])
        step = re.search(r"\bL-[a-z]+-\d+\b", title)
        s.update({"title": str(title)[:120], "step": step[0] if step else "", "touched": mt,
                  "agents": sorted((parse_subagent(m) for m in glob.glob(os.path.join(TRANSCRIPTS, sid, "subagents", "*.meta.json"))),
                                   key=lambda a: a["start"])})
        out.append(s)
    return sorted(out, key=lambda s: -s["touched"])


DESK = {"t": 0, "data": None}


def desk():
    if os.environ.get("DESK") == "0":
        return None
    if time.time() - DESK["t"] > 60:  # at most one read-only call per minute
        DESK["t"] = time.time()
        try:
            # same call as grab.sh makes (curl); read-only, takes no lease
            d = json.loads(subprocess.run(["curl", "-s", "-m", "6", "https://pequalnp.com/desk/stats"], capture_output=True, check=True).stdout)
            no = d.get("not_offerable")
            DESK["data"] = {k: v for k, v in d.items() if isinstance(v, (int, float))} | {
                "not_offerable": {str(k)[:40]: v for k, v in no.items() if isinstance(v, int)} if isinstance(no, dict) else {},
                "at": int(time.time())}
        except Exception as e:
            DESK["data"] = {"error": type(e).__name__, "at": int(time.time())}
    return DESK["data"]


def state(usage, machine):
    ev = read(os.path.join(LEASES, "events.log"), tail=40000).splitlines()[-250:]
    verdicts = {}
    for line in read(os.path.join(HARNESS, "master", "verdicts.txt")).splitlines():
        p = line.split()
        if len(p) > 1:
            verdicts[p[1]] = verdicts.get(p[1], 0) + 1
    collector = any(p["cmd"].find("grab.sh") >= 0 for p in machine.procs) or bool(
        [1 for pid in filter(str.isdigit, os.listdir("/proc")) if "master/grab.sh" in read(f"/proc/{pid}/cmdline").replace("\0", " ")])
    return {"now": int(time.time()), "collector": collector, "desk": desk(), "lanes": lanes(), "results": results(),
            "verdicts": verdicts, "events": ev, "pause": read(os.path.join(LEASES, "pause-watch.log"), tail=2000).splitlines()[-6:],
            "research": research(), "sessions": research_sessions(usage.titles), "cores": machine.cores, "mem": getattr(machine, "mem", {}), "hist": machine.hist,
            "load": read("/proc/loadavg").split()[:3], "procs": machine.procs, "budget": SOLVER_BUDGET,
            "tools": usage.snapshot(machine.running_tools()), "usage_ready": usage.done}


def serve(port):
    usage = Usage()
    machine = Machine(usage)
    machine.start()

    def rescan():
        while True:
            usage.scan()
            time.sleep(20)
    threading.Thread(target=rescan, daemon=True).start()

    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.split("?")[0] == "/api/state":
                body, ctype = json.dumps(state(usage, machine)).encode(), "application/json"
            elif self.path in ("/", "/index.html"):
                body, ctype = open(os.path.join(HERE, "index.html"), "rb").read(), "text/html; charset=utf-8"
            else:
                self.send_error(404); return
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

    print(f"dashboard: http://127.0.0.1:{port}/")
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()


def demo():
    u = Usage()
    cmd = lambda c: json.dumps({"timestamp": "2026-11-26T10:00:00Z", "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command": c}}]}}).encode()
    u.line(cmd("fleet-tools/capmem -m 4G fleet-tools/live 0xE8 1 && python3 -I fleet-tools/circuit2lean.py a b"), "s")
    u.line(cmd("echo alive; ls fleet-tools/live.c; cat delivery.txt"), "s")  # "live" as a word or a source file is not a run
    got = {k: v["n"] for k, v in u.count.items()}
    assert got == {"capmem": 1, "live": 1, "circuit2lean.py": 1}, got
    assert all(t["what"] for t in u.cat if t["kind"] == "py"), [t["name"] for t in u.cat if not t["what"]]
    msg = 'Another session: <cross-session-message from="x" from-session="y" from-name="Orchestrator" from-mode="p">\nOrchestrator → Research : go\nmore\n</cross-session-message>'
    assert XMSG.findall(msg) == [("Orchestrator", "Orchestrator → Research : go\nmore")], XMSG.findall(msg)
    print("demo ok")


if __name__ == "__main__":
    demo() if sys.argv[1:] == ["--demo"] else serve(int(sys.argv[1]) if sys.argv[1:] else 8377)
