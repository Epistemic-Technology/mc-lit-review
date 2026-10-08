"""Polite, logged HTTP client.

- Per-host minimum interval (thread-safe), so concurrent body fetches never hammer one host.
- Retries with exponential backoff on 429/5xx/network errors; honours Retry-After.
- Every request is appended to `fetch_log` via the provided logger callback (the DB is written
  from the main thread only; see bodies.py).
- Built on `requests`/urllib3. httpx was tried first and is served a Cloudflare challenge (403,
  cf-mitigated: challenge) on substack.com and *.substack.com regardless of headers or HTTP version,
  while urllib, urllib3 and requests with identical headers pass. Sessions are per thread.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Callable
from urllib.parse import urlsplit

import requests


@dataclass
class Response:
    url: str
    final_url: str
    status: int
    content: bytes
    attempts: int
    elapsed_ms: int
    error: str | None = None

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300

    def json(self):
        import json

        return json.loads(self.content)

    def text(self) -> str:
        return self.content.decode("utf-8", errors="replace")


LogFn = Callable[[Response], None]


class Client:
    def __init__(
        self,
        user_agent: str,
        timeout: float = 30.0,
        default_interval: float = 1.0,
        host_intervals: dict[str, float] | None = None,
        global_interval: float = 0.0,
        max_retries: int = 5,
        log: LogFn | None = None,
    ) -> None:
        self._headers = {"User-Agent": user_agent, "Accept": "application/json, text/html;q=0.9, */*;q=0.8"}
        self._timeout = timeout
        self._local = threading.local()
        self.default_interval = default_interval
        self.global_interval = global_interval
        self._global_next = 0.0
        self.host_intervals = {k.lower(): float(v) for k, v in (host_intervals or {}).items()}
        self.max_retries = max_retries
        self.log = log
        self._next_ok: dict[str, float] = {}
        self._lock = threading.Lock()

    def _session(self) -> requests.Session:
        s = getattr(self._local, "session", None)
        if s is None:
            s = requests.Session()
            s.headers.update(self._headers)
            self._local.session = s
        return s

    def close(self) -> None:
        s = getattr(self._local, "session", None)
        if s is not None:
            s.close()

    # -- rate limiting -------------------------------------------------------
    def _interval_for(self, host: str) -> float:
        host = host.lower()
        for suffix, iv in self.host_intervals.items():
            if host == suffix or host.endswith("." + suffix):
                return iv
        return self.default_interval

    def _wait_turn(self, host: str) -> None:
        with self._lock:
            now = time.monotonic()
            start = max(now, self._next_ok.get(host, 0.0), self._global_next)
            self._next_ok[host] = start + self._interval_for(host)
            self._global_next = start + self.global_interval
        delay = start - time.monotonic()
        if delay > 0:
            time.sleep(delay)

    # -- requests -------------------------------------------------------------
    def get(self, url: str, headers: dict[str, str] | None = None, retries: int | None = None, timeout: float | None = None) -> Response:
        """`retries`/`timeout` override the client defaults for this call (used for arbitrary web hosts,
        where hanging or dead sites should cost one short attempt, not the Substack backoff schedule)."""
        max_retries = self.max_retries if retries is None else max(1, retries)
        tmo = self._timeout if timeout is None else timeout
        host = urlsplit(url).hostname or ""
        t0 = time.monotonic()
        attempts = 0
        err: str | None = None
        status = 0
        content = b""
        final_url = url
        backoff = 5.0
        while attempts < max_retries:
            attempts += 1
            self._wait_turn(host)
            try:
                r = self._session().get(url, headers=headers, timeout=tmo, allow_redirects=True)
                status, content, final_url = r.status_code, r.content, str(r.url)
                err = None
                if status == 429 or 500 <= status < 600:
                    ra = r.headers.get("Retry-After")
                    sleep_for = float(ra) if ra and ra.isdigit() else backoff
                    time.sleep(min(sleep_for, 120))
                    backoff = min(backoff * 3, 120)
                    continue
                break
            except requests.RequestException as e:
                err = f"{type(e).__name__}: {e}"
                time.sleep(backoff)
                backoff = min(backoff * 2, 60)
        resp = Response(url, final_url, status, content, attempts, int((time.monotonic() - t0) * 1000), err)
        if self.log:
            self.log(resp)
        return resp
