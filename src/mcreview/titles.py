"""Title resolution for cited works (stage 7 prerequisite; `mcreview titles`).

The citation rounds fetch titles only for coupling candidates, so works on blocked domains (lab blogs,
social media, books), works cited once, and pages that refuse the project's user agent stay nameless.
This pass names everything the site shows. Strategies, in order:

  network (works cited by >= `min_posts` posts, plus every arXiv, DOI and ISBN reference)
    arxiv        abstract page citation_title
    doi          doi.org CSL JSON, then the Crossref API
    book         Open Library by ISBN-10 (Kindle ASINs have no ISBN)
    oEmbed       YouTube, X/Twitter, Spotify, Reddit, Vimeo, TikTok: the platform's own title/author
    page         citation_title > og:title > <title>; a 401/403 is retried once with a browser user agent;
                 PDFs give their metadata title when it is not a filename or an editor's default
  local (every remaining work, including those cited once)
    brave        the title Brave returned for the same URL during discovery or coupling searches
    anchor       the anchor text posts used for the link, when it reads as a title (refs.anchor_title)

Titles found here are stored in `refs.title` with their `title_source`; junk page titles (bot challenges,
storefront chrome, "Amazon.com") are treated as missing and replaced. Anchor-derived titles are never used
as coupling queries (citations.update_eligibility). The export adds a last display-only fallback, the URL
slug, which is never written to the database.
"""
from __future__ import annotations

import json
import logging
import re
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from io import BytesIO
from typing import Iterator
from urllib.parse import quote, urlsplit

from selectolax.parser import HTMLParser

from . import db, refs as refs_mod
from .config import load_yaml
from .context import Ctx
from .http import Client, Response

log = logging.getLogger(__name__)

BROWSER_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
HTML_ACCEPT = {"Accept": "text/html,application/xhtml+xml,*/*;q=0.8", "Accept-Language": "en-US,en;q=0.9"}
JUNK_TITLE = re.compile(
    r"^(amazon\.(com|co\.uk|ca|de)|client challenge|checking your browser|just a moment|attention required|access denied|"
    r"enterprise it news and events|request access|page not found|403 forbidden|404|are you a robot|please wait|"
    r"untitled|microsoft word - .*|[\w.-]+\.(com|org|net|ai|co\.uk)|home|homepage|\[?deleted( by user)?\]?|\[removed\])\W*$", re.I)
ISBN10 = re.compile(r"^\d{9}[\dX]$")
OEMBED = {
    "youtube.com": "https://www.youtube.com/oembed?format=json&url={url}",
    "youtu.be": "https://www.youtube.com/oembed?format=json&url={url}",
    "x.com": "https://publish.twitter.com/oembed?omit_script=1&url={url}",
    "twitter.com": "https://publish.twitter.com/oembed?omit_script=1&url={url}",
    "spotify.com": "https://open.spotify.com/oembed?url={url}",
    "reddit.com": "https://www.reddit.com/oembed?url={url}",
    "vimeo.com": "https://vimeo.com/api/oembed.json?url={url}",
    "tiktok.com": "https://www.tiktok.com/oembed?url={url}",
}
SKIP_DOMAINS = {"substack.com", "open.substack.com", "claude.ai", "chatgpt.com"}


def is_junk_title(title: str | None) -> bool:
    return not title or bool(JUNK_TITLE.match(title.strip()))


def html_title(html: str) -> str | None:
    tree = HTMLParser(html)
    for sel, attr in (('meta[name="citation_title"]', "content"), ('meta[property="og:title"]', "content"), ('meta[name="twitter:title"]', "content")):
        n = tree.css_first(sel)
        if n and n.attributes.get(attr):
            return n.attributes[attr]
    t = tree.css_first("title")
    return t.text() if t else None


