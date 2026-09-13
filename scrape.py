#!/usr/bin/env python3
"""Laca's Site - news collector.

Fetches every configured source, merges the results with what we already have,
and writes data/news.json, which is the only thing the web page reads.

Run it locally with:   python scrape.py
"""
from __future__ import annotations

import json
import pathlib
import sys

from sources import SOURCES
from sources._common import canonical_url, clean, id_for, now_iso, to_iso, truncate
from sources._tags import derive_tags

OUTPUT = pathlib.Path(__file__).parent / "data" / "news.json"
MAX_ITEMS = 400  # keep the JSON small enough to load instantly


def load_existing() -> dict:
    if not OUTPUT.exists():
        return {"items": []}
    try:
        return json.loads(OUTPUT.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print("! existing news.json is unreadable, starting fresh")
        return {"items": []}


def normalise(raw: dict, source: dict, stored: dict | None, seen_at: str) -> dict | None:
    url = (raw.get("url") or "").strip()
    title = clean(raw.get("title"))
    if not url or not title:
        return None

    published = to_iso(raw.get("published_at"))
    first_seen = (stored or {}).get("firstSeenAt") or seen_at
    summary = truncate(clean(raw.get("summary")), 240)
    category = clean(raw.get("category"))

    # The longer text shown in the Summary popup. Always the publisher's own
    # words - we never write one - so the popup credits them for it.
    full_summary = truncate(clean(raw.get("full_summary")), 450) or summary
    if not full_summary and stored:
        full_summary = stored.get("fullSummary", "")

    # Publisher-assigned tags only come back on the run that fetched the article,
    # so we keep them. That means tags can be re-derived from scratch every run,
    # and editing the vocabulary in sources/_tags.py retags the whole archive on
    # the next run rather than only affecting new stories.
    raw_tags = raw.get("raw_tags") or (stored or {}).get("rawTags") or []
    tags = derive_tags(title=title, summary=summary, raw_tags=raw_tags, section=category)

    return {
        "id": id_for(url),
        "title": title,
        "url": url,
        "source": source["id"],
        "sourceName": source["name"],
        "accent": source.get("accent", "#8b8b8b"),
        "summary": summary,
        "fullSummary": full_summary,
        "tags": tags,
        "rawTags": raw_tags,   # the publisher's own words, kept so tags can be rebuilt
        "image": raw.get("image") or None,
        "author": clean(raw.get("author")),
        "category": category,
        # Undated items sort by when we first saw them, which for a live feed is
        # a close enough stand-in and keeps the ordering sensible.
        "publishedAt": published or first_seen,
        "datePrecise": bool(published),
        "firstSeenAt": first_seen,
        "enrichAttempts": raw.get("enrich_attempts", (stored or {}).get("enrichAttempts", 0)),
    }


def main() -> int:
    existing = load_existing()
    stored_by_url = {canonical_url(item["url"]): item for item in existing.get("items", [])}
    seen_at = now_iso()

    collected: dict[str, dict] = {}
    reports: list[dict] = []
    failures = 0

    for source in SOURCES:
        print(f"-> {source['name']}")
        try:
            raw_items = source["fetch_items"](stored_by_url)
        except Exception as error:  # noqa: BLE001 - one dead site must not kill the run
            failures += 1
            print(f"   FAILED: {error}")
            kept = [i for i in existing.get("items", []) if i.get("source") == source["id"]]
            for item in kept:
                collected[canonical_url(item["url"])] = item
            reports.append({
                "id": source["id"], "name": source["name"], "site": source["site"],
                "accent": source.get("accent"), "status": "error",
                "error": str(error)[:300], "count": len(kept),
            })
            continue

        count = 0
        for raw in raw_items:
            key = canonical_url(raw.get("url", ""))
            item = normalise(raw, source, stored_by_url.get(key), seen_at)
            if item and key not in collected:
                collected[key] = item
                count += 1
        print(f"   {count} items")
        reports.append({
            "id": source["id"], "name": source["name"], "site": source["site"],
            "accent": source.get("accent"), "status": "ok", "error": None, "count": count,
        })

    # Keep stories that have scrolled off a front page but that we saw earlier.
    for key, item in stored_by_url.items():
        collected.setdefault(key, item)

    items = sorted(collected.values(), key=lambda i: i.get("publishedAt") or "", reverse=True)[:MAX_ITEMS]

    if items == existing.get("items"):
        print(f"\nNo changes ({len(items)} items) - leaving news.json untouched.")
        return 0

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(
            {"generatedAt": seen_at, "itemCount": len(items), "sources": reports, "items": items},
            indent=2, ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )
    print(f"\nWrote {OUTPUT.relative_to(pathlib.Path.cwd())} - {len(items)} items, {failures} source(s) failed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
