"""The codebook must produce well-formed engine inputs and obey the design rules in docs/jev.md §3."""
import json
import random

from mcreview.codebook import NOUL_FALSE, NOUL_TRUE, Codebook


def test_every_choice_has_an_abstain_option():
    cb = Codebook()
    for c in cb.constructs + cb.publication_constructs:
        if c.primitive == "choice":
            assert c.abstain is not None, c.name


def test_stance_items_share_options_and_carry_claims():
    cb = Codebook()
    stance = cb.by_group("stance")
    assert len(stance) >= 10
    for c in stance:
        assert c.claim and list(c.options) == list(cb.stance_options)
        assert "not_addressed" in c.options and "reports_only" in c.options


def test_jev_permutation_changes_order_not_names():
    cb = Codebook()
    cons = [cb.get("relevance"), cb.get("current_conscious"), cb.get("arg_chinese_room")]
    base = cb.jev_questions(cons)
    perm = cb.jev_questions(cons, random.Random(7))
    assert set(base["relevance"]["criteria"]) == set(perm["relevance"]["criteria"])
    assert any(list(base[n]["criteria"]) != list(perm[n]["criteria"]) for n in ("relevance", "current_conscious"))
    assert base["arg_chinese_room"]["type"] == "noul"
    assert "domain" not in json.dumps(base)                       # definition goes in the state, once
    assert cb.jev_state({"title": "t"})["definitions"]["machine minds"] == cb.domain
    json.dumps(perm)  # serialisable


def test_jev_criteria_drop_empty_fields():
    cb = Codebook()
    q = cb.jev_questions([cb.get("genre")])
    assert "not_for" not in q["genre"]["criteria"]["other"]


def test_claude_schema_enums_match_options():
    cb = Codebook()
    schema = cb.claude_schema(cb.constructs)
    assert schema["additionalProperties"] is False
    assert schema["properties"]["relevance"]["properties"]["value"]["enum"] == ["central", "substantial", "passing", "irrelevant"]
    assert schema["properties"]["arg_emergence"]["properties"]["value"]["enum"] == [NOUL_TRUE, NOUL_FALSE]
    assert set(schema["required"]) == {c.name for c in cb.constructs}


def test_system_prompt_and_markdown_mention_every_construct():
    cb = Codebook()
    sys_prompt = cb.claude_system(cb.constructs)
    md = cb.render_markdown()
    for c in cb.constructs:
        assert c.name in sys_prompt and c.name in md
    assert cb.version in md
