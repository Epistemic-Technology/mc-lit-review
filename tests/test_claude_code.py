"""Claude Code CLI transport: argv shape, env hygiene, result parsing, rate-limit retry. No real CLI."""
import json
from types import SimpleNamespace

import pytest

from mcreview.codebook import Codebook
from mcreview.engines import claude_code as cc


def _engine(**kw):
    return cc.ClaudeCodeEngine(Codebook(), "claude-opus-5-5", rate_limit_wait=0.0, rate_limit_retries=1, **kw)


def _result(structured, **over):
    d = {"is_error": False, "result": json.dumps(structured), "structured_output": structured, "session_id": "s1", "total_cost_usd": 0.05,
         "usage": {"input_tokens": 10, "output_tokens": 50, "cache_creation_input_tokens": 12000, "cache_read_input_tokens": 0},
         "modelUsage": {"claude-opus-5-5": {}}}
    d.update(over)
    return json.dumps(d)


def test_env_drops_api_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    assert "ANTHROPIC_API_KEY" not in _engine().env


def test_argv_has_schema_and_no_tools():
    cb = Codebook()
    argv = _engine().argv([cb.get("relevance")])
    assert argv[:2] == ["claude", "-p"] and "--tools" in argv and argv[argv.index("--tools") + 1] == ""
    schema = json.loads(argv[argv.index("--json-schema") + 1])
    assert schema["properties"]["relevance"]["properties"]["value"]["enum"][0] == "central"


def test_code_parses_structured_output_and_sends_post_on_stdin(monkeypatch):
    cb = Codebook()
    cons = [cb.get("relevance"), cb.get("arg_emergence")]
    seen = {}

    def fake_run(argv, input, capture_output, text, env, timeout):
        seen["input"] = input
        return SimpleNamespace(stdout=_result({"relevance": {"value": "central", "evidence": "q"}, "arg_emergence": {"value": "false", "evidence": ""}}), stderr="", returncode=0)

    monkeypatch.setattr(cc.subprocess, "run", fake_run)
    res = _engine().code({"title": "T", "subtitle": "", "body": "B"}, cons)
    assert '"title": "T"' in seen["input"]
    assert res.answers["relevance"].value == "central" and res.answers["relevance"].evidence == "q"
    assert res.answers["arg_emergence"].evidence is None
    assert res.input_tokens == 12010 and res.output_tokens == 50 and res.model == "claude-opus-5-5"
    assert res.extra["transport"] == "cli"


def test_rate_limit_retries_then_succeeds(monkeypatch):
    cb = Codebook()
    cons = [cb.get("relevance")]
    calls = iter([
        _result(None, is_error=True, result="You've hit your usage limit", api_error_status=429),
        _result({"relevance": {"value": "passing", "evidence": ""}}),
    ])
    monkeypatch.setattr(cc.subprocess, "run", lambda *a, **k: SimpleNamespace(stdout=next(calls), stderr="", returncode=0))
    assert _engine().code("x", cons).answers["relevance"].value == "passing"


def test_usage_limit_with_reset_timestamp_waits_until_reset(monkeypatch):
    import time as _t

    cb = Codebook()
    slept = []
    monkeypatch.setattr(cc.time, "sleep", lambda s: slept.append(s))
    reset = int(_t.time()) + 1800
    calls = iter([
        _result(None, is_error=True, result=f"Claude AI usage limit reached|{reset}"),
        _result({"relevance": {"value": "central", "evidence": ""}}),
    ])
    monkeypatch.setattr(cc.subprocess, "run", lambda *a, **k: SimpleNamespace(stdout=next(calls), stderr="", returncode=0))
    assert _engine().code("x", [cb.get("relevance")]).answers["relevance"].value == "central"
    assert 1700 < slept[0] < 1900


def test_other_errors_raise(monkeypatch):
    cb = Codebook()
    monkeypatch.setattr(cc.subprocess, "run", lambda *a, **k: SimpleNamespace(stdout=_result(None, is_error=True, result="Not logged in"), stderr="", returncode=1))
    with pytest.raises(RuntimeError, match="Not logged in"):
        _engine().code("x", [cb.get("relevance")])
