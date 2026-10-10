"""Normalisation rules for cited works. Run: uv run --group dev pytest -q"""
from mcreview.refs import anchor_title, clean_title, coupling_queries, normalize, slug_title, title_key, work_key

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


def test_publisher_urls_collapse_onto_the_doi():
    forms = ["https://dl.acm.org/doi/10.1145/3442188.3445922", "https://dl.acm.org/doi/pdf/10.1145/3442188.3445922", "https://doi.org/10.1145/3442188.3445922"]
    assert {n(u).identifier for u in forms} == {"doi:10.1145/3442188.3445922"}
    assert n("https://link.springer.com/article/10.1007/s43681-026-01297-8").identifier == "doi:10.1007/s43681-026-01297-8"
    assert n("https://www.biorxiv.org/content/10.1101/407007v1.full.pdf").identifier == "doi:10.1101/407007"
    assert n("https://academic.oup.com/pq/advance-article/doi/10.1093/pq/pqaf031/8100849").identifier == "doi:10.1093/pq/pqaf031"
    assert n("https://www.nature.com/articles/d41586-025-03222-1").identifier == "doi:10.1038/d41586-025-03222-1"
    assert n("https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0123456").identifier == "doi:10.1371/journal.pone.0123456"
    assert n("https://example.com/blog/10.5/x").kind == "web" and n("https://www.nature.com/nature/articles").kind == "web"


def test_arxiv_doi_is_the_arxiv_reference():
    assert n("https://doi.org/10.48550/arXiv.2308.08708").url_norm == "https://arxiv.org/abs/2308.08708"


def test_youtube_forms_and_more_tracking_params():
    assert n("https://youtu.be/87DyyMV0kCY?t=586").url_norm == n("https://www.youtube.com/watch?t=23s&v=87DyyMV0kCY&feature=shared").url_norm == "https://youtube.com/watch?v=87DyyMV0kCY"
    assert n("https://www.nytimes.com/2026/08/31/a.html?unlocked_article_code=1.9lA").url_norm == "https://nytimes.com/2026/08/31/a.html"
    assert n("https://www.sciencedirect.com/science/article/abs/pii/S1364661325002347").url_norm == "https://sciencedirect.com/science/article/pii/S1364661325002347"


def test_work_key_merges_publisher_pdf_and_doi():
    assert work_key("web", None, "https://dl.acm.org/doi/pdf/10.1145/3442188.3445922") == work_key("doi", "doi:10.1145/3442188.3445922", "https://doi.org/10.1145/3442188.3445922")
    assert work_key("substack_post", "x/p/y", "https://x/p/y", target_post_id=7) == "post:7"
    assert work_key("web", None, "https://example.org/a") == "https://example.org/a"


def test_title_key_ignores_short_or_generic_titles():
    assert title_key("Emotion Concepts and their Function in a Large Language Model | Anthropic") == "emotion concepts and their function in a large language model"
    assert title_key("the void") is None and title_key("Consciousness") is None


def test_anchor_title_prefers_agreed_or_title_cased_anchors():
    anchors = [("https://openai.com/index/x/", 3), ("OpenAI", 2), ("The Hugging Face incident and the road ahead", 2), ("“The Hugging Face incident and the road ahead”", 2),
               ("here", 9), ("recent reports of self-sacrificial cooperation among AI agents", 1), ("OpenAI’s incident report", 2)]
    assert anchor_title(anchors) == "The Hugging Face incident and the road ahead"
    assert anchor_title([("Stochastic Parrots: Frequently Unasked Questions", 1), ("defended her positions", 1)]) == "Stochastic Parrots: Frequently Unasked Questions"
    assert anchor_title([("Follow CIMC on X", 10)]) is None and anchor_title([("All info here", 6)]) is None and anchor_title([("Jacob Coxon’s", 3)]) is None
    assert anchor_title([("The New York Times", 4)]) is None and anchor_title([("Noam Chomsky argued, in the New York Times", 2)]) is None
    assert anchor_title([("COMPUTING MACHINERY AND INTELLIGENCE", 2)]) == "Computing Machinery And Intelligence"


def test_slug_title_is_a_readable_last_resort():
    assert slug_title("https://openai.com/index/hugging-face-incident-and-the-road-ahead") == "Hugging face incident and the road ahead"
    assert slug_title("https://lesswrong.com/posts/6ZnznCaTcbGYsCmqu/the-rise-of-parasitic-ai") == "The rise of parasitic ai"
    assert slug_title("https://youtube.com/watch?v=pyXouxa0WnY") is None and slug_title("https://anthropic.com/constitution") is None


def test_clean_title_strips_storefront_chrome():
    assert clean_title("Amazon.com: Addiction by Design: Machine Gambling in Las Vegas: 9780691160887: Schüll, Natasha Dow: Books") == "Addiction by Design: Machine Gambling in Las Vegas"
