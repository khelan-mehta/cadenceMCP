"""Dashboard HTTP server (stdlib only).

Serves a Plotly single-page app plus JSON/SVG APIs backed by the run store,
experiment registry, device catalog and schematic generator. Runs either as a
daemon thread (started from the MCP server) or standalone via __main__.
"""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from . import config, devices, experiments, schematic, store

STATIC = Path(__file__).parent / "static"

_server = None
_thread = None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # silence
        pass

    def _send(self, code, body, ctype="application/json"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body)
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        u = urlparse(self.path)
        path = u.path
        q = parse_qs(u.query)
        try:
            if path in ("/", "/index.html"):
                html = (STATIC / "index.html").read_text(encoding="utf-8")
                return self._send(200, html, "text/html; charset=utf-8")

            if path == "/api/experiments":
                return self._send(200, experiments.list_experiments())

            if path.startswith("/api/experiment/"):
                eid = path.rsplit("/", 1)[-1]
                exp = experiments.get(eid)
                if not exp:
                    return self._send(404, {"error": "not found"})
                return self._send(200, {"id": exp.id, "title": exp.title,
                                        "spec": exp.spec, "notes": exp.notes,
                                        "params": exp.params,
                                        "analyses": exp.analyses,
                                        "plots": exp.plots})

            if path == "/api/devices":
                return self._send(200, devices.list_devices())

            if path == "/api/cpu-demos":
                from .digital import sim
                from .digital.cpu import OPCODES
                return self._send(200, {"demos": {k: v.strip() for k, v in sim.DEMOS.items()},
                                        "isa": list(OPCODES.keys())})

            if path == "/api/cells":
                from .digital.cells import CELLS
                return self._send(200, [{"name": n, **c} for n, c in CELLS.items()])

            if path.startswith("/api/device/"):
                name = path.rsplit("/", 1)[-1]
                d = devices.get_device(name)
                return self._send(200 if d else 404, d or {"error": "not found"})

            if path == "/api/runs":
                eid = q.get("experiment", [None])[0]
                return self._send(200, store.list_runs(eid))

            if path.startswith("/api/run/"):
                rid = path.rsplit("/", 1)[-1]
                d = store.load_run(rid)
                return self._send(200 if d else 404, d or {"error": "not found"})

            if path.startswith("/api/schematic/"):
                eid = path.rsplit("/", 1)[-1]
                params = {k: v[0] for k, v in q.items()}
                svg = schematic.render(eid, params)
                return self._send(200, svg, "image/svg+xml")

            return self._send(404, {"error": "no route", "path": path})
        except Exception as e:
            return self._send(500, {"error": str(e)})

    def do_POST(self):
        u = urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw or b"{}")
        except Exception:
            payload = {}
        try:
            from . import core   # imported lazily (pulls in vm bridge)
            if u.path == "/api/run":
                r = core.run_experiment(str(payload.get("experiment")),
                                        payload.get("params") or {})
                return self._send(200, r)
            if u.path == "/api/parametric":
                r = core.run_parametric(str(payload.get("experiment")),
                                        payload.get("sweep_param"),
                                        payload.get("values") or [],
                                        payload.get("params") or {})
                return self._send(200, r)
            if u.path == "/api/vm":
                act = payload.get("action")
                if act == "start":
                    return self._send(200, {"status": vm_start()})
                return self._send(200, vm_status())
            if u.path == "/api/run-cpu":
                r = core.run_cpu(payload.get("program", "fibonacci"),
                                 int(payload.get("max_cycles", 3000)),
                                 int(payload.get("cache_lines", 8)),
                                 int(payload.get("line_bytes", 4)),
                                 int(payload.get("miss_penalty", 8)))
                return self._send(200, r)
            if u.path == "/api/characterize":
                from .digital import cells
                core.ensure_vm()
                cell = str(payload.get("cell", "INV")).upper()
                if cell == "RING":
                    return self._send(200, cells.ring_oscillator(int(payload.get("stages", 5))))
                fn = {"INV": cells.characterize_inverter, "FA": cells.characterize_full_adder,
                      "SRAM6T": cells.characterize_sram, "DFF": cells.characterize_dff}.get(cell)
                if not fn:
                    return self._send(404, {"error": f"no characterization for {cell}"})
                return self._send(200, fn())
            return self._send(404, {"error": "no route", "path": u.path})
        except Exception as e:
            return self._send(500, {"error": str(e)})


def vm_status():
    from . import vm
    return vm.status()


def vm_start():
    from . import vm
    return vm.start(wait=True)


def start(background: bool = True):
    global _server, _thread
    if _server is not None:
        return f"http://{config.DASHBOARD_HOST}:{config.DASHBOARD_PORT}/"
    _server = ThreadingHTTPServer((config.DASHBOARD_HOST, config.DASHBOARD_PORT), Handler)
    url = f"http://{config.DASHBOARD_HOST}:{config.DASHBOARD_PORT}/"
    if background:
        _thread = threading.Thread(target=_server.serve_forever, daemon=True)
        _thread.start()
    else:
        _server.serve_forever()
    return url


if __name__ == "__main__":
    print("Cadence dashboard on", start(background=False))
