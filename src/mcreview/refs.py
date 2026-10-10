"""Reference normalisation: turn outbound links into canonical cited-work identities.

Two links are the same reference when they normalise to the same `url_norm`. The rules are
deliberately conservative and fully deterministic so the references table can be rebuilt
from the raw bodies at any time.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit, unquote

from . import substack

TRACKING_PARAMS = re.compile(r"^(utm_\w+|ref|source|src|fbclid|gclid|mc_cid|mc_eid|igshid|igsh|si|s|t|r|triedRedirect|isFreemail|post_id|publication_id|showWelcomeOnShare|open|share|via|smid|cmpid|ncid|mbid|ito|cmp|at_\w+|sr_share|share_id|guccounter|__s|_hsenc|_hsmi|mkt_tok|wt\.mc_id|ref_src|ref_url|linkId|taid|unlocked_article_code|dlsi|nd|cid|programme_code|feature|ab_channel|x-amz-\w+|_ga|_gl|sh|ss_source|ss_campaign_\w+|srsltid)$", re.I)
# DOIs embedded in publisher URLs: dl.acm.org/doi/10.1145/x, science.org/doi/10.1126/x, link.springer.com/article/10.1007/x,
# frontiersin.org/articles/10.3389/x/full, biorxiv.org/content/10.1101/x v1, academic.oup.com/.../doi/10.1093/x/8100849.
PATH_DOI_RE = re.compile(r"/(10\.\d{4,9}/[^\s?#]+?)(?:v\d+)?(?:/(?:full|pdf|epdf|abstract|abs|meta|fulltext|html|\d{5,}))*/?$", re.I)
NATURE_ARTICLE_RE = re.compile(r"^/articles/([a-z]\d{5}-\d{3}-\d{4,6}-[0-9a-z]+|[a-z]+\d{3,6})$", re.I)
ARXIV_RE = re.compile(r"arxiv\.org/(?:abs|pdf|html)/((?:\d{4}\.\d{4,5})|(?:[a-z\-]+(?:\.[A-Z]{2})?/\d{7}))(?:v\d+)?", re.I)
DOI_RE = re.compile(r"^/(10\.\d{4,9}/[^\s#?]+)")
ASIN_RE = re.compile(r"/(?:dp|gp/product|gp/aw/d)/([A-Z0-9]{10})(?:[/?]|$)")
WIKI_RE = re.compile(r"^([a-z\-]+)\.(?:m\.)?wikipedia\.org$")
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
NOT_SUBSTACK_P_DOMAINS = {"medium.com", "instagram.com", "facebook.com", "pinterest.com", "tumblr.com", "x.com", "twitter.com", "threads.net"}
MULTI_LABEL_TLDS = {"co.uk", "org.uk", "ac.uk", "gov.uk", "com.au", "net.au", "org.au", "co.nz", "co.jp", "co.in", "com.br", "co.za", "com.mx"}


@dataclass
class Ref:
    url_norm: str
    kind: str          # substack_post | arxiv | doi | wikipedia | book | web | homepage
    identifier: str | None
    domain: str
    title: str | None = None
    title_source: str | None = None


def registered_domain(host: str) -> str:
    parts = host.split(".")
    if len(parts) >= 3 and ".".join(parts[-2:]) in MULTI_LABEL_TLDS:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


def normalize(url: str, known_substack_hosts: set[str] | None = None, host_map: dict[str, str] | None = None) -> Ref | None:
    """`known_substack_hosts`: custom-domain hosts confirmed as Substack publications.
    `host_map`: alias host -> canonical host (e.g. sub.substack.com -> www.custom.com), so the same post
    linked via open.substack.com, its subdomain, or its custom domain becomes one reference."""
    url = url.strip()
    if not url.lower().startswith(("http://", "https://")):
        return None
    try:
        u = urlsplit(url)
    except ValueError:
        return None
    host = (u.hostname or "").lower().rstrip(".")
    if not host or "." not in host:
        return None
    bare = host[4:] if host.startswith("www.") else host
    path = u.path or "/"
    if bare.endswith("substackcdn.com") or bare.endswith("substack-post-media.s3.amazonaws.com"):
        return None  # image/asset links, not citations

    # -- arXiv
    m = ARXIV_RE.search(host + path)
    if m:
        aid = m.group(1)
        return Ref(f"https://arxiv.org/abs/{aid}", "arxiv", f"arxiv:{aid}", "arxiv.org")
    # -- DOI (doi.org, or carried by a publisher URL: the article page, its PDF and its doi.org link are one work)
    doi = None
    if bare in ("doi.org", "dx.doi.org"):
        m = DOI_RE.match(unquote(path))
        doi = m.group(1).rstrip("/.\u2060").lower() if m else None
    else:
        doi = _publisher_doi(bare, unquote(path), u.query)
    if doi:
        m = re.match(r"^10\.48550/arxiv\.(.+)$", doi)   # DataCite DOIs minted for arXiv preprints
        if m:
            return Ref(f"https://arxiv.org/abs/{m.group(1)}", "arxiv", f"arxiv:{m.group(1)}", "arxiv.org")
        return Ref(f"https://doi.org/{doi}", "doi", f"doi:{doi}", "doi.org")
    # -- YouTube short links and timestamps
    if bare == "youtu.be" and len(path) > 1:
        return Ref(f"https://youtube.com/watch?v={path[1:].split('/')[0]}", "web", None, "youtube.com")
    # -- Wikipedia
    m = WIKI_RE.match(bare)
    if m and path.startswith("/wiki/"):
        title = unquote(path[len("/wiki/"):]).split("#")[0]
        if title and ":" not in title:  # skip Special:, File:, Talk: etc.
            lang = m.group(1)
            return Ref(f"https://{lang}.wikipedia.org/wiki/{title}", "wikipedia", f"wiki:{lang}:{title}", "wikipedia.org",
                       title=title.replace("_", " "), title_source="wikipedia")
    # -- Amazon books
    if "amazon." in bare:
        m = ASIN_RE.search(path)
        if m:
            return Ref(f"https://www.amazon.com/dp/{m.group(1)}", "book", f"asin:{m.group(1)}", registered_domain(bare))
    # -- Substack posts (own domain, custom domain, or open.substack.com/pub/<sub>/p/<slug>)
    kind, h, slug = substack.classify_url(url)
    if kind == "open_pub" and slug:
        h, kind = h + substack.SUBSTACK_SUFFIX, "post"
    if kind == "post" and h and (h.endswith(substack.SUBSTACK_SUFFIX) or (known_substack_hosts and h in known_substack_hosts)):
        h = (host_map or {}).get(h, h)
        return Ref(f"https://{h}/p/{slug}", "substack_post", f"{h}/p/{slug}", registered_domain(h))
    if kind == "post" and h and SLUG_RE.match(slug or "") and registered_domain(h) not in NOT_SUBSTACK_P_DOMAINS:
        # /p/<slug> on an unknown host: probably a custom-domain Substack publication. Confirmed (or demoted
        # to 'web') by the resolve stage, which fetches the homepage once per host.
        return Ref(f"https://{h}/p/{slug}", "maybe_substack_post", f"{h}/p/{slug}", registered_domain(h))
    # -- generic web page
    q = [(k, v) for k, v in parse_qsl(u.query, keep_blank_values=False) if not TRACKING_PARAMS.match(k)]
    q.sort()
    path_n = re.sub(r"/+", "/", path)
    if bare == "sciencedirect.com":
        path_n = path_n.replace("/science/article/abs/pii/", "/science/article/pii/")
    if len(path_n) > 1:
        path_n = path_n.rstrip("/")
    if path_n in ("", "/") and not q:
        return Ref(f"https://{bare}/", "homepage", None, registered_domain(bare))
    norm = urlunsplit(("https", bare, path_n, urlencode(q, doseq=True), ""))
    return Ref(norm, "web", None, registered_domain(bare))


def _publisher_doi(bare: str, path: str, query: str) -> str | None:
    """DOI carried by a publisher URL, lower-cased; None when the URL has no recognisable DOI."""
    if bare in ("doi.org", "dx.doi.org", "wikipedia.org") or bare.endswith(".wikipedia.org"):
        return None
    if bare == "nature.com":
        m = NATURE_ARTICLE_RE.match(path)
        return f"10.1038/{m.group(1).lower()}" if m else None
    if bare.endswith("plos.org"):
        for k, v in parse_qsl(query):
            if k == "id" and v.startswith("10."):
                return v.lower().rstrip("/.")
    m = PATH_DOI_RE.search(path)
    if not m:
        return None
    doi = re.sub(r"(v\d+)?(\.full|\.abstract)?(\.pdf|\.html?)?$", "", m.group(1).lower(), flags=re.I).rstrip("/.")
    return doi if len(doi.split("/", 1)[1]) >= 3 else None


WORK_KEY_KINDS = ("arxiv", "doi", "book", "wikipedia", "substack_post", "maybe_substack_post")


def work_key(kind: str, identifier: str | None, url_norm: str, target_post_id: int | None = None) -> str:
    """Identity of the cited work for merging references that are the same thing under different URLs:
    the corpus post when the reference resolves to one, else the stable identifier (DOI, arXiv id, ASIN,
    Wikipedia title, Substack post) after re-normalising, else the normalised URL itself."""
    if target_post_id:
        return f"post:{int(target_post_id)}"
    r = normalize(url_norm)
    if r is not None:
        if r.kind in WORK_KEY_KINDS and r.identifier:
            return r.identifier
        return re.sub(r"\.(pdf|html?)$", "", r.url_norm, flags=re.I)   # a paper's PDF and its HTML page are one work
    if kind in WORK_KEY_KINDS and identifier:
        return identifier
    return url_norm


def title_key(title: str | None) -> str | None:
    """Loose identity of a title for merging the same work hosted at several URLs (preprint and journal,
    lab blog and paper, mirrors of a PDF). Short or generic titles never merge."""
    t = clean_title(title)
    if not t:
        return None
    k = re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()
    if len(k) < 16 or len(k.split()) < 3:
        return None
    return k


GENERIC_ANCHORS = re.compile(
    r"^(here|this|link|source|paper|article|post|essay|report|study|book|video|podcast|episode|thread|tweet|page|pdf|website|site|"
    r"read more|see here|full (paper|article|report|text)|the (paper|article|post|essay|report|study|book|piece|link|original))\W*$", re.I)
# Anchors that name the venue or the author rather than the work.
VENUE_ANCHORS = {"the new york times", "new york times", "nyt", "the washington post", "washington post", "the guardian", "guardian", "reuters", "the wall street journal",
                 "wall street journal", "wsj", "bloomberg", "the atlantic", "wired", "nature", "science", "arxiv", "medium", "substack", "youtube", "twitter", "linkedin",
                 "library of congress", "stanford encyclopedia of philosophy", "wikipedia", "amazon", "google scholar", "ssrn", "philpapers", "boston review", "noema",
                 "noema magazine", "aeon", "vox", "npr", "bbc", "cnn", "forbes", "techcrunch", "the verge", "ars technica", "mit technology review", "technology review",
                 "scientific american", "the economist", "financial times", "axios", "politico", "the information", "semafor", "openai", "anthropic", "google deepmind",
                 "deepmind", "microsoft", "meta", "the new yorker", "new yorker", "the times", "time", "time magazine", "the conversation", "quanta", "quanta magazine",
                 "the economist", "lesswrong", "less wrong", "ea forum", "effective altruism forum", "hacker news", "reddit", "github", "spotify", "apple podcasts"}
_people_anchors: set[str] | None = None


def _person_names() -> set[str]:
    global _people_anchors
    if _people_anchors is None:
        try:
            from .config import load_yaml

            _people_anchors = {p["name"].lower() for p in load_yaml("names.yaml")["people"]}
        except Exception:  # noqa: BLE001 - config optional in tests
            _people_anchors = set()
    return _people_anchors


CALL_TO_ACTION = re.compile(r"^(follow|subscribe|join|buy|click|read|watch|listen|download|sign|visit|check out|get|order|pre-?order|support|donate|share|see)\b", re.I)


def anchor_title(anchors: list[tuple[str, int]]) -> str | None:
    """Pick a title from the anchor texts posts used for a link: (text, count) pairs, count being the number
    of posts using that text. An anchor used verbatim by two or more posts is taken as the work's name;
    an anchor used once is accepted only when it is title-cased. Sentence fragments, calls to action,
    bare URLs and generic words ("here", "paper") never qualify."""
    merged: dict[str, tuple[int, float, str]] = {}
    for raw, n in anchors:
        t = re.sub(r"\s+", " ", raw or "").strip().strip(" \"'“”‘’«»,.;:")
        if not t or len(t) < 12 or len(t) > 160 or GENERIC_ANCHORS.match(t) or CALL_TO_ACTION.match(t):
            continue
        if re.match(r"^(https?://|www\.)", t, re.I) or ("/" in t and " " not in t) or not t[0].isalnum() or t[0].islower():
            continue
        if re.search(r"\b(here|there|below|above)$|['’]s$|^(all|more|full) (info|details)", t, re.I):   # "all the details here", "Smith's"
            continue
        low = re.sub(r"\s+", " ", t.lower())
        if low in VENUE_ANCHORS or low in _person_names() or re.match(r"^(the )?[a-z]+ (times|post|review|magazine|journal|tribune|herald|gazette)$", low):
            continue
        if re.match(r"^(my |our |the |their |his |her )?(youtube|twitter|x|linkedin|facebook|instagram|substack|website|blog|podcast|newsletter|bluesky|mastodon|discord|github|patreon)( channel| page| account| profile| feed| server)?$", low):
            continue
        if re.search(r"\b(reported|argued|wrote|writes|published|said|says|noted|explained|described|interviewed|profiled) (in|on|at|for|by)\b", t, re.I):
            continue   # "Kashmir Hill reported in The New York Times"
        if t.isupper():
            t = t.title()
        words = t.split()
        if len(words) < 2:
            continue
        alpha = [w for w in words if w[0].isalpha()]
        ratio = sum(1 for w in alpha if w[0].isupper()) / len(alpha) if alpha else 0.0
        if ratio < 0.7 and re.search(r"\b(argued|argues|arguing|wrote|writes|writing|said|says|reported|reports|noted|notes|claimed|claims|explained|explains|published|described|describes|pointed out|points out)\b", t):
            continue   # a sentence fragment that mentions the work ("Noam Chomsky argued, in the New York Times")
        key = re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()
        cnt, best_ratio, best = merged.get(key, (0, 0.0, t))
        merged[key] = (cnt + int(n), max(best_ratio, ratio), best if cnt else t)
    if not merged:
        return None
    cnt, ratio, text = max(merged.values(), key=lambda x: (x[0], x[1], -len(x[2])))
    if cnt >= 2 or ratio >= 0.6:
        return text
    return None


def slug_title(url_norm: str) -> str | None:
    """Readable form of the URL's last path segment, used only as a display fallback (title_source 'slug')."""
    try:
        path = urlsplit(url_norm).path
    except ValueError:
        return None
    segs = [s for s in path.split("/") if s]
    if not segs:
        return None
    seg = unquote(segs[-1])
    seg = re.sub(r"\.(html?|pdf|php|aspx?|cfm)$", "", seg, flags=re.I)
    if len(segs) >= 2 and re.fullmatch(r"[A-Za-z0-9]{6,}", seg) and "-" not in seg:   # opaque ids (lesswrong, youtube)
        seg = unquote(segs[-2]) if "-" in segs[-2] else seg
    seg = re.sub(r"^\d{4}[-/]\d{2}[-/]\d{2}[-_]", "", seg)
    words = [w for w in re.split(r"[-_+]+", seg) if w]
    if len(words) < 3 or not any(re.search(r"[a-z]{3,}", w, re.I) for w in words):
        return None
    t = " ".join(words)
    return t[0].upper() + t[1:] if t[0].isalpha() else t


