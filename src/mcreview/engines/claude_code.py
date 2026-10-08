"""Claude via the Claude Code CLI (subscription auth) instead of the API.

`claude -p` with `--json-schema` returns a `structured_output` object validated against the schema, so
the parsing is the same as the API engine's. Requirements verified 2026-09-29 with Claude Code 2.1.285:
- ANTHROPIC_API_KEY must be absent from the subprocess environment, otherwise the CLI uses the key
  (and its credit balance) instead of the claude.ai login;
- `--bare` breaks the login lookup ("Not logged in"), so it is not used;
- the post goes in on stdin (argv has size limits); the codebook goes in `--system-prompt`.
Every call carries ~12k tokens of Claude Code's own context, which counts against the subscription's
usage window. `total_cost_usd` in the result is the list-price equivalent, not a charge.
"""
from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import time

from . import Answer, EngineResult, FatalEngineError
from ..codebook import Codebook, Construct

log = logging.getLogger(__name__)


class ClaudeCodeEngine:
    name = "claude"

    def __init__(self, codebook: Codebook, model: str, effort: str = "medium", timeout: float = 600.0,
                 cli: str = "claude", rate_limit_wait: float = 300.0, rate_limit_retries: int = 12) -> None:
        self.codebook = codebook
        self.model = model
        self.effort = effort
        self.timeout = timeout
        self.cli = cli
        self.rate_limit_wait = rate_limit_wait
        self.rate_limit_retries = rate_limit_retries
        self.env = {k: v for k, v in os.environ.items() if k not in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")}

    def argv(self, constructs: list[Construct]) -> list[str]:
        return [self.cli, "-p", "--no-session-persistence", "--model", self.model, "--effort", self.effort, "--tools", "",
                "--output-format", "json", "--json-schema", json.dumps(self.codebook.claude_schema(constructs)),
                "--system-prompt", self.codebook.claude_system(constructs)]

    def code(self, state: dict | str, constructs: list[Construct], repeat_no: int = 0, entity_id: int = 0) -> EngineResult:
        user = state if isinstance(state, str) else json.dumps(state, ensure_ascii=False)
        prompt = "Code this post.\n\n" + user
        argv = self.argv(constructs)
        for attempt in range(self.rate_limit_retries + 1):
            proc = subprocess.run(argv, input=prompt, capture_output=True, text=True, env=self.env, timeout=self.timeout)
            raw = proc.stdout.encode("utf-8")
            try:
                d = json.loads(proc.stdout)
            except json.JSONDecodeError as e:
                raise RuntimeError(f"claude cli: non-JSON output (exit {proc.returncode}): {proc.stderr[:300] or proc.stdout[:300]}") from e
            if d.get("is_error"):
                msg = str(d.get("result") or "")
                low = msg.lower()
                if d.get("api_error_status") == 429 or any(s in low for s in ("rate limit", "usage limit", "limit reached", "hit your limit", "out of extra usage")):
                    wait = self.rate_limit_wait
                    # The CLI appends the reset time as "...|<unix seconds>" when it knows it.
                    m = re.search(r"\|(\d{9,11})\s*$", msg.strip())
                    if m:
                        wait = max(60.0, min(float(m.group(1)) - time.time() + 60.0, 6 * 3600))
                    log.warning("claude cli usage-limited (%s); waiting %.0f min (attempt %d/%d)", msg[:120], wait / 60, attempt + 1, self.rate_limit_retries)
                    time.sleep(wait)
                    continue
                if "not logged in" in msg.lower() or "credit balance" in msg.lower():
                    raise FatalEngineError(f"claude cli: {msg[:300]}")
                raise RuntimeError(f"claude cli error: {msg[:300]}")
            return self._parse(d, raw, constructs)
        raise RuntimeError("claude cli: still rate-limited after retries")

    def _parse(self, d: dict, raw: bytes, constructs: list[Construct]) -> EngineResult:
        data = d.get("structured_output")
        if not isinstance(data, dict):
            try:
                data = json.loads(d.get("result") or "")
            except json.JSONDecodeError as e:
                raise RuntimeError("claude cli: no structured_output in result") from e
        out: dict[str, Answer] = {}
        for c in constructs:
            a = data.get(c.name)
            if not isinstance(a, dict) or "value" not in a:
                continue
            ev = (a.get("evidence") or "").strip() or None
            out[c.name] = Answer(c.name, str(a["value"]), None, None, None, ev)
        u = d.get("usage") or {}
        itok = int(u.get("input_tokens") or 0) + int(u.get("cache_creation_input_tokens") or 0) + int(u.get("cache_read_input_tokens") or 0)
        otok = int(u.get("output_tokens") or 0)
        mu = d.get("modelUsage") or {}
        model = next(iter(mu), self.model)
        return EngineResult(out, raw, itok, otok, float(d.get("total_cost_usd") or 0.0), model, {"transport": "cli", "session_id": d.get("session_id")})
