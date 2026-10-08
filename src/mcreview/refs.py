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

TRACKING_PARAMS = re.compile(r"^(utm_\w+|ref|source|src|fbclid|gclid|mc_cid|mc_eid|igshid|si|s|r|triedRedirect|isFreemail|post_id|publication_id|showWelcomeOnShare|open|share|via|smid|cmpid|ncid|mbid|ito|cmp|at_\w+|sr_share|share_id|guccounter|__s|_hsenc|_hsmi|mkt_tok|wt\.mc_id|ref_src|ref_url|linkId|taid)$", re.I)
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
    # -- DOI
    if bare in ("doi.org", "dx.doi.org"):
        m = DOI_RE.match(unquote(path))
        if m:
            doi = m.group(1).rstrip("/.").lower()
            return Ref(f"https://doi.org/{doi}", "doi", f"doi:{doi}", "doi.org")
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
    if len(path_n) > 1:
        path_n = path_n.rstrip("/")
    if path_n in ("", "/") and not q:
        return Ref(f"https://{bare}/", "homepage", None, registered_domain(bare))
    norm = urlunsplit(("https", bare, path_n, urlencode(q, doseq=True), ""))
    return Ref(norm, "web", None, registered_domain(bare))


def clean_title(title: str | None) -> str | None:
    if not title:
        return None
    t = re.sub(r"\s+", " ", title).strip()
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
