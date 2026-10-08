"""Coding engines. Each exposes `code(state, constructs) -> EngineResult` with the same result shape so
`code.py` can store either. See docs/jev.md and docs/plan.md stage 3."""
from __future__ import annotations

from dataclasses import dataclass, field


class FatalEngineError(RuntimeError):
    """Credentials, billing or configuration: retrying other items cannot help, so the run stops."""


@dataclass
class Answer:
    construct: str
    value: str                       # chosen option, or 'true'/'false'
    probability: float | None = None # p(value); noul: p(true)
    confidence: float | None = None
    distribution: dict[str, float] | None = None
    evidence: str | None = None


@dataclass
class EngineResult:
    answers: dict[str, Answer]
    raw: bytes                       # exact response body, stored in the raw store
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    model: str = ""
    extra: dict = field(default_factory=dict)
