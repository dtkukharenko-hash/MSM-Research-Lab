#!/usr/bin/env python3
"""Read-only MSM orchestrator dashboard with constrained systemd actions."""
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
REPORTS = STATE / "reports"
ALLOWED_CLIENTS = ipaddress.ip_network("10.43.44.0/24")
TASK_ID_RE = re.compile(r"^[A-Z0-9][A-Z0-9-]{1,127}$")
LAUNCH_SERVICE = "msm-dashboard-launch.service"
SYNC_SERVICE = "msm-dashboard-sync.service"
SYNC_TIMER = "msm-dashboard-sync.timer"
SERVICES = (
    "msm-orchestrator.service",
    "msm-task-feeder.service",
    "msm-reporter.service",
    "msm-dashboard.service",
    SYNC_TIMER,
)


def run(args: list[str], timeout: int = 20) -> tuple[int, str]:
    try:
        process = subprocess.run(
            args,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
        return process.returncode, process.stdout.strip()
    except Exception as exc:
        return 1, f"ERROR: {exc}"


def task_fields() -> dict[str, str]:
    try:
        text = TASK_FILE.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}
    fields: dict[str, str] = {}
    for name in ("task_id", "status", "task_kind", "infrastructure_maintenance"):
        match = re.search(
            rf"(?m)^-\s*{re.escape(name)}:\s*[`\"]?([^`\"\r\n]+)",
            text,
        )
        if match:
            fields[name] = match.group(1).strip()
    return fields


def newest_envelope(task_id: str, directory: str) -> Path | None:
    root = STATE / directory
    if not root.is_dir():
        return None
    paths = list(root.glob(f"{task_id}-*.json"))
    return max(paths, key=lambda path: path.stat().st_mtime) if paths else None


def any_envelope(directory: str) -> bool:
    root = STATE / directory
    return root.is_dir() and next(root.glob("*.json"), None) is not None


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


def git_head() -> str:
    code, output = run(["git", "-C", str(REPO), "rev-parse", "--short=12", "HEAD"])
    return output if code == 0 else "unknown"


def process_rows(task_id: str) -> list[str]:
    _, output = run(["ps", "-eo", "pid,etime,%cpu,%mem,rss,args", "--sort=-%cpu"])
    if not output:
        return []
    needles = (
        task_id.lower(),
        "msm_orchestrator",
        "msm-orchestrator",
        "msm_worker",
        "codex",
        "planner",
        "implementer",
        "corrector",
        "auditor",
    )
    lines = output.splitlines()
    selected = [lines[0]]
    for line in lines[1:]:
        lowered = line.lower()
        if "msm_dashboard.py" not in lowered and any(
            needle and needle in lowered for needle in needles
        ):
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
            rows.append(
                {
                    "role": value.get("role", path.stem),
                    "verdict": value.get("verdict", ""),
                    "summary": value.get("summary", ""),
                    "findings": findings if isinstance(findings, list) else [],
                }
            )
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


def report_path(task_id: str) -> Path | None:
    if not TASK_ID_RE.fullmatch(task_id):
        return None
    root = REPORTS.resolve()
    path = (REPORTS / f"{task_id}.md").resolve()
    if path.parent != root or not path.is_file():
        return None
    return path


def report(task_id: str) -> dict:
    path = report_path(task_id)
    if path is None:
        return {
            "path": str(REPORTS / f"{task_id}.md"),
            "present": False,
            "content": "",
            "download_url": "",
        }
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        content = ""
    return {
        "path": str(path),
        "present": bool(content),
        "content": content[:300_000],
        "download_url": "/download/report" if content else "",
    }


def status_payload() -> dict:
    fields = task_fields()
    task_id = fields.get("task_id", "")
    rows = transitions(task_id) if task_id else []
    state = current_state(task_id, rows) if task_id else "NO_TASK"
    active_any = any_envelope("running") or any_envelope("queue")
    terminal_current = bool(
        newest_envelope(task_id, "completed")
        or newest_envelope(task_id, "failed")
        or newest_envelope(task_id, "blocked")
    )
    can_start = bool(
        task_id
        and fields.get("status") == "READY"
        and not active_any
        and not terminal_current
    )
    return {
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hostname": socket.gethostname(),
        "git_head": git_head(),
        "task": fields,
        "state": state,
        "can_start": can_start,
        "can_sync": not active_any,
        "start_block_reason": (
            ""
            if can_start
            else "task status is not READY"
            if fields.get("status") != "READY"
            else "another task is running or queued"
            if active_any
            else "this task already has a terminal envelope"
            if terminal_current
            else "task_id is missing"
        ),
        "sync_block_reason": "" if not active_any else "sync is disabled while a task is active",
        "services": service_states(),
        "transitions": rows,
        "processes": process_rows(task_id),
        "roles": role_results(task_id),
        "report": report(task_id)
        if task_id
        else {"path": "", "present": False, "content": "", "download_url": ""},
    }


