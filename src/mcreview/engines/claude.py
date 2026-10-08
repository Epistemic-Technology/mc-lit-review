"""Claude engine: the coder of record for stance items (docs/plan.md stage 3).

Structured output (`output_config.format` JSON schema built from the codebook) so every construct gets
a value from its enum plus a verbatim evidence quote. Two modes:
- synchronous `code()` for small runs and the human-verification queue;
- Message Batches (`submit_batch` / `collect_batch`) for the full pass at half price.
The system prompt is the rendered codebook and is cached; the post is the user turn.
"""
from __future__ import annotations

import json
import logging
from typing import Iterable

import anthropic

from . import Answer, EngineResult
from ..codebook import Codebook, Construct

log = logging.getLogger(__name__)

PRICES = {  # $/MTok input, output; batch is half. Cached-read pricing ignored (conservative).
    "claude-opus-5-5": (4.0, 20.0),
    "claude-sonnet-5-5": (2.0, 10.0),
    "claude-haiku-4-5": (1.0, 5.0),
}


class ClaudeEngine:
    name = "claude"

    def __init__(self, codebook: Codebook, model: str, max_tokens: int = 8000, effort: str = "medium",
                 fallbacks: bool = True, timeout: float = 300.0, api_key: str | None = None) -> None:
        self.codebook = codebook
        self.model = model
        self.max_tokens = max_tokens
        self.effort = effort
        self.fallbacks = fallbacks
        self.client = anthropic.Anthropic(api_key=api_key, timeout=timeout) if api_key else anthropic.Anthropic(timeout=timeout)

    # -- request building --------------------------------------------------
    def params(self, state: dict | str, constructs: list[Construct]) -> dict:
        system = self.codebook.claude_system(constructs)
        user = state if isinstance(state, str) else json.dumps(state, ensure_ascii=False)
        p: dict = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            "messages": [{"role": "user", "content": "Code this post.\n\n" + user}],
            "output_config": {"effort": self.effort, "format": {"type": "json_schema", "schema": self.codebook.claude_schema(constructs)}},
        }
        return p

    # -- synchronous ------------------------------------------------------------
    def code(self, state: dict | str, constructs: list[Construct], repeat_no: int = 0, entity_id: int = 0) -> EngineResult:
        p = self.params(state, constructs)
        if self.fallbacks:
            msg = self.client.beta.messages.create(betas=["server-side-fallback-2026-07-01"], fallbacks="default", **p)
        else:
            msg = self.client.messages.create(**p)
        return self._parse(msg, constructs, batch=False)

    # -- batches --------------------------------------------------------------
    def submit_batch(self, items: Iterable[tuple[str, dict | str]], constructs: list[Construct]) -> str:
        from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
        from anthropic.types.messages.batch_create_params import Request

        reqs = [Request(custom_id=cid, params=MessageCreateParamsNonStreaming(**self.params(state, constructs))) for cid, state in items]
        b = self.client.messages.batches.create(requests=reqs)
        log.info("submitted batch %s with %d requests", b.id, len(reqs))
        return b.id

    def batch_status(self, batch_id: str) -> tuple[str, dict]:
        b = self.client.messages.batches.retrieve(batch_id)
        return b.processing_status, b.request_counts.model_dump()

    def collect_batch(self, batch_id: str, constructs: list[Construct]) -> Iterable[tuple[str, EngineResult | None, str | None]]:
        """Yields (custom_id, result, error). Results arrive in any order."""
        for r in self.client.messages.batches.results(batch_id):
            if r.result.type == "succeeded":
                yield r.custom_id, self._parse(r.result.message, constructs, batch=True), None
            else:
                err = getattr(getattr(r.result, "error", None), "type", None) or r.result.type
                yield r.custom_id, None, str(err)

    # -- parsing ---------------------------------------------------------------
    def _parse(self, msg, constructs: list[Construct], batch: bool) -> EngineResult:
        raw = msg.to_json().encode("utf-8") if hasattr(msg, "to_json") else json.dumps(msg.to_dict()).encode("utf-8")
        if msg.stop_reason == "refusal":
            raise RuntimeError(f"refusal: {getattr(msg.stop_details, 'category', None)}")
        if msg.stop_reason == "max_tokens":
            raise RuntimeError("max_tokens hit before the JSON was complete")
        text = next((b.text for b in msg.content if b.type == "text"), "")
        data = json.loads(text)
        out: dict[str, Answer] = {}
        for c in constructs:
            a = data.get(c.name)
            if not isinstance(a, dict) or "value" not in a:
                continue
            v = str(a["value"])
            ev = (a.get("evidence") or "").strip() or None
            out[c.name] = Answer(c.name, v, None, None, None, ev)
        u = msg.usage
        itok = int(u.input_tokens or 0) + int(getattr(u, "cache_creation_input_tokens", 0) or 0) + int(getattr(u, "cache_read_input_tokens", 0) or 0)
        otok = int(u.output_tokens or 0)
        pi, po = PRICES.get(self.model, (4.0, 20.0))
        mult = 0.5 if batch else 1.0
        cost = (itok / 1e6 * pi + otok / 1e6 * po) * mult
        return EngineResult(out, raw, itok, otok, cost, msg.model)
