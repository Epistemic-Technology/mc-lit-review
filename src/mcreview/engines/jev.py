"""TypeSafe Jev (System One decision model) engine. Research notes and caveats: docs/jev.md.

Request shape (docs.typesafe.ai/api.md): POST {base_url}/v1/systemone with
  {"model": ..., "state": <str|obj>, "questions": {name: {"type": "choice"|"noul", "instructions": ..., "criteria": ...}}}
Response: {"model": ..., "answers": {name: {"type": "choice", "choice": ..., "probabilities": {...}, "confidence": ...}
                                   | {"type": "noul", "noul": p}}, "usage": {"input_tokens": n, ...}}
Uses `requests` like the rest of the pipeline (plain API host, no Cloudflare challenge involved).
"""
from __future__ import annotations

import json
import logging
import random
import time

import requests

from . import Answer, EngineResult, FatalEngineError
from ..codebook import Codebook, Construct

log = logging.getLogger(__name__)


class JevEngine:
    name = "jev"

    def __init__(self, api_key: str, codebook: Codebook, model: str, base_url: str, timeout: float = 60.0,
                 price_per_mtok: float = 0.042, seed: int = 0, user_agent: str = "mc-lit-review") -> None:
        if not api_key:
            raise RuntimeError("TYPESAFE_API_KEY is not set (add it to the credentials env file)")
        self.codebook = codebook
        self.model = model
        self.url = base_url.rstrip("/") + "/v1/systemone"
        self.timeout = timeout
        self.price = price_per_mtok
        self.seed = seed
        self._session = requests.Session()
        self._session.headers.update({"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", "User-Agent": user_agent})

    def questions(self, constructs: list[Construct], repeat_no: int, entity_id: int) -> dict[str, dict]:
        """Repeat 0 uses codebook order; later repeats permute option order with a seed derived from
        (seed, entity, repeat) so a run is reproducible item by item."""
        rng = None if repeat_no == 0 else random.Random(f"{self.seed}:{entity_id}:{repeat_no}")
        return self.codebook.jev_questions(constructs, rng)

    def code(self, state: dict | str, constructs: list[Construct], repeat_no: int = 0, entity_id: int = 0) -> EngineResult:
        questions = self.questions(constructs, repeat_no, entity_id)
        backoff = 2.0
        shrinks = 0
        for attempt in range(9):
            st = self.codebook.jev_state(state) if isinstance(state, dict) else state
            payload = json.dumps({"model": self.model, "state": st, "questions": questions}, ensure_ascii=False).encode("utf-8")
            r = self._session.post(self.url, data=payload, timeout=self.timeout)
            if r.status_code in (429, 529) or r.status_code >= 500:
                ra = r.headers.get("Retry-After")
                time.sleep(min(float(ra) if ra and ra.replace(".", "", 1).isdigit() else backoff, 60))
                backoff = min(backoff * 2, 60)
                continue
            if r.status_code in (401, 402, 403):
                raise FatalEngineError(f"jev http {r.status_code}: {r.text[:300]}")
            if r.status_code == 400 and "max_tokens_exceeded" in r.text and isinstance(state, dict) and state.get("body") and shrinks < 3:
                # The character cap is a tokeniser guess; when the state still overflows, cut the body and retry.
                body = state["body"].rstrip()
                body = body[: int(len(body) * 0.7)] + "\n\n[TRUNCATED]"
                state = {**state, "body": body}
                shrinks += 1
                continue
            if r.status_code != 200:
                raise RuntimeError(f"jev http {r.status_code}: {r.text[:300]}")
            res = self._parse(r.content, constructs)
            if shrinks:
                res.extra["body_shrinks"] = shrinks
            return res
        raise RuntimeError("jev: gave up after repeated 429/5xx")

    def _parse(self, raw: bytes, constructs: list[Construct]) -> EngineResult:
        d = json.loads(raw)
        answers_in = d.get("answers") or {}
        out: dict[str, Answer] = {}
        for c in constructs:
            a = answers_in.get(c.name)
            if a is None:
                continue
            if c.primitive == "choice":
                probs = {k: float(v) for k, v in (a.get("probabilities") or {}).items()}
                choice = a.get("choice") or (max(probs, key=probs.get) if probs else None)
                out[c.name] = Answer(c.name, str(choice), probs.get(str(choice)), _f(a.get("confidence")), probs)
            else:
                p = _f(a.get("noul"))
                if p is None:
                    p = _f(a.get("probability"))
                out[c.name] = Answer(c.name, "true" if (p or 0.0) >= 0.5 else "false", p, None, {"true": p, "false": 1 - p} if p is not None else None)
        usage = d.get("usage") or {}
        itok = int(usage.get("input_tokens") or 0)
        return EngineResult(out, raw, itok, int(usage.get("output_tokens") or 0), itok / 1e6 * self.price, str(d.get("model") or self.model))


def _f(x) -> float | None:
    try:
        return None if x is None else float(x)
    except (TypeError, ValueError):
        return None
