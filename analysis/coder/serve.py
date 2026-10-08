#!/usr/bin/env python3
"""Serve the coder tool with two small endpoints, no dependencies:

  GET  /api/samples                 -> list of sample files in data/ (without -decisions files)
  GET  /data/<name>.json            -> the exported sample
  POST /api/decisions/<name>        -> body is the decisions JSON; written to data/<name>-decisions.json
  GET  /api/decisions/<name>        -> the saved decisions, or {} if none

Usage: python3 analysis/coder/serve.py [port]   (default 8765), then expose with devserve if needed.
Import saved decisions with: uv run mcreview gold-import analysis/coder/data/<name>-decisions.json
"""
from __future__ import annotations

import json
import sys
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=str(ROOT), **k)

    def _json(self, obj, status=HTTPStatus.OK):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/samples":
            names = sorted(p.stem for p in DATA.glob("*.json") if not p.stem.endswith("-decisions"))
            return self._json([{"name": n, "decisions": (DATA / f"{n}-decisions.json").exists()} for n in names])
        if self.path.startswith("/api/decisions/"):
            p = DATA / f"{self._name()}-decisions.json"
            return self._json(json.loads(p.read_text()) if p.exists() else {})
        return super().do_GET()

    def do_POST(self):
        if not self.path.startswith("/api/decisions/"):
            return self.send_error(HTTPStatus.NOT_FOUND)
        n = int(self.headers.get("Content-Length") or 0)
        data = json.loads(self.rfile.read(n) or b"{}")
        DATA.mkdir(exist_ok=True)
        p = DATA / f"{self._name()}-decisions.json"
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1))
        tmp.replace(p)
        self._json({"saved": p.name, "items": len(data)})

    def _name(self) -> str:
        name = self.path.split("/api/decisions/", 1)[1].split("?")[0]
        if not name.replace("_", "").replace("-", "").isalnum():
            raise ValueError("bad sample name")
        return name

    def end_headers(self):
        if self.path.startswith("/data/") or self.path.startswith("/api/"):
            self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):  # quieter
        if "/api/" in (args[0] if args else ""):
            super().log_message(fmt, *args)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    print(f"coder tool on http://127.0.0.1:{port}  (data in {DATA})")
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
