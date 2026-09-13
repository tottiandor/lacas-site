"""The Drum - no usable RSS feed, so this adapter reads structured data instead.

The homepage embeds a JSON-LD `CollectionPage` whose `mainEntity.itemListElement`
lists the current front-page stories with their URL, headline and image. That is
far more stable than scraping CSS classes, which change whenever the site is
restyled.

The list carries no publish dates, so we fetch the article page for stories we
have not seen before and read `datePublished`, author and section from its
JSON-LD. Already-stored stories are never re-fetched, and each run enriches at
most ENRICH_LIMIT articles, spaced by the 5 second crawl-delay in the site's
robots.txt.
"""
from __future__ import annotations

import json
import re

from ._common import clean, fetch, truncate

HOME = "https://www.thedrum.com/"
CRAWL_DELAY = 5.0          # seconds, as requested by https://www.thedrum.com/robots.txt
ENRICH_LIMIT = 20          # article pages fetched per run; the rest wait for the next run
LIST_LIMIT = 40            # headlines taken from the front page
MAX_ATTEMPTS = 3           # give up enriching a stubborn page after this many runs

_JSON_LD = re.compile(r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>', re.S | re.I)


def _json_ld_blocks(page_html: str) -> list:
    """Every JSON-LD object on a page, flattened out of any arrays or @graphs."""
    blocks = []
    for raw in _JSON_LD.findall(page_html):
        try:
            parsed = json.loads(raw.strip())
        except json.JSONDecodeError:
            continue
        queue = parsed if isinstance(parsed, list) else [parsed]
        while queue:
            node = queue.pop(0)
            if not isinstance(node, dict):
                continue
            blocks.append(node)
            if isinstance(node.get("@graph"), list):
                queue.extend(node["@graph"])
    return blocks


def _front_page_items() -> list[dict]:
    page = fetch(HOME, crawl_delay=CRAWL_DELAY)
    for block in _json_ld_blocks(page):
        entity = block.get("mainEntity") or {}
        elements = entity.get("itemListElement")
        if not isinstance(elements, list):
            continue
        items = []
        for element in elements:
            url, name = element.get("url"), element.get("name")
            if url and name:
                items.append({
                    "title": clean(name),
                    "url": url,
                    "image": element.get("image"),
                })
        if items:
            return items[:LIST_LIMIT]
    raise RuntimeError("no JSON-LD itemListElement found on The Drum front page")


def _article_details(url: str) -> dict:
    """Publish date, author and section from a single article page."""
    page = fetch(url, crawl_delay=CRAWL_DELAY)
    details: dict = {}

    for block in _json_ld_blocks(page):
        # Articles carry datePublished; the site's video pages are VideoObjects
        # that use uploadDate instead.
        stamp = block.get("datePublished") or block.get("uploadDate")
        if not stamp:
            continue
        details["published_at"] = stamp
        details["category"] = clean(block.get("articleSection") or "")
        author = block.get("author")
        if isinstance(author, list):
            author = author[0] if author else None
        if isinstance(author, dict):
            author = author.get("name")
        details["author"] = clean(author or "")
        # These pages carry no description/og:description, so take a short
        # opening excerpt from articleBody - the same role an RSS summary plays.
        details["summary"] = truncate(
            clean(block.get("description") or block.get("articleBody") or ""), 200
        )
        break

    if not details.get("summary"):
        for tag in re.findall(r"<meta[^>]*>", page):
            if re.search(r'(?:property|name)="(?:og:)?description"', tag, re.I):
                content = re.search(r'content="([^"]*)"', tag, re.I)
                if content:
                    details["summary"] = truncate(clean(content.group(1)), 200)
                    break
    return details


def fetch_items(known: dict) -> list[dict]:
    """`known` maps canonical URL -> the item already stored from earlier runs."""
    from ._common import canonical_url

    items = _front_page_items()
    budget = ENRICH_LIMIT

    for item in items:
        stored = known.get(canonical_url(item["url"]))
        # Anything already stored with a real date is left alone; anything else
        # queues for enrichment, so a backlog drains over successive runs.
        # news.json stores camelCase keys; datePrecise marks an item we have
        # already enriched, so we never pay for the same article page twice.
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
            except Exception as error:  # noqa: BLE001 - one bad article must not fail the source
                print(f"    ! could not enrich {item['url']}: {error}")
        else:
            item["enrich_attempts"] = attempts
    return items


SOURCE = {
    "id": "thedrum",
    "name": "The Drum",
    "site": HOME,
    "feed": None,
    "accent": "#00d1b2",
    "fetch_items": fetch_items,
}
