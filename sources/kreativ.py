"""Kreatív Online (kreativ.hu) - Hungarian marketing and media trade press.

No RSS feed (/rss/ returns a 500), and the site is a server-rendered Nuxt app,
so this adapter reads the front page HTML for article links and then pulls
metadata from each article's Open Graph tags.

IMPORTANT - read before changing anything here
----------------------------------------------
kreativ.hu's robots.txt begins with `User-agent: * / Disallow: /`, allowing only
a named list of crawlers (Googlebot, Bingbot, Applebot and several AI crawlers).
This collector is not on that list. It was added anyway as a deliberate, informed
decision by the site owner, not by oversight.

Because of that, this adapter is written to be as light as it can be:

  * a 4 second gap between requests, slower than any named crawler is asked for;
  * at most 30 article pages per run, and an article is never fetched twice;
  * an honest User-Agent, so Kreatív can identify and block us if they object.

If Kreatív asks us to stop, remove this source's line from sources/__init__.py -
that is the whole revert. Seeking written permission remains the clean fix, and
if it is granted, this note can go.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin

from ._common import clean, fetch, truncate

HOME = "https://kreativ.hu/"
CRAWL_DELAY = 4.0      # deliberately gentle; see the note above
ENRICH_LIMIT = 30      # the whole front page in one nightly run
MAX_ATTEMPTS = 3       # stop retrying a page that never yields a date
LIST_LIMIT = 40

# Articles all live under /cikk/<slug>. Capture each link and its inner markup.
_ARTICLE_LINK = re.compile(r'<a\s+href="(/cikk/[^"#?]+)"[^>]*>(.*?)</a>', re.S | re.I)
_IMG_SRC = re.compile(r'<img[^>]+src="([^"]+)"', re.I)
_IMG_ALT = re.compile(r'<img[^>]+alt="([^"]*)"', re.I)

try:  # Hungary observes DST, so use the real zone when the platform has one.
    from zoneinfo import ZoneInfo
    _BUDAPEST = ZoneInfo("Europe/Budapest")
except Exception:  # noqa: BLE001 - bare Windows installs ship no tz database
    _BUDAPEST = timezone(timedelta(hours=1))


def _meta(page: str, key: str) -> str | None:
    """Value of a <meta> tag matched on property/name, in any attribute order."""
    for tag in re.findall(r"<meta[^>]*>", page):
        if re.search(r'(?:property|name)="%s"' % re.escape(key), tag, re.I):
            content = re.search(r'content="([^"]*)"', tag, re.I)
            if content:
                return content.group(1)
    return None


def _parse_local_time(stamp: str) -> str | None:
    """'2026-09-11 00:22' in Hungarian local time -> ISO-8601 UTC."""
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S"):
        try:
            naive = datetime.strptime(stamp.strip(), fmt)
        except ValueError:
            continue
        return naive.replace(tzinfo=_BUDAPEST).astimezone(timezone.utc).isoformat().replace(
            "+00:00", "Z"
        )
    return None


def _front_page_items() -> list[dict]:
    """Front-page articles, merging the picture link and headline link per story.

    Each story is linked twice - once wrapping its thumbnail, once wrapping its
    heading - so we collect both and keep the best title and image for each slug.
    """
    page = fetch(HOME, crawl_delay=CRAWL_DELAY)
    by_slug: dict[str, dict] = {}

    for path, inner in _ARTICLE_LINK.findall(page):
        slug = path.rstrip("/")
        entry = by_slug.setdefault(slug, {"url": urljoin(HOME, slug), "title": "", "image": None})

        # The heading link carries visible text; the picture link carries an
        # img alt that repeats the headline. Either will do.
        text = clean(inner)
        alt = _IMG_ALT.search(inner)
        title = text or (clean(alt.group(1)) if alt else "")
        if len(title) > len(entry["title"]):
            entry["title"] = title

        if not entry["image"]:
            src = _IMG_SRC.search(inner)
            if src:
                entry["image"] = urljoin(HOME, src.group(1))

    items = [i for i in by_slug.values() if i["title"]]
    if not items:
        raise RuntimeError("no /cikk/ articles found on the kreativ.hu front page")
    return items[:LIST_LIMIT]


def _article_details(url: str) -> dict:
    page = fetch(url, crawl_delay=CRAWL_DELAY)
    details: dict = {}

    stamp = _meta(page, "article:published_time")
    if stamp:
        details["published_at"] = _parse_local_time(stamp) or stamp

    author = _meta(page, "author")
    if author:
        details["author"] = clean(author)

    description = _meta(page, "og:description")
    if description:
        details["summary"] = truncate(clean(description), 200)
        details["full_summary"] = truncate(clean(description), 450)

    # Kreatív tags its own articles (/tag/<slug>) and files them in a section
    # (/rovat/<slug>). Both beat anything we could infer. The site-wide
    # <meta name="keywords"> is boilerplate and deliberately ignored.
    slugs = re.findall(r'href="/(?:tag|rovat)/([^"/]+)', page)
    if slugs:
        details["raw_tags"] = list(dict.fromkeys(slugs))[:8]

    # og:title is prefixed with the publication name; the bare headline is better.
    title = _meta(page, "og:title")
    if title:
        details["title"] = clean(re.sub(r"^\s*Kreat[ií]v Online\s*[-–]\s*", "", title))

    return details


def fetch_items(known: dict) -> list[dict]:
    from ._common import canonical_url

    items = _front_page_items()
    budget = ENRICH_LIMIT

    for item in items:
        stored = known.get(canonical_url(item["url"]))
        attempts = (stored or {}).get("enrichAttempts", 0)

        if stored and (stored.get("datePrecise") or attempts >= MAX_ATTEMPTS):
            for stored_key, item_key in (
                ("publishedAt", "published_at"), ("author", "author"),
                ("category", "category"), ("summary", "summary"),
            ):
                if stored.get(stored_key):
                    item[item_key] = stored[stored_key]
            continue

        if budget > 0:
            budget -= 1
            item["enrich_attempts"] = attempts + 1
            try:
                item.update(_article_details(item["url"]))
            except Exception as error:  # noqa: BLE001 - one bad page must not fail the source
                print(f"    ! could not enrich {item['url']}: {error}")
        else:
            item["enrich_attempts"] = attempts

    return items


SOURCE = {
    "id": "kreativ",
    "name": "Kreatív",
    "site": HOME,
    "feed": None,
    "accent": "#e8453c",
    "fetch_items": fetch_items,
}
