"""Engine response parsing, with no network."""
import json
from types import SimpleNamespace

from mcreview.codebook import Codebook
from mcreview.engines.claude import ClaudeEngine
from mcreview.engines.jev import JevEngine


def _jev():
    return JevEngine("test-key", Codebook(), "jev-1.13.0", "https://api.example", seed=1)


def test_jev_parse_choice_and_noul():
    cb = Codebook()
    cons = [cb.get("relevance"), cb.get("arg_hard_problem")]
    raw = json.dumps({
        "model": "jev-1.13.0",
        "answers": {
            "relevance": {"type": "choice", "choice": "central", "confidence": 0.8, "probabilities": {"central": 0.85, "substantial": 0.1, "passing": 0.03, "irrelevant": 0.02}},
            "arg_hard_problem": {"type": "noul", "noul": 0.2},
        },
        "usage": {"input_tokens": 1000, "output_tokens": 0},
    }).encode()
    res = _jev()._parse(raw, cons)
    assert res.answers["relevance"].value == "central" and res.answers["relevance"].probability == 0.85
    assert res.answers["arg_hard_problem"].value == "false" and res.answers["arg_hard_problem"].probability == 0.2
    assert abs(res.cost_usd - 1000 / 1e6 * 0.042) < 1e-12
    assert res.model == "jev-1.13.0"


def test_jev_repeat_zero_is_codebook_order_and_repeats_are_reproducible():
    e = _jev()
    cons = [Codebook().get("relevance")]
    q0 = e.questions(cons, 0, 42)
    assert list(q0["relevance"]["criteria"]) == ["central", "substantial", "passing", "irrelevant"]
    assert e.questions(cons, 1, 42) == e.questions(cons, 1, 42)


def test_claude_parse_reads_structured_json():
    cb = Codebook()
    cons = [cb.get("experience_now"), cb.get("arg_emergence")]
    payload = {"experience_now": {"value": "no", "evidence": "They are not conscious."}, "arg_emergence": {"value": "true", "evidence": ""}}
    msg = SimpleNamespace(
        stop_reason="end_turn", stop_details=None, model="claude-opus-5-5",
        content=[SimpleNamespace(type="text", text=json.dumps(payload))],
        usage=SimpleNamespace(input_tokens=5000, output_tokens=200, cache_creation_input_tokens=0, cache_read_input_tokens=3000),
        to_json=lambda: json.dumps({"ok": True}),
    )
    eng = ClaudeEngine.__new__(ClaudeEngine)
    eng.model = "claude-opus-5-5"
    res = eng._parse(msg, cons, batch=True)
    assert res.answers["experience_now"].value == "no"
    assert res.answers["experience_now"].evidence == "They are not conscious."
    assert res.answers["arg_emergence"].evidence is None
    assert res.input_tokens == 8000
    assert abs(res.cost_usd - (8000 / 1e6 * 4.0 + 200 / 1e6 * 20.0) * 0.5) < 1e-9
