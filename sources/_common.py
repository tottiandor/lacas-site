"""Shared helpers for every source adapter: HTTP, text cleanup, RSS parsing.

Standard library only - nothing to install, on your machine or in CI.
"""
from __future__ import annotations

import gzip
import html
import json
import re
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlparse, urlunparse, parse_qsl, urlencode

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 LacasSiteBot/0.1"
)

# Per-host timestamp of the last request, so we can honour crawl delays.
_last_request: dict[str, float] = {}


def fetch(url: str, *, timeout: int = 25, retries: int = 2, crawl_delay: float = 0.0) -> str:
    """GET a URL and return decoded text. Retries transient failures."""
    host = urlparse(url).netloc
    if crawl_delay:
        elapsed = time.time() - _last_request.get(host, 0.0)
        if elapsed < crawl_delay:
            time.sleep(crawl_delay - elapsed)

    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-GB,en;q=0.9",
                    "Accept-Encoding": "gzip",
                },
            )
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read()
                if response.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
                charset = response.headers.get_content_charset() or "utf-8"
            _last_request[host] = time.time()
            return raw.decode(charset, errors="replace")
        except Exception as error:  # noqa: BLE001 - any failure is worth retrying once
            last_error = error
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"failed to fetch {url}: {last_error}")


# --------------------------------------------------------------------------- text

def clean(text: str | None) -> str:
    """HTML fragment -> tidy single-line plain text."""
    if not text:
        return ""
    text = re.sub(r"<(script|style)[\s\S]*?</\1>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("<![CDATA[", " ").replace("]]>", " ")
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def truncate(text: str, limit: int = 240) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    cut = text.rfind(" ", 0, limit)
    return text[: cut if cut > 0 else limit].rstrip() + "\u2026"


def canonical_url(raw: str) -> str:
    """Drop tracking params/fragments so the same story de-duplicates cleanly."""
    try:
        parts = urlparse((raw or "").strip())
        query = [
            (k, v) for k, v in parse_qsl(parts.query)
            if not re.match(r"^(utm_|fbclid|gclid|mc_cid|mc_eid|ref$|source$)", k, re.I)
        ]
        path = parts.path.rstrip("/") or "/"
        host = parts.netloc.lower().removeprefix("www.")
        return urlunparse((parts.scheme or "https", host, path, "", urlencode(query), ""))
    except Exception:  # noqa: BLE001
        return (raw or "").strip()


def id_for(url: str) -> str:
    """Stable short id derived from the canonical URL (djb2)."""
    value = 5381
    for char in canonical_url(url):
        value = ((value * 33) ^ ord(char)) & 0xFFFFFFFF
    return f"{value:08x}"


def to_iso(value) -> str | None:
    """Anything date-ish -> ISO-8601 UTC string, or None if unparseable."""
    if not value:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value).strip()
        parsed = None
        try:
            parsed = parsedate_to_datetime(text)  # RFC 822, i.e. RSS pubDate
        except Exception:  # noqa: BLE001
            pass
        if parsed is None:
            try:
                parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            except ValueError:
                return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def first_image_in(html_fragment: str | None, base: str | None = None) -> str | None:
    if not html_fragment:
        return None
    match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', html_fragment, re.I)
    if not match:
        return None
    src = html.unescape(match.group(1))
    return urljoin(base, src) if base else src


# --------------------------------------------------------------------------- RSS

NS = {
    "content": "http://purl.org/rss/1.0/modules/content/",
    "dc": "http://purl.org/dc/elements/1.1/",
    "media": "http://search.yahoo.com/mrss/",
    "atom": "http://www.w3.org/2005/Atom",
}


def _text(node, path: str) -> str | None:
    found = node.find(path, NS)
    return found.text if found is not None and found.text else None


def parse_rss(xml_text: str) -> list[dict]:
    """Parse an RSS 2.0 or Atom feed into plain dicts.

    Covers the fields we actually render; unknown extras are ignored rather
    than raising, because feeds in the wild are inconsistent.
    """
    root = ET.fromstring(xml_text.lstrip("\ufeff \n\r\t"))
    entries = root.findall(".//item") or root.findall(".//atom:entry", NS)
    parsed: list[dict] = []

    for entry in entries:
        link = _text(entry, "link")
        if not link:  # Atom puts the URL in an attribute
            anchor = entry.find("atom:link[@rel='alternate']", NS) or entry.find("atom:link", NS)
            link = anchor.get("href") if anchor is not None else None
        if not link:
            continue

        body = _text(entry, "content:encoded") or _text(entry, "description") or ""
        image = None
        for path, attribute in (("media:content", "url"), ("media:thumbnail", "url"), ("enclosure", "url")):
            node = entry.find(path, NS)
            if node is not None and node.get(attribute):
                image = node.get(attribute)
                break
        if not image:
            image = first_image_in(body, link)

        parsed.append({
            "title": clean(_text(entry, "title") or _text(entry, "atom:title")),
            "url": link.strip(),
            # Some feeds put only a thumbnail link in <description>, which cleans
            # away to nothing - fall back to the full content in that case.
            "summary": truncate(clean(_text(entry, "description")) or clean(body)),
            "author": clean(_text(entry, "dc:creator") or _text(entry, "atom:author/atom:name")),
            "category": clean(_text(entry, "category")),
            "image": image,
            "published_at": to_iso(
                _text(entry, "pubDate") or _text(entry, "atom:published") or _text(entry, "atom:updated")
            ),
        })
    return parsed


def make_rss_source(*, id: str, name: str, site: str, feed: str, accent: str = "#8b8b8b", limit: int = 40):
    """Build a source adapter for any site that publishes an RSS/Atom feed.

    Most sites - anything on WordPress, and plenty besides - need nothing
    more than this. See sources/creativereview.py for a worked example.
    """
    def fetch_items(known: dict) -> list[dict]:  # noqa: ARG001 - feeds carry real dates already
        return parse_rss(fetch(feed))[:limit]

    return {
        "id": id,
        "name": name,
        "site": site,
        "feed": feed,
        "accent": accent,
        "fetch_items": fetch_items,
    }
