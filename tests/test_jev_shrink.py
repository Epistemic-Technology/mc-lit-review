"""Jev: a state that overflows the token budget is retried with a shorter body."""
import json
from types import SimpleNamespace

from mcreview.codebook import Codebook
from mcreview.engines.jev import JevEngine


def test_max_tokens_exceeded_shrinks_body_and_retries():
    cb = Codebook()
    e = JevEngine("k", cb, "jev-1.13.0", "https://api.example")
    sent = []

    def post(url, data, timeout):
        body = json.loads(data)
        sent.append(len(body["state"]["body"]))
        if len(sent) < 3:
            return SimpleNamespace(status_code=400, text='{"detail":{"error_type":"max_tokens_exceeded"}}', headers={}, content=b"")
        ok = {"model": "jev-1.13.0", "answers": {"relevance": {"type": "choice", "choice": "passing", "probabilities": {"passing": 1.0}, "confidence": 1.0}}, "usage": {"input_tokens": 5}}
        return SimpleNamespace(status_code=200, text="", headers={}, content=json.dumps(ok).encode())

    e._session = SimpleNamespace(post=post)
    res = e.code({"title": "t", "subtitle": "", "body": "x" * 10000}, [cb.get("relevance")])
    assert res.answers["relevance"].value == "passing"
    assert sent[0] == 10000 and sent[1] < sent[0] and sent[2] < sent[1]
    assert res.extra["body_shrinks"] == 2
