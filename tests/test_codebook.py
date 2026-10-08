"""The codebook must produce well-formed engine inputs and obey the design rules in docs/jev.md §3."""
import json
import random

from mcreview.codebook import NOUL_FALSE, NOUL_TRUE, Codebook


def test_every_choice_has_an_abstain_option():
    cb = Codebook()
    for c in cb.constructs + cb.publication_constructs:
        if c.primitive == "choice":
            assert c.abstain is not None, c.name


def test_stance_questions_carry_claims_and_uniform_levels():
    cb = Codebook()
    stance = cb.by_group("stance")
    assert len(stance) == 6
    allowed = {"yes", "yes_qualified", "no", "unsure", "discussed", "reports_only", "not_addressed"}
    for c in stance:
        assert c.claim and c.instructions and c.since == cb.version
        assert set(c.options) <= allowed and {"yes", "no", "discussed", "reports_only", "not_addressed"} <= set(c.options)
    retired = cb.by_group("stance", retired=True)
    assert len(retired) == 14 and all(list(c.options) == list(cb.stance_options) and c.retired_in == "0.2.0" for c in retired)


def test_versions_accept_unchanged_constructs_from_earlier_codebooks():
    cb = Codebook()
    assert cb.get("relevance").since == "0.1.0" and cb.accepts("relevance", "0.1.0") and cb.accepts("relevance", "0.2.0")
    assert cb.get("experience_now").since == "0.2.0" and not cb.accepts("experience_now", "0.1.0") and cb.accepts("experience_now", "0.2.0")
    assert cb.accepts("current_conscious", "0.1.0") and not cb.accepts("current_conscious", "0.2.0")   # retired
    assert not cb.accepts("no_such_construct", "0.2.0")
    assert cb.accepts("community", cb.pub_code_version, "publication") and not cb.accepts("community", "0.1.0/pub0.1.2", "publication")


def test_jev_permutation_changes_order_not_names():
    cb = Codebook()
    cons = [cb.get("relevance"), cb.get("experience_now"), cb.get("arg_chinese_room")]
    base = cb.jev_questions(cons)
    perm = cb.jev_questions(cons, random.Random(7))
    assert set(base["relevance"]["criteria"]) == set(perm["relevance"]["criteria"])
    assert any(list(base[n]["criteria"]) != list(perm[n]["criteria"]) for n in ("relevance", "experience_now"))
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