def pdf_title(content: bytes) -> str | None:
    """Metadata title of a PDF, unless it is a filename, an editor default or a bare URL."""
    try:
        from pypdf import PdfReader

        meta = PdfReader(BytesIO(content)).metadata
        t = (meta.title if meta else None) or None
    except Exception:  # noqa: BLE001 - malformed PDFs are common
        return None
    if not t or len(t) < 8 or re.search(r"\.(pdf|docx?|tex|indd)$|^(untitled|microsoft word|document|paper|draft|final|manuscript)\b|^https?://", t, re.I):
        return None
    return t


def _oembed_title(domain: str, url: str, data: dict) -> str | None:
    if domain in ("x.com", "twitter.com"):
        who = data.get("author_name")
        p = HTMLParser(data.get("html") or "").css_first("p")
        text = re.sub(r"\s+", " ", p.text()).strip() if p else ""
        text = re.sub(r"\s*(pic\.twitter\.com/\S+|https?://t\.co/\S+)\s*$", "", text)
        if who and text:
            return f"{who} on X: {text[:110]}{'…' if len(text) > 110 else ''}"
        return f"{who} on X" if who else None
    t = data.get("title")
    if t and domain == "spotify.com":
        t = re.sub(r"^Spotify Embed:\s*", "", t)
    if not t and domain == "spotify.com":
        m = re.search(r'title="Spotify Embed: ([^"]+)"', data.get("html") or "")
        t = m.group(1) if m else None
    if t and data.get("author_name") and domain in ("youtube.com", "youtu.be", "vimeo.com", "tiktok.com"):
        return f"{t} ({data['author_name']})"
    return t


def _resolve_network(client: Client, row: dict) -> tuple[str | None, str | None, str | None]:
    """(title, title_source, error) for one reference, trying the strategy that fits its kind and host."""
    kind, url, ident, domain = row["kind"], row["url_norm"], row["identifier"] or "", row["domain"] or ""
    try:
        if kind == "arxiv":
            r = client.get(url, headers=HTML_ACCEPT)
            t = html_title(r.text()) if r.ok else None
            t = re.sub(r"^\[\d{4}\.\d{4,5}(v\d+)?\]\s*", "", t) if t else None
            return (t, "arxiv_page", None) if t else (None, None, f"http_{r.status}")
        if kind == "doi":
            doi = ident.split(":", 1)[1]
            r = client.get(url, headers={"Accept": "application/vnd.citationstyles.csl+json"})
            if r.ok:
                try:
                    t = r.json().get("title")
                    if t:
                        return t, "doi_csl", None
                except ValueError:
                    pass
            r2 = client.get(f"https://api.crossref.org/works/{quote(doi, safe='')}", headers={"Accept": "application/json"})
            if r2.ok:
                try:
                    ts = (r2.json().get("message") or {}).get("title") or []
                    if ts and ts[0]:
                        return ts[0], "crossref", None
                except ValueError:
                    pass
            return None, None, f"http_{r.status}/{r2.status}"
        if kind == "book":
            asin = ident.split(":", 1)[1]
            if not ISBN10.match(asin):
                return None, None, "no_isbn"
            r = client.get(f"https://openlibrary.org/isbn/{asin}.json", headers={"Accept": "application/json"})
            if r.ok:
                try:
                    d = r.json()
                    t = d.get("title")
                    if t and d.get("subtitle"):
                        t = f"{t}: {d['subtitle']}"
                    if t:
                        return t, "openlibrary", None
                except ValueError:
                    pass
            return None, None, f"http_{r.status}"
        if domain in OEMBED and (domain not in ("x.com", "twitter.com") or "/status/" in url):
            r = client.get(OEMBED[domain].format(url=quote(url, safe="")), headers={"Accept": "application/json"})
            if r.ok:
                try:
                    t = _oembed_title(domain, url, r.json())
                    if t:
                        return t, "oembed", None
                except ValueError:
                    pass
            if domain != "x.com" and domain != "twitter.com":
                return None, None, f"oembed_http_{r.status}"
        # generic page; a refusal of the project user agent is retried once as a browser
        r = client.get(url, headers=HTML_ACCEPT)
        if r.status in (401, 403, 406):
            r = client.get(url, headers={**HTML_ACCEPT, "User-Agent": BROWSER_UA})
        if not r.ok:
            return None, None, f"http_{r.status}"
        head = r.content[:5]
        if head.startswith(b"%PDF") or r.final_url.lower().endswith(".pdf"):
            t = pdf_title(r.content)
            return (t, "pdf", None) if t else (None, None, "pdf_no_title")
        t = html_title(r.text())
        if t and is_junk_title(refs_mod.clean_title(t)):
            return None, None, "junk_title"
        return (t, "page", None) if t else (None, None, "no_title")
    except Exception as e:  # noqa: BLE001 - one bad host must not stop the pass
        return None, None, f"{type(e).__name__}: {e}"[:200]