HTML = r"""<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MSM Research Lab</title><style>
:root{color-scheme:dark;--bg:#0b1020;--card:#151c30;--line:#2a3553;--text:#e8ecf6;--muted:#9ca9c4;--ok:#39d98a;--bad:#ff6b78;--warn:#ffca58;--accent:#72a7ff}*{box-sizing:border-box}body{margin:0;padding:24px;font-family:system-ui,-apple-system,"Segoe UI",sans-serif;background:var(--bg);color:var(--text)}main{max-width:1450px;margin:auto}header{display:flex;justify-content:space-between;gap:20px;align-items:flex-start;margin-bottom:18px}h1,h2,h3{margin-top:0}.muted{color:var(--muted)}.grid{display:grid;grid-template-columns:repeat(12,1fr);gap:14px}.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;overflow:auto}.s3{grid-column:span 3}.s6{grid-column:span 6}.s12{grid-column:span 12}.label{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.08em}.value{margin-top:6px;font-size:20px;font-weight:650;overflow-wrap:anywhere}.chip{display:inline-block;padding:6px 11px;border-radius:999px;font-weight:700;background:var(--accent);color:#07101f}.ok{background:var(--ok)}.bad{background:var(--bad)}.warn{background:var(--warn)}button{border:0;border-radius:10px;padding:11px 15px;font-weight:700;font-size:14px;background:var(--ok);color:#06160e;cursor:pointer;margin:3px}button.secondary{background:var(--accent);color:#07101f}button:disabled{background:#4b556d;color:#aeb6c8;cursor:not-allowed}.message{margin-top:10px;white-space:pre-wrap}.service{display:flex;justify-content:space-between;padding:7px 0;border-bottom:1px solid var(--line)}.row{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}pre{white-space:pre-wrap;word-break:break-word;margin:0;font:13px/1.45 ui-monospace,SFMono-Regular,Consolas,monospace}table{border-collapse:collapse;width:100%;font-size:13px}th,td{border-bottom:1px solid var(--line);text-align:left;padding:8px;vertical-align:top}th{color:var(--muted)}ol{padding-left:22px}@media(max-width:900px){body{padding:12px}.s3,.s6,.s12{grid-column:span 12}}
</style></head><body><main><header><div><h1>MSM Research Lab</h1><div class="muted">Оркестратор, автосинхронизация и запуск заданий</div></div><div class="muted" id="updated">Загрузка…</div></header><section class="grid">
<div class="card s6"><div class="label">Текущее задание</div><div class="value" id="task">—</div><div class="muted" id="githead"></div></div><div class="card s3"><div class="label">Состояние</div><div class="value"><span class="chip" id="state">—</span></div></div><div class="card s3"><div class="label">Действия</div><div class="value"><button class="secondary" id="sync">Синхронизировать</button><button id="start" disabled>Запустить</button></div><div class="muted message" id="actionmsg"></div></div>
<div class="card s6"><h2>Службы</h2><div id="services"></div></div><div class="card s6"><h2>Активные процессы</h2><pre id="processes">—</pre></div><div class="card s12"><h2>Переходы</h2><div id="transitions"></div></div><div class="card s6"><h2>Результаты ролей</h2><div id="roles">Пока нет</div></div><div class="card s6"><div class="row"><h2>Итоговый отчёт</h2><button class="secondary" id="download" disabled>Скачать отчёт</button></div><div class="muted" id="reportpath"></div><pre id="report">Ещё не сформирован</pre></div>
</section></main><script>
const esc=v=>String(v??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
const stateClass=s=>/COMPLETED|READY/.test(s)?'ok':/FAILED|BLOCKED/.test(s)?'bad':/CORRECTING/.test(s)?'warn':'';
function renderTransitions(rows){if(!rows.length)return '<div class="muted">Переходов пока нет</div>';return '<table><thead><tr><th>UTC</th><th>Роль</th><th>Из</th><th>В</th></tr></thead><tbody>'+rows.map(r=>`<tr><td>${esc(r.timestamp||'')}</td><td>${esc(r.role||'')}</td><td>${esc(r.from_state||'')}</td><td><strong>${esc(r.to_state||r.state||'')}</strong></td></tr>`).join('')+'</tbody></table>'}
function renderRoles(rows){if(!rows.length)return '<div class="muted">Пока нет результатов</div>';return rows.map(r=>`<h3>${esc(r.role)} — ${esc(r.verdict)}</h3><div>${esc(r.summary)}</div>${r.findings?.length?'<ol>'+r.findings.map(x=>`<li>${esc(x)}</li>`).join('')+'</ol>':''}`).join('<hr>')}
async function refresh(){try{const d=await fetch('/api/status',{cache:'no-store'}).then(r=>r.json());document.getElementById('updated').textContent=`${d.hostname} · ${d.updated_at}`;document.getElementById('task').textContent=d.task.task_id||'—';document.getElementById('githead').textContent='Git: '+d.git_head;const st=document.getElementById('state');st.textContent=d.state;st.className=`chip ${stateClass(d.state)}`;const start=document.getElementById('start');start.disabled=!d.can_start;start.title=d.start_block_reason||'';const sync=document.getElementById('sync');sync.disabled=!d.can_sync;sync.title=d.sync_block_reason||'';const download=document.getElementById('download');download.disabled=!d.report.present;download.dataset.url=d.report.download_url||'';download.title=d.report.present?'Скачать Markdown-файл отчёта':'Отчёт ещё не сформирован';if(!document.getElementById('actionmsg').dataset.busy){document.getElementById('actionmsg').textContent=d.can_start?'Задание READY. Можно запускать.':d.start_block_reason}document.getElementById('services').innerHTML=Object.entries(d.services).map(([n,s])=>`<div class="service"><span>${esc(n)}</span><strong>${esc(s)}</strong></div>`).join('');document.getElementById('processes').textContent=(d.processes||[]).join('\n')||'Нет активных процессов';document.getElementById('transitions').innerHTML=renderTransitions(d.transitions||[]);document.getElementById('roles').innerHTML=renderRoles(d.roles||[]);document.getElementById('reportpath').textContent=d.report.path||'';document.getElementById('report').textContent=d.report.present?d.report.content:'Ещё не сформирован'}catch(e){document.getElementById('actionmsg').textContent='Ошибка связи: '+e}}
async function action(path,header,message){const box=document.getElementById('actionmsg');box.dataset.busy='1';box.textContent=message;try{const r=await fetch(path,{method:'POST',headers:{'X-MSM-Action':header}});const d=await r.json();box.textContent=(d.ok?'Готово: ':'Ошибка: ')+(d.output||d.error||'');}catch(e){box.textContent='Ошибка: '+e}delete box.dataset.busy;setTimeout(refresh,1000)}
document.getElementById('start').addEventListener('click',()=>action('/api/start','start-current-task','Запуск…'));
document.getElementById('sync').addEventListener('click',()=>action('/api/sync','sync-repository','Синхронизация…'));
document.getElementById('download').addEventListener('click',e=>{const url=e.currentTarget.dataset.url;if(url)window.location.assign(url)});
refresh();setInterval(refresh,3000);
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def client_allowed(self) -> bool:
        try:
            return ipaddress.ip_address(self.client_address[0]) in ALLOWED_CLIENTS
        except ValueError:
            return False

    def send_current_report(self) -> None:
        if not self.client_allowed():
            self.send_json(403, {"ok": False, "error": "client network is not allowed"})
            return
        task_id = task_fields().get("task_id", "")
        path = report_path(task_id)
        if path is None:
            self.send_json(404, {"ok": False, "error": "report is not available"})
            return
        try:
            body = path.read_bytes()
        except OSError as exc:
            self.send_json(500, {"ok": False, "error": f"cannot read report: {exc}"})
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/markdown; charset=utf-8")
        self.send_header("Content-Disposition", f'attachment; filename="{task_id}.md"')
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            body = HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)
        elif path == "/api/status":
            self.send_json(200, status_payload())
        elif path == "/download/report":
            self.send_current_report()
        elif path == "/health":
            self.send_json(200, {"ok": True})
        else:
            self.send_json(404, {"ok": False, "error": "not found"})

    def do_POST(self) -> None:
        if not self.client_allowed():
            self.send_json(403, {"ok": False, "error": "client network is not allowed"})
            return
        path = urlparse(self.path).path
        actions = {
            "/api/start": ("start-current-task", LAUNCH_SERVICE, "START_REQUEST_ACCEPTED"),
            "/api/sync": ("sync-repository", SYNC_SERVICE, "SYNC_COMPLETE"),
        }
        action = actions.get(path)
        if action is None:
            self.send_json(404, {"ok": False, "error": "not found"})
            return
        expected_header, service, success_message = action
        if self.headers.get("X-MSM-Action") != expected_header:
            self.send_json(403, {"ok": False, "error": "missing action header"})
            return
        code, output = run(
            ["sudo", "-n", "/usr/bin/systemctl", "start", service],
            timeout=120,
        )
        self.send_json(
            200 if code == 0 else 409,
            {"ok": code == 0, "output": output or success_message},
        )

    def log_message(self, fmt: str, *args: object) -> None:
        print(
            f"{self.client_address[0]} {self.log_date_time_string()} {fmt % args}",
            flush=True,
        )


def main() -> None:
    server = ThreadingHTTPServer(("10.43.44.254", 8765), Handler)
    print("MSM dashboard listening on http://10.43.44.254:8765", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