def clean_title(title: str | None) -> str | None:
    if not title:
        return None
    t = re.sub(r"\s+", " ", title).strip()
    # Storefront chrome: "Amazon.com: Title: Author: 9780691160887: Amazon.com: Books"
    t = re.sub(r"^Amazon\.[a-z.]+\s*:\s*", "", t, flags=re.I)
    if re.search(r"\b(Amazon\.[a-z.]+|Books|Kindle Store)\s*$", t, re.I):
        t = re.sub(r"\s*:\s*(\d{10}|\d{13}|[A-Z0-9]{10})\s*:.*$", "", t)                      # ISBN, author and store chrome
        t = re.sub(r"(\s*:\s*(Amazon\.[a-z.]+|Books|Kindle Store|eBook|Audible Books & Originals))+$", "", t, flags=re.I)
    # Drop common site suffixes: "Title | Site", "Title - Site", "Title — Site" (keep if that leaves too little)
    for sep in (" | ", " — ", " – ", " - ", " · "):
        if sep in t:
            head = t.split(sep)[0].strip()
            if len(head) >= 15:
                t = head
            break
    t = t.strip(" \"'“”‘’")
    return t or None


def coupling_queries(kind: str, identifier: str | None, url_norm: str, title: str | None) -> list[tuple[str, str]]:
    """(variant, query text) pairs used to find Substack posts citing this reference."""
    out: list[tuple[str, str]] = []
    qt = None
    if title:
        t = clean_title(title)
        if t and len(t) >= 15:
            qt = t.replace('"', "")[:150]
    if kind == "arxiv" and identifier:
        out.append(("coupling_id", f'site:substack.com "{identifier.split(":", 1)[1]}"'))
    elif kind == "doi" and identifier:
        out.append(("coupling_id", f'site:substack.com "{identifier.split(":", 1)[1]}"'))
    elif kind == "substack_post" and identifier:
        out.append(("coupling_url", f'site:substack.com "{identifier}"'))
    elif kind == "wikipedia":
        out.append(("coupling_url", f'site:substack.com "{url_norm.split("//", 1)[1]}"'))
    if qt and kind in ("arxiv", "doi", "substack_post", "web", "book"):
        out.append(("coupling_title", f'site:substack.com "{qt}"'))
    return out