def candidates(ctx: Ctx, only_relevant: bool = True) -> list[dict]:
    """References the site may show that still lack a usable title."""
    tiers = load_yaml("domain_tiers.yaml")
    ignore = set(tiers.get("ignore") or []) | SKIP_DOMAINS
    rel = ""
    if only_relevant and ctx.conn.execute("SELECT 1 FROM code_final WHERE construct='relevance' LIMIT 1").fetchone():
        rel = ("AND r.id IN (SELECT pr.ref_id FROM post_refs pr WHERE pr.post_id IN "
               "(SELECT entity_id FROM code_final WHERE entity_type='post' AND construct='relevance' AND value IN ('central','substantial')))")
    rows = ctx.conn.execute(
        f"SELECT r.id, r.kind, r.identifier, r.url_norm, r.domain, r.title, r.title_source, r.title_fetched_at, r.citing_posts FROM refs r "
        f"WHERE r.kind NOT IN ('wikipedia','substack_post') AND (r.title IS NULL OR r.title_source IN ('anchor','brave')) {rel} "
        "ORDER BY r.citing_pubs DESC, r.citing_posts DESC, r.id"
    ).fetchall()
    out = []
    for r in rows:
        if r["domain"] in ignore or (r["domain"] or "").endswith(".substack.com") and r["kind"] == "homepage":
            continue
        out.append(dict(r))
    # stored page titles that are really bot challenges or storefront chrome
    junk = ctx.conn.execute(
        f"SELECT r.id, r.kind, r.identifier, r.url_norm, r.domain, r.title, r.title_source, r.title_fetched_at, r.citing_posts FROM refs r "
        f"WHERE r.title IS NOT NULL AND r.title_source NOT IN ('anchor','brave','post','wikipedia') AND r.kind NOT IN ('wikipedia','substack_post') {rel}"
    ).fetchall()
    out.extend(dict(r) for r in junk if r["domain"] not in ignore and (is_junk_title(refs_mod.clean_title(r["title"])) or (r["kind"] == "book" and r["title"].lower().startswith("amazon."))))
    return out


def brave_titles(ctx: Ctx) -> dict[str, str]:
    """url_norm -> title from every search result Brave ever returned."""
    known_hosts: set[str] = set()
    out: dict[str, str] = {}
    for url, title in ctx.conn.execute("SELECT url, title FROM search_results WHERE title IS NOT NULL AND title<>'' GROUP BY url"):
        ref = refs_mod.normalize(url, known_hosts)
        if ref is None:
            continue
        t = refs_mod.clean_title(title)
        if t and not is_junk_title(t) and ref.url_norm not in out:
            out[ref.url_norm] = t
    return out


def anchors_for(ctx: Ctx, ref_ids: list[int]) -> dict[int, list[tuple[str, int]]]:
    out: dict[int, list[tuple[str, int]]] = {}
    for i in range(0, len(ref_ids), 500):
        chunk = ref_ids[i:i + 500]
        q = ",".join("?" * len(chunk))
        for rid, text, n in ctx.conn.execute(
            f"SELECT ref_id, anchor_text, COUNT(DISTINCT post_id) FROM post_refs WHERE ref_id IN ({q}) AND anchor_text IS NOT NULL GROUP BY ref_id, anchor_text", chunk
        ):
            out.setdefault(int(rid), []).append((text, int(n)))
    return out


