"""Normalisation rules for cited works. Run: uv run --group dev pytest -q"""
from mcreview.refs import clean_title, coupling_queries, normalize

KNOWN = {"www.theintrinsicperspective.com"}
HOST_MAP = {"theintrinsicperspective.substack.com": "www.theintrinsicperspective.com"}


def n(url):
    return normalize(url, KNOWN, HOST_MAP)


def test_arxiv_versions_and_formats_collapse():
    urls = ["https://arxiv.org/abs/2308.08708v3", "https://arxiv.org/pdf/2308.08708", "http://www.arxiv.org/html/2308.08708v1"]
    assert {n(u).url_norm for u in urls} == {"https://arxiv.org/abs/2308.08708"}
    assert n(urls[0]).identifier == "arxiv:2308.08708"


def test_doi_lowercased_and_tracking_stripped():
    r = n("https://doi.org/10.1038/S41586-023-06647-8?utm_source=substack")
    assert r.kind == "doi" and r.identifier == "doi:10.1038/s41586-023-06647-8"


def test_wikipedia_title_without_fetch():
    r = n("https://en.wikipedia.org/wiki/Hard_problem_of_consciousness#Overview")
    assert r.kind == "wikipedia" and r.title == "Hard problem of consciousness"
    assert n("https://en.m.wikipedia.org/wiki/Special:Search").kind == "web"


def test_substack_post_aliases_become_one_reference():
    forms = [
        "https://open.substack.com/pub/theintrinsicperspective/p/slug?r=abc&utm_medium=ios",
        "https://theintrinsicperspective.substack.com/p/slug",
        "https://www.theintrinsicperspective.com/p/slug?s=r",
    ]
    assert {n(u).url_norm for u in forms} == {"https://www.theintrinsicperspective.com/p/slug"}


def test_unknown_custom_domain_post_is_a_candidate():
    assert n("https://example.com/p/some-essay").kind == "maybe_substack_post"
    assert n("https://medium.com/p/3f9a1c").kind == "web"          # Medium short links use /p/<hex>
    assert n("https://example.com/p/Not_A_Slug").kind == "web"


def test_homepage_and_tracking_params():
    assert n("https://www.theintrinsicperspective.com/").kind == "homepage"
    assert n("https://www.nytimes.com/a.html?smid=x&utm_x=1&page=2").url_norm == "https://nytimes.com/a.html?page=2"


def test_amazon_asin():
    r = n("https://www.amazon.com/Edge-Sentience/dp/0192870424/ref=sr_1_1")
    assert r.kind == "book" and r.identifier == "asin:0192870424"


def test_non_http_ignored():
    assert n("mailto:x@y.z") is None


def test_coupling_queries():
    q = coupling_queries("arxiv", "arxiv:2308.08708", "https://arxiv.org/abs/2308.08708", "Consciousness in Artificial Intelligence: Insights")
    assert q[0] == ("coupling_id", 'site:substack.com "2308.08708"')
    assert q[1][0] == "coupling_title"
    assert coupling_queries("web", None, "https://x.org/y", "Home") == []


def test_clean_title_strips_site_suffix_only_when_enough_remains():
    assert clean_title("The Edge of Sentience | Oxford Academic") == "The Edge of Sentience"
    assert clean_title("Home | Some Site") == "Home | Some Site"


def test_cdn_assets_are_not_references():
    assert n("https://substackcdn.com/image/fetch/w_1456/https%3A%2F%2Fexample.png") is None
