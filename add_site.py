#!/usr/bin/env python3
"""Add a news source to Laca's Site.

    python add_site.py https://www.designweek.co.uk
    python add_site.py https://www.designweek.co.uk --name "Design Week"
    python add_site.py https://example.com/feed/ --dry-run

Give it a site's homepage. It finds the RSS feed, checks the feed actually works,
warns you if the site's robots.txt asks crawlers to stay away, and writes the entry
into sites.json. Then run `python scrape.py` and the site is live.

If no feed can be found, the site needs a Python adapter instead - copy
sources/thedrum.py or sources/kreativ.py and adapt it. The README explains how.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import urllib.robotparser
from urllib.parse import urljoin, urlparse

from sources._common import USER_AGENT, clean, fetch, parse_rss

ROOT = pathlib.Path(__file__).resolve().parent
CONFIG = ROOT / "sites.json"

# Tried in order when the homepage does not advertise a feed itself.
COMMON_PATHS = [
    "/feed/", "/feed", "/rss/", "/rss", "/rss.xml", "/feed.xml",
    "/atom.xml", "/index.xml", "/blog/feed/", "/news/feed/", "/?feed=rss2",
]

FEED_LINK = re.compile(
    r'<link[^>]+type=["\']application/(?:rss|atom)\+xml["\'][^>]*>', re.I
)


def normalise_start(raw: str) -> str:
    url = raw.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def declared_feeds(page: str, base: str) -> list[str]:
    """Feed URLs the page advertises in <link rel="alternate">."""
    found = []
    for tag in FEED_LINK.findall(page):
        href = re.search(r'href=["\']([^"\']+)["\']', tag, re.I)
        if not href:
            continue
        url = urljoin(base, href.group(1))
        # Comment feeds are noise - they carry reader comments, not articles.
        if re.search(r"comments?/?(feed)?/?$", url, re.I):
            continue
        if url not in found:
            found.append(url)
    return found


def validate(url: str) -> tuple[list[dict], str] | None:
    """Return (items, feed title) if this URL is a usable feed, else None."""
    try:
        body = fetch(url, retries=0, timeout=20)
    except Exception:  # noqa: BLE001 - a candidate that fails is simply not the feed
        return None
    if "<rss" not in body[:2000].lower() and "<feed" not in body[:2000].lower():
        return None
    try:
        items = parse_rss(body)
    except Exception:  # noqa: BLE001 - malformed XML means not usable
        return None
    if not items:
        return None
    title = re.search(r"<title[^>]*>(.*?)</title>", body, re.S | re.I)
    return items, clean(title.group(1)) if title else ""


def discover(start: str) -> tuple[str, list[dict], str] | None:
    """Find a working feed for a site. Returns (feed url, items, feed title)."""
    # The URL given might already be the feed.
    result = validate(start)
    if result:
        print(f"  that URL is itself a feed")
        return start, result[0], result[1]

    try:
        page = fetch(start, timeout=20)
    except Exception as error:  # noqa: BLE001
        print(f"  could not open {start}: {error}")
        page = ""

    candidates = declared_feeds(page, start) if page else []
    if candidates:
        print(f"  page advertises {len(candidates)} feed(s)")
    candidates += [urljoin(start, path) for path in COMMON_PATHS]

    tried = set()
    for candidate in candidates:
        if candidate in tried:
            continue
        tried.add(candidate)
        result = validate(candidate)
        if result:
            return candidate, result[0], result[1]
    return None


def robots_verdict(start: str) -> tuple[bool, str]:
    """Whether robots.txt lets an unnamed crawler read this site."""
    robots_url = urljoin(start, "/robots.txt")
    parser = urllib.robotparser.RobotFileParser()
    parser.set_url(robots_url)
    try:
        parser.read()
    except Exception:  # noqa: BLE001 - no robots.txt is not a refusal
        return True, "no robots.txt found (that is fine - it means no restrictions)"
    if parser.can_fetch(USER_AGENT, start) and parser.can_fetch("*", start):
        return True, "robots.txt allows it"
    return False, "robots.txt asks crawlers like ours not to read this site"


def suggest_id(start: str, feed_title: str) -> str:
    host = urlparse(start).netloc.lower()
    host = re.sub(r"^(www|feeds?)\.", "", host)
    stem = host.split(".")[0]
    return re.sub(r"[^a-z0-9]", "", stem) or re.sub(r"[^a-z0-9]", "", feed_title.lower())[:20]


def suggest_name(feed_title: str, site_id: str) -> str:
    # Feed titles are often "Design Week - Feed" or "Design Week » Articles".
    name = re.split(r"\s*[-–»|]\s*", feed_title)[0].strip() if feed_title else ""
    name = re.sub(r"\s*\b(rss|feed|atom|news feed)\b\s*$", "", name, flags=re.I).strip()
    return name or site_id.capitalize()


def load_config() -> dict:
    if not CONFIG.exists():
        return {"sites": []}
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Add a news source to Laca's Site.")
    parser.add_argument("url", help="the site's homepage (or its feed, if you know it)")
    parser.add_argument("--name", help="display name; taken from the feed if omitted")
    parser.add_argument("--id", dest="site_id", help="short id; taken from the domain if omitted")
    parser.add_argument("--accent", help="dot colour, e.g. #00a8e8")
    parser.add_argument("--limit", type=int, default=40, help="max stories per run (default 40)")
    parser.add_argument("--dry-run", action="store_true", help="report only, change nothing")
    args = parser.parse_args()

    start = normalise_start(args.url)
    print(f"\nLooking at {start}")

    allowed, reason = robots_verdict(start)
    print(f"  {'OK  ' if allowed else 'WARN'} {reason}")

    print("  searching for a feed...")
    found = discover(start)
    if not found:
        print(
            "\nNo RSS feed found.\n\n"
            "This site needs a Python adapter instead. Copy sources/thedrum.py\n"
            "(JSON-LD) or sources/kreativ.py (Open Graph tags), adapt the parsing,\n"
            "then add it to ADAPTERS in sources/__init__.py. See the README.\n"
        )
        return 1

    feed_url, items, feed_title = found
    site_id = (args.site_id or suggest_id(start, feed_title)).lower()
    name = args.name or suggest_name(feed_title, site_id)

    print(f"\n  feed:    {feed_url}")
    print(f"  title:   {feed_title or '(none)'}")
    print(f"  stories: {len(items)}")
    dated = sum(1 for i in items if i.get("published_at"))
    imaged = sum(1 for i in items if i.get("image"))
    print(f"  of those, {dated} have a date and {imaged} have an image")
    print("\n  most recent:")
    for item in items[:3]:
        print(f"    - {item['title'][:70]}")

    config = load_config()
    if any(entry.get("id") == site_id for entry in config["sites"]):
        print(f"\n{site_id!r} is already in sites.json. Nothing to do.")
        return 1
    if any(entry.get("feed") == feed_url for entry in config["sites"]):
        print(f"\nThat feed is already in sites.json under a different id. Nothing to do.")
        return 1

    entry = {"id": site_id, "name": name, "site": start, "feed": feed_url}
    if args.accent:
        entry["accent"] = args.accent
    if args.limit != 40:
        entry["limit"] = args.limit

    print("\n  entry to add:")
    for line in json.dumps(entry, indent=2, ensure_ascii=False).split("\n"):
        print("    " + line)

    if not allowed:
        print(
            "\n  WARNING: this site's robots.txt asks crawlers like ours to stay away.\n"
            "  A feed is published for syndication, so reading it is a normal thing to do,\n"
            "  but the site has still asked. Consider emailing them before switching it on."
        )

    if args.dry_run:
        print("\nDry run - sites.json not changed.\n")
        return 0

    config["sites"].append(entry)
    CONFIG.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"\nAdded {name} to sites.json.")
    print("Next:  python scrape.py     then commit sites.json and data/news.json\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