def fill_titles(ctx: Ctx, min_posts: int = 2, workers: int = 6, network: bool = True, only_relevant: bool = True, limit: int | None = None) -> None:
    cands = candidates(ctx, only_relevant)
    ctx.bump("titles_candidates", len(cands))
    log.info("%d references without a usable title", len(cands))
    cfg = ctx.settings["citation"]
    if network:
        # Works cited often enough to show, plus every arXiv/DOI/ISBN reference (one cheap API call each).
        # Earlier failures are retried: the round fetcher never tried a browser user agent, Crossref or oEmbed.
        todo = [c for c in cands if c["citing_posts"] >= min_posts or c["kind"] in ("arxiv", "doi", "book") or c["domain"] in OEMBED]
        if limit:
            todo = todo[:limit]
        h = ctx.settings["http"]
        client = Client(user_agent=h["user_agent"], timeout=float(cfg.get("title_fetch_timeout_seconds", 10)), default_interval=1.0,
                        host_intervals={"api.crossref.org": 0.2, "arxiv.org": 0.5, "openlibrary.org": 0.5}, global_interval=0.0, max_retries=1, log=ctx._log_fetch)
        log.info("network pass: %d references, %d workers", len(todo), workers)

        def work(row):
            return row, _resolve_network(client, row)

        def results() -> Iterator:
            window = workers * 4
            ex = ThreadPoolExecutor(max_workers=workers)
            pending: set = set()
            it = iter(todo)
            try:
                while True:
                    while len(pending) < window:
                        row = next(it, None)
                        if row is None:
                            break
                        pending.add(ex.submit(work, row))
                    if not pending:
                        break
                    done, pending = wait(pending, return_when=FIRST_COMPLETED)
                    for fut in done:
                        yield fut.result()
            finally:
                ex.shutdown(wait=False, cancel_futures=True)

        n = 0
        for row, (title, source, err) in results():
            title = refs_mod.clean_title(title)
            if title and is_junk_title(title):
                title, source, err = None, None, "junk_title"
            if title:
                ctx.conn.execute("UPDATE refs SET title=?, title_source=?, title_fetched_at=?, title_error=NULL WHERE id=?", (title, source, db.now(), row["id"]))
                row["title"], row["title_source"] = title, source
                ctx.bump(f"titles_{source}")
            else:
                ctx.conn.execute("UPDATE refs SET title_fetched_at=?, title_error=? WHERE id=? AND title IS NULL", (db.now(), err, row["id"]))
                ctx.bump("titles_network_missing")
            n += 1
            if n % 50 == 0:
                ctx.commit()
                log.info("titles: %d/%d fetched", n, len(todo))
        ctx.commit()
        client.close()
    # local evidence for whatever is still nameless
    remaining = [c for c in cands if not c["title"] or c["title_source"] in ("anchor", "brave") or is_junk_title(refs_mod.clean_title(c["title"]))]
    brave = brave_titles(ctx)
    anchors = anchors_for(ctx, [c["id"] for c in remaining])
    for c in remaining:
        title, source = None, None
        bt = brave.get(c["url_norm"])
        if bt:
            title, source = bt, "brave"
        else:
            at = refs_mod.anchor_title(anchors.get(c["id"], []))
            if at:
                title, source = refs_mod.clean_title(at), "anchor"
        if title and (c["title"] != title or c["title_source"] != source):
            ctx.conn.execute("UPDATE refs SET title=?, title_source=? WHERE id=?", (title, source, c["id"]))
            ctx.bump(f"titles_{source}")
        elif not title and c["title"] and (c["title_source"] in ("anchor", "brave") or is_junk_title(refs_mod.clean_title(c["title"]))):
            # a junk page title, or an anchor/search title the current rules no longer accept
            ctx.conn.execute("UPDATE refs SET title=NULL, title_source=NULL WHERE id=?", (c["id"],))
            ctx.bump("titles_cleared")
        elif not title:
            ctx.bump("titles_still_missing")
    ctx.commit()
