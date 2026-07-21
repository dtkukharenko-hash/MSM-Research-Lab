#!/usr/bin/env python3
"""Read-only MSM orchestrator dashboard with a constrained start action."""
from __future__ import annotations

import ipaddress
import json
import re
import socket
import subprocess
from collections import deque
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

REPO = Path("/home/nnv/MSM-Research-Lab")
STATE = Path("/home/nnv/.local/state/msm-orchestrator")
TASK_FILE = REPO / ".codex" / "TASK.md"
LAUNCHER = "/usr/local/lib/msm-orchestrator/msm_dashboard_start.sh"
ALLOWED_CLIENTS = ipaddress.ip_network("10.43.44.0/24")
SERVICES = (
    "msm-orchestrator.service",
    "msm-task-feeder.service",
    "msm-reporter.service",
    "msm-dashboard.service",
)


def run(args: list[str], timeout: int = 20) -> tuple[int, str]:
    try:
        p = subprocess.run(
            args,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
        return p.returncode, p.stdout.strip()
    except Exception as exc:  # dashboard must remain available
        return 1, f"ERROR: {exc}"


def task_fields() -> dict[str, str]:
    try:
        text = TASK_FILE.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}
    fields: dict[str, str] = {}
    for name in ("task_id", "status", "task_kind", "infrastructure_maintenance"):
        match = re.search(rf"(?m)^-\s*{re.escape(name)}:\s*[`\"]?([^`\"\r\n]+)", text)
        if match:
            fields[name] = match.group(1).strip()
    return fields


def newest_envelope(task_id: str, directory: str) -> Path | None:
    root = STATE / directory
    if not root.is_dir():
        return None
    paths = list(root.glob(f"{task_id}-*.json"))
    return max(paths, key=lambda p: p.stat().st_mtime) if paths else None


def transitions(task_id: str, limit: int = 40) -> list[dict]:
    rows: deque[dict] = deque(maxlen=limit)
    path = STATE / "logs" / f"{task_id}.jsonl"
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                try:
                    value = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(value, dict):
                    rows.append(value)
    except OSError:
        pass
    return list(rows)


def service_states() -> dict[str, str]:
    result: dict[str, str] = {}
    for service in SERVICES:
        _, output = run(["systemctl", "is-active", service], timeout=3)
        result[service] = output or "unknown"
    return result


def process_rows(task_id: str) -> list[str]:
    _, output = run(["ps", "-eo", "pid,etime,%cpu,%mem,rss,args", "--sort=-%cpu"])
    if not output:
        return []
    needles = (
        task_id.lower(), "msm_orchestrator", "msm-orchestrator", "msm_worker",
        "codex", "planner", "implementer", "corrector", "auditor",
    )
    lines = output.splitlines()
    selected = [lines[0]]
    for line in lines[1:]:
        low = line.lower()
        if "msm_dashboard.py" not in low and any(x and x in low for x in needles):
            selected.append(line)
        if len(selected) >= 16:
            break
    return selected


def role_results(task_id: str) -> list[dict]:
    rows: list[dict] = []
    for path in sorted((STATE / "logs").glob(f"{task_id}-*.result.json")):
        try:
            value = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            continue
        if isinstance(value, dict):
            findings = value.get("findings", [])
            rows.append({
                "role": value.get("role", path.stem),
                "verdict": value.get("verdict", ""),
                "summary": value.get("summary", ""),
                "findings": findings if isinstance(findings, list) else [],
            })
    return rows


def current_state(task_id: str, rows: list[dict]) -> str:
    for directory, state in (
        ("running", "RUNNING"),
        ("queue", "QUEUED"),
        ("completed", "COMPLETED"),
        ("failed", "FAILED_TECHNICAL"),
        ("blocked", "BLOCKED_USER_DECISION"),
    ):
        if newest_envelope(task_id, directory):
            return state
    if rows:
        return str(rows[-1].get("to_state") or rows[-1].get("state") or "UNKNOWN")
    return "READY"


def report(task_id: str) -> dict:
    path = STATE / "reports" / f"{task_id}.md"
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        content = ""
    return {"path": str(path), "present": bool(content), "content": content[:300_000]}


