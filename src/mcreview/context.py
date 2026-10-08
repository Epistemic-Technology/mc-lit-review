"""Shared per-run context: settings, DB, raw store, HTTP client, run row, credentials."""
from __future__ import annotations

import subprocess
import threading
from typing import Any

from . import db
from .config import PROJECT_ROOT, Settings
from .http import Client, Response
from .raw import RawStore


def git_sha() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return None


class Ctx:
    def __init__(self, stage: str, args: dict[str, Any] | None = None, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()
        self.conn = db.connect(self.settings.path("db"))
        self.raw = RawStore(self.settings.path("raw"))
        self.creds = self.settings.credentials()
        self.cutoff = self.settings.cutoff_date
        self.run_id = db.start_run(self.conn, stage, self.settings.config_hash(), git_sha(), args or {})
        self._log_buf: list[Response] = []
        self._log_lock = threading.Lock()
        h = self.settings["http"]
        self.client = Client(
            user_agent=h["user_agent"],
            timeout=h.get("timeout_seconds", 30),
            default_interval=h.get("default_host_interval", 1.0),
            host_intervals=h.get("host_intervals") or {},
            global_interval=h.get("global_interval", 0.0),
            max_retries=h.get("max_retries", 5),
            log=self._log_fetch,
        )
        self.counts: dict[str, int] = {}

    # -- bookkeeping ---------------------------------------------------------
    def bump(self, key: str, n: int = 1) -> None:
        self.counts[key] = self.counts.get(key, 0) + n

    def _log_fetch(self, r: Response) -> None:
        with self._log_lock:
            self._log_buf.append(r)

    def commit(self) -> None:
        with self._log_lock:
            buf, self._log_buf = self._log_buf, []
        if buf:
            self.conn.executemany(
                "INSERT INTO fetch_log(run_id, url, status, elapsed_ms, attempts, error, fetched_at) VALUES (?,?,?,?,?,?,?)",
                [(self.run_id, r.url, r.status, r.elapsed_ms, r.attempts, r.error, db.now()) for r in buf],
            )
        self.conn.commit()

    def finish(self, status: str = "ok") -> None:
        self.commit()
        db.finish_run(self.conn, self.run_id, self.counts, status)
        self.client.close()
        self.conn.close()

    def store_raw(self, r: Response, ext: str = "json") -> str:
        return self.raw.put(r.content, ext)

    @property
    def cookie(self) -> str | None:
        return self.creds.get("COOKIES_STRING")

    @property
    def brave_key(self) -> str | None:
        return self.creds.get("BRAVE_API_KEY")
