# ruff: noqa: E501
"""Serve a loopback-only, lazy browser for table extraction cases."""

from __future__ import annotations

import argparse
import json
import mimetypes
import sys
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
for dependency_path in (REPOSITORY_ROOT / "src", REPOSITORY_ROOT / "third_party/grits-main"):
    if str(dependency_path) not in sys.path:
        sys.path.insert(0, str(dependency_path))

from cptla.evaluation.case_browser import LiveCaseBrowser  # noqa: E402
from scripts.build_table_case_report import load_config  # noqa: E402

BROWSER_HTML = r"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>表格恢复实时案例浏览器</title><style>
:root{--bg:#eef1f5;--card:#fff;--ink:#18212c;--line:#bdc7d2}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:system-ui,"Microsoft YaHei",sans-serif}header{position:sticky;top:0;z-index:5;background:#17233a;color:white;padding:10px 18px;display:flex;gap:10px;align-items:center;flex-wrap:wrap}button,input{padding:8px 12px;border:1px solid #8c99a8;border-radius:6px}button{cursor:pointer}button:disabled{opacity:.45;cursor:not-allowed}#status{margin-left:auto}.main{padding:16px}.meta{display:flex;gap:16px;flex-wrap:wrap;background:white;padding:12px;border-radius:9px}.tag{display:inline-block;background:#e6edff;padding:3px 8px;border-radius:999px;margin:2px}.views{display:grid;grid-template-columns:minmax(280px,1fr) minmax(360px,1fr) minmax(360px,1fr);gap:12px;margin-top:14px}.panel{background:var(--card);border:1px solid var(--line);border-radius:9px;padding:10px;min-width:0}.scroll{overflow:auto;max-height:72vh}.source{display:block;max-width:100%;max-height:72vh;margin:auto;cursor:zoom-in}.comparison-table{border-collapse:collapse;font-size:.78rem;min-width:max-content}.comparison-table td,.comparison-table th{border:1px solid #8996a3;padding:4px 7px;max-width:280px}.cell-match{background:#e5f6e8}.cell-text-diff{background:#fff3ad}.cell-structure-diff{background:#ffc9c9}.cell-one-sided,.cell-gap{background:#eadde1}.loading{opacity:.45;pointer-events:none}pre{white-space:pre-wrap;word-break:break-all;max-height:240px;overflow:auto;background:#f5f7f9;padding:10px}dialog{max-width:96vw;max-height:96vh;border:0;border-radius:10px}dialog img{max-width:92vw;max-height:88vh}@media(max-width:1100px){.views{grid-template-columns:1fr}}
</style></head><body>
<header><button id="previous">← 上一个</button><button id="next">下一个 →</button><form id="jump"><input id="target" placeholder="序号或 unit_id"><button>跳转</button></form><b id="position">— / —</b><span id="status">正在连接…</span></header>
<div class="main" id="main"><div class="meta"><b id="unit">—</b><span id="scores"></span><span id="profiles"></span><span id="tags"></span></div>
<div class="views"><section class="panel"><h2>原始裁剪图</h2><img id="source" class="source" alt="原始表格"></section><section class="panel"><h2>Ground Truth</h2><div id="truth" class="scroll"></div></section><section class="panel"><h2>Prediction</h2><div id="prediction" class="scroll"></div></section></div>
<details><summary>原始 HTML / 错误信息</summary><h3>Ground Truth</h3><pre id="truth-raw"></pre><h3>Prediction</h3><pre id="prediction-raw"></pre><h3>Error</h3><pre id="error"></pre></details></div>
<dialog id="zoom"><form method="dialog"><button>关闭</button></form><img alt="放大原图"></dialog>
<script>
let current=Math.max(0,Number(localStorage.getItem('table-case-index')||0));let total=0;const $=id=>document.getElementById(id);function profile(value){return value?`${value.row_count}×${value.column_count} / ${value.cell_count} cells / header rows ${value.header_row_count} / spans ${value.spanning_cells}`:'无预测结构'}async function load(index){if(index<0||(total&&index>=total))return;$('main').classList.add('loading');$('status').textContent='加载并计算当前案例…';try{const response=await fetch(`/api/case?index=${index}`);if(!response.ok)throw new Error(await response.text());const data=await response.json();current=data.index;total=data.total;localStorage.setItem('table-case-index',String(current));$('position').textContent=`${data.position} / ${data.total}`;$('unit').textContent=data.unit_id;$('scores').textContent=`GriTS-Top ${data.grits_top.toFixed(4)} · GriTS-Con ${data.grits_con.toFixed(4)} · Acc ${data.acc_con?'正确':'错误'}`;$('profiles').textContent=`GT ${profile(data.truth_profile)} | Pred ${profile(data.prediction_profile)}`;$('tags').innerHTML=[data.score_stratum,...data.error_tags].map(tag=>`<span class="tag">${tag}</span>`).join('');$('source').src=data.image_url;$('truth').innerHTML=data.truth_table_html;$('prediction').innerHTML=data.prediction_table_html;$('truth-raw').textContent=data.truth_html;$('prediction-raw').textContent=data.prediction_html;$('error').textContent=data.error||'';$('previous').disabled=current===0;$('next').disabled=current===total-1;$('status').textContent='已加载';}catch(error){$('status').textContent=`加载失败：${error.message}`;}finally{$('main').classList.remove('loading')}}$('previous').onclick=()=>load(current-1);$('next').onclick=()=>load(current+1);$('jump').onsubmit=async event=>{event.preventDefault();$('status').textContent='定位中…';try{const response=await fetch(`/api/resolve?value=${encodeURIComponent($('target').value)}`);if(!response.ok)throw new Error(await response.text());const data=await response.json();load(data.index)}catch(error){$('status').textContent=`跳转失败：${error.message}`}};document.addEventListener('keydown',event=>{if(event.target.tagName==='INPUT')return;if(event.key==='ArrowLeft')load(current-1);if(event.key==='ArrowRight')load(current+1)});const zoom=$('zoom');$('source').onclick=()=>{zoom.querySelector('img').src=$('source').src;zoom.showModal()};load(current);
</script></body></html>"""


class CaseBrowserServer(ThreadingHTTPServer):
    daemon_threads = True


def _handler(browser: LiveCaseBrowser):
    class Handler(BaseHTTPRequestHandler):
        def _headers(self, status: int, content_type: str, length: int) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(length))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; img-src 'self' data:")
            self.end_headers()

        def _send(self, payload: bytes, content_type: str, status: int = 200) -> None:
            self._headers(status, content_type, len(payload))
            self.wfile.write(payload)

        def _json(self, value: object, status: int = 200) -> None:
            self._send(json.dumps(value, ensure_ascii=False).encode(), "application/json; charset=utf-8", status)

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            try:
                if parsed.path == "/":
                    self._send(BROWSER_HTML.encode(), "text/html; charset=utf-8")
                    return
                if parsed.path == "/api/case":
                    index = int(query.get("index", ["0"])[0])
                    case = browser.get_case(index)
                    browser.record_view(case)
                    self._json(case)
                    return
                if parsed.path == "/api/resolve":
                    self._json({"index": browser.resolve_index(query.get("value", [""])[0])})
                    return
                if parsed.path == "/api/image":
                    index = int(query.get("index", ["0"])[0])
                    path = browser.image_path(index)
                    self._send(path.read_bytes(), mimetypes.guess_type(path.name)[0] or "image/jpeg")
                    return
                self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)
            except (IndexError, KeyError, ValueError) as error:
                self._json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
            except FileNotFoundError as error:
                self._json({"error": str(error)}, HTTPStatus.NOT_FOUND)
            except Exception as error:
                self._json({"error": f"{type(error).__name__}: {error}"}, HTTPStatus.INTERNAL_SERVER_ERROR)

        def log_message(self, format: str, *args: object) -> None:
            print(f"{self.address_string()} - {format % args}", flush=True)

    return Handler


def create_server(
    browser: LiveCaseBrowser, *, host: str = "127.0.0.1", port: int = 8765
) -> CaseBrowserServer:
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("live case browser must bind to a loopback address")
    return CaseBrowserServer((host, port), _handler(browser))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--cache-size", type=int, default=128)
    parser.add_argument(
        "--session-root", type=Path, default=Path("outputs/analysis/table-case-browser-sessions")
    )
    args = parser.parse_args()
    config = load_config(args.config)
    session_id = f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-tatr-live-case-browser"
    session_dir = args.session_root / session_id
    browser = LiveCaseBrowser(
        manifest_path=config.manifest,
        prediction_paths=config.predictions,
        truth_dir=config.truth_dir,
        images_dir=config.images_dir,
        session_dir=session_dir,
        cache_size=args.cache_size,
    )
    server = create_server(browser, host=args.host, port=args.port)
    print(json.dumps({"status": "ready", "url": f"http://{args.host}:{args.port}", "total": browser.total, "session_dir": str(session_dir)}, ensure_ascii=False), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