def status_payload() -> dict:
    fields = task_fields()
    task_id = fields.get("task_id", "")
    rows = transitions(task_id) if task_id else []
    state = current_state(task_id, rows) if task_id else "NO_TASK"
    has_active = bool(newest_envelope(task_id, "running") or newest_envelope(task_id, "queue"))
    has_terminal = bool(
        newest_envelope(task_id, "completed")
        or newest_envelope(task_id, "failed")
        or newest_envelope(task_id, "blocked")
    )
    can_start = bool(task_id and fields.get("status") == "READY" and not has_active and not has_terminal)
    return {
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hostname": socket.gethostname(),
        "task": fields,
        "state": state,
        "can_start": can_start,
        "start_block_reason": (
            "" if can_start else
            "task status is not READY" if fields.get("status") != "READY" else
            "task already running or queued" if has_active else
            "this task already has a terminal envelope" if has_terminal else
            "task_id is missing"
        ),
        "services": service_states(),
        "transitions": rows,
        "processes": process_rows(task_id),
        "roles": role_results(task_id),
        "report": report(task_id) if task_id else {"path": "", "present": False, "content": ""},
    }


HTML = r"""<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MSM Research Lab</title><style>
:root{color-scheme:dark;--bg:#0b1020;--card:#151c30;--line:#2a3553;--text:#e8ecf6;--muted:#9ca9c4;--ok:#39d98a;--bad:#ff6b78;--warn:#ffca58;--accent:#72a7ff}*{box-sizing:border-box}body{margin:0;padding:24px;font-family:system-ui,-apple-system,"Segoe UI",sans-serif;background:var(--bg);color:var(--text)}main{max-width:1450px;margin:auto}header{display:flex;justify-content:space-between;gap:20px;align-items:flex-start;margin-bottom:18px}h1,h2,h3{margin-top:0}.muted{color:var(--muted)}.grid{display:grid;grid-template-columns:repeat(12,1fr);gap:14px}.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;overflow:auto}.s3{grid-column:span 3}.s6{grid-column:span 6}.s12{grid-column:span 12}.label{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.08em}.value{margin-top:6px;font-size:20px;font-weight:650;overflow-wrap:anywhere}.chip{display:inline-block;padding:6px 11px;border-radius:999px;font-weight:700;background:var(--accent);color:#07101f}.ok{background:var(--ok)}.bad{background:var(--bad)}.warn{background:var(--warn)}button{border:0;border-radius:10px;padding:12px 18px;font-weight:700;font-size:15px;background:var(--ok);color:#06160e;cursor:pointer}button:disabled{background:#4b556d;color:#aeb6c8;cursor:not-allowed}.message{margin-top:10px;white-space:pre-wrap}.service{display:flex;justify-content:space-between;padding:7px 0;border-bottom:1px solid var(--line)}pre{white-space:pre-wrap;word-break:break-word;margin:0;font:13px/1.45 ui-monospace,SFMono-Regular,Consolas,monospace}table{border-collapse:collapse;width:100%;font-size:13px}th,td{border-bottom:1px solid var(--line);text-align:left;padding:8px;vertical-align:top}th{color:var(--muted)}ol{padding-left:22px}@media(max-width:900px){body{padding:12px}.s3,.s6,.s12{grid-column:span 12}}
</style></head><body><main><header><div><h1>MSM Research Lab</h1><div class="muted">Оркестратор и запуск текущего задания</div></div><div class="muted" id="updated">Загрузка…</div></header><section class="grid">
<div class="card s6"><div class="label">Текущее задание</div><div class="value" id="task">—</div></div><div class="card s3"><div class="label">Состояние</div><div class="value"><span class="chip" id="state">—</span></div></div><div class="card s3"><div class="label">Действие</div><div class="value"><button id="start" disabled>Запустить</button></div><div class="muted message" id="startmsg"></div></div>
<div class="card s6"><h2>Службы</h2><div id="services"></div></div><div class="card s6"><h2>Активные процессы</h2><pre id="processes">—</pre></div><div class="card s12"><h2>Переходы</h2><div id="transitions"></div></div><div class="card s6"><h2>Результаты ролей</h2><div id="roles">Пока нет</div></div><div class="card s6"><h2>Итоговый отчёт</h2><div class="muted" id="reportpath"></div><pre id="report">Ещё не сформирован</pre></div>
</section></main><script>
const esc=v=>String(v??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
const stateClass=s=>/COMPLETED|READY/.test(s)?'ok':/FAILED|BLOCKED/.test(s)?'bad':/CORRECTING/.test(s)?'warn':'';
function renderTransitions(rows){if(!rows.length)return '<div class="muted">Переходов пока нет</div>';return '<table><thead><tr><th>UTC</th><th>Роль</th><th>Из</th><th>В</th></tr></thead><tbody>'+rows.map(r=>`<tr><td>${esc(r.timestamp||'')}</td><td>${esc(r.role||'')}</td><td>${esc(r.from_state||'')}</td><td><strong>${esc(r.to_state||r.state||'')}</strong></td></tr>`).join('')+'</tbody></table>'}
function renderRoles(rows){if(!rows.length)return '<div class="muted">Пока нет результатов</div>';return rows.map(r=>`<h3>${esc(r.role)} — ${esc(r.verdict)}</h3><div>${esc(r.summary)}</div>${r.findings?.length?'<ol>'+r.findings.map(x=>`<li>${esc(x)}</li>`).join('')+'</ol>':''}`).join('<hr>')}
async function refresh(){try{const d=await fetch('/api/status',{cache:'no-store'}).then(r=>r.json());document.getElementById('updated').textContent=`${d.hostname} · ${d.updated_at}`;document.getElementById('task').textContent=d.task.task_id||'—';const st=document.getElementById('state');st.textContent=d.state;st.className=`chip ${stateClass(d.state)}`;const b=document.getElementById('start');b.disabled=!d.can_start;b.title=d.start_block_reason||'';document.getElementById('startmsg').textContent=d.can_start?'Можно запускать текущее READY-задание':d.start_block_reason;document.getElementById('services').innerHTML=Object.entries(d.services).map(([n,s])=>`<div class="service"><span>${esc(n)}</span><strong>${esc(s)}</strong></div>`).join('');document.getElementById('processes').textContent=(d.processes||[]).join('\n')||'Нет активных процессов';document.getElementById('transitions').innerHTML=renderTransitions(d.transitions||[]);document.getElementById('roles').innerHTML=renderRoles(d.roles||[]);document.getElementById('reportpath').textContent=d.report.path||'';document.getElementById('report').textContent=d.report.present?d.report.content:'Ещё не сформирован'}catch(e){document.getElementById('startmsg').textContent='Ошибка связи: '+e}}
document.getElementById('start').addEventListener('click',async()=>{const b=document.getElementById('start');b.disabled=true;document.getElementById('startmsg').textContent='Запуск…';try{const r=await fetch('/api/start',{method:'POST',headers:{'X-MSM-Action':'start-current-task'}});const d=await r.json();document.getElementById('startmsg').textContent=(d.ok?'Запущено: ':'Ошибка: ')+(d.output||d.error||'');}catch(e){document.getElementById('startmsg').textContent='Ошибка запуска: '+e}setTimeout(refresh,1500)});refresh();setInterval(refresh,3000);
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def client_allowed(self) -> bool:
        try:
            return ipaddress.ip_address(self.client_address[0]) in ALLOWED_CLIENTS
        except ValueError:
            return False

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            body = HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
        elif path == "/api/status":
            self.send_json(200, status_payload())
        elif path == "/health":
            self.send_json(200, {"ok": True})
        else:
            self.send_json(404, {"ok": False, "error": "not found"})

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/start":
            self.send_json(404, {"ok": False, "error": "not found"})
            return
        if not self.client_allowed():
            self.send_json(403, {"ok": False, "error": "client network is not allowed"})
            return
        if self.headers.get("X-MSM-Action") != "start-current-task":
            self.send_json(403, {"ok": False, "error": "missing action header"})
            return
        code, output = run(["sudo", "-n", LAUNCHER], timeout=90)
        self.send_json(200 if code == 0 else 409, {"ok": code == 0, "output": output})

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"{self.client_address[0]} {self.log_date_time_string()} {fmt % args}", flush=True)


def main() -> None:
    server = ThreadingHTTPServer(("10.43.44.254", 8765), Handler)
    print("MSM dashboard listening on http://10.43.44.254:8765", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
