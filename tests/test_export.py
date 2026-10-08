"""Export helpers: tiering, quarters, name patterns."""
import re

from mcreview.config import load_yaml
from mcreview.export import _tier_lookup, quarter


def test_quarter():
    assert quarter("2025-02-10T00:00:00Z") == "2025Q1" and quarter("2026-09-30") == "2026Q3" and quarter(None) is None


def test_tier_lookup_kind_domain_suffix_ignore():
    t = _tier_lookup(load_yaml("domain_tiers.yaml"))
    assert t("arxiv", None) == "academic" and t("book", "amazon.com") == "book" and t("wikipedia", "wikipedia.org") == "encyclopedia"
    assert t("web", "www.nytimes.com") == "press" and t("web", "anthropic.com") == "lab" and t("web", "lesswrong.com") == "forum"
    assert t("web", "philosophy.stanford.edu") == "academic"      # suffix rule
    assert t("web", "unsplash.com") is None and t("homepage", "unsplash.com") is None
    assert t("homepage", "substack.com") is None and t("homepage", "example.substack.com") == "substack"
    assert t("web", "open.substack.com") is None and t("substack_post", "example.substack.com") == "substack"
    assert t("web", "example.org") == "web"


def test_name_patterns_compile_and_avoid_turing_test():
    people = load_yaml("names.yaml")["people"]
    for p in people:
        for pat in p["patterns"]:
            re.compile(pat)
    turing = next(p for p in people if p["name"] == "Alan Turing")
    pats = [re.compile(x) for x in turing["patterns"]]
    assert not any(x.search("passes the Turing test") for x in pats)
    assert any(x.search("as Turing argued in 1950") for x in pats)
