"""Export helpers: tiering, quarters, name patterns."""
import re

from mcreview.config import load_yaml
from mcreview.export import _tier_lookup, merge_works, quarter


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


def _w(i, kind, url, title=None, source=None, posts=(), tier=None, **kw):
    return {"id": i, "kind": kind, "identifier": kw.get("identifier"), "url": url, "domain": url.split("/")[2], "title": title, "title_source": source,
            "target_post_id": kw.get("target_post_id"), "citing_posts": set(posts), "citing_pubs": {p * 10 for p in posts}, "tier": tier}


def test_merge_works_by_identifier_then_title():
    works = [
        _w(1, "web", "https://dl.acm.org/doi/10.1145/3442188.3445922", None, None, [1, 2]),
        _w(2, "doi", "https://doi.org/10.1145/3442188.3445922", "On the Dangers of Stochastic Parrots", "doi_csl", [2, 3], identifier="doi:10.1145/3442188.3445922"),
        _w(3, "arxiv", "https://arxiv.org/abs/2604.07729", "Emotion Concepts and their Function in a Large Language Model", "arxiv_page", [4], identifier="arxiv:2604.07729"),
        _w(4, "web", "https://transformer-circuits.pub/2026/emotions/index.html", "Emotion Concepts and their Function in a Large Language Model", "page", [5, 6]),
        _w(5, "homepage", "https://eleosai.org/", "Eleos AI Research", "page", [7]),
        _w(6, "web", "https://linkedin.com/company/eleos-ai-research", "Eleos AI Research", "page", [8], tier="social"),
        _w(7, "web", "https://example.org/a", "Short", "page", [9]),
    ]
    out = {w["url"]: w for w in merge_works(works)}
    parrots = out["https://doi.org/10.1145/3442188.3445922"]
    assert parrots["citing_posts"] == {1, 2, 3} and parrots["title"] == "On the Dangers of Stochastic Parrots" and parrots["aliases"] == ["https://dl.acm.org/doi/10.1145/3442188.3445922"]
    emotions = out["https://arxiv.org/abs/2604.07729"]           # the preprint is the canonical form; the lab page merges into it
    assert emotions["citing_posts"] == {4, 5, 6} and "https://transformer-circuits.pub/2026/emotions/index.html" in emotions["aliases"]
    assert "https://eleosai.org/" in out and "https://linkedin.com/company/eleos-ai-research" in out   # org names never merge
    assert "https://example.org/a" in out and len(out) == 5


def test_post_norm_leave_one_out_rank_and_threshold():
    from mcreview.export import MIN_NORM_POSTS, post_norm
    others = [{"reactions": 2, "comments": 0, "restacks": 1}] * (MIN_NORM_POSTS - 1) + [{"reactions": 20, "comments": 0, "restacks": 0}]
    n = post_norm({"reactions": 10, "comments": 3, "restacks": 1}, others)
    assert n["n"] == MIN_NORM_POSTS
    # baseline excludes the post itself: (9*2 + 20) / 10
    assert n["reactions"]["baseline"] == 3.8 and n["reactions"]["ratio"] == round(10 / 3.8, 2)
    assert n["reactions"]["rank"] == 2                       # one other post is higher
    assert n["comments"]["ratio"] is None                    # baseline 0: no ratio
    assert n["restacks"]["rank"] == 1                        # ties share the better rank
    # too few other posts: baseline and rank still reported, no ratio
    small = post_norm({"reactions": 10, "comments": 0, "restacks": 0}, others[:3])
    assert small["reactions"]["baseline"] == 2 and small["reactions"]["ratio"] is None and small["reactions"]["rank"] == 1
    empty = post_norm({"reactions": 10, "comments": 0, "restacks": 0}, [])
    assert empty["reactions"]["baseline"] is None and empty["reactions"]["ratio"] is None


def test_gold_allocation_fixed_and_proportional():
    from mcreview.gold import _allocate

    strata = {"a": list(range(100)), "b": list(range(30)), "c": list(range(5))}
    assert _allocate(strata, 20, {"a": 8, "b": 8, "c": 8}) == {"a": 8, "b": 8, "c": 5}   # capped by availability
    prop = _allocate(strata, 27)
    assert sum(prop.values()) == 27 and prop["a"] == 20 and prop["b"] == 6 and prop["c"] == 1
