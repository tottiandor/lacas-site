"""The list of sites Laca's Site pulls from.

There are two ways a site gets in, and you almost always want the first.

1. **sites.json** (in the project root) - for any site with an RSS feed. No Python,
   no code review, just a few lines of config. Easiest way by far:

       python add_site.py https://www.designweek.co.uk

   That finds the feed, checks it works, warns you if the site's robots.txt asks
   crawlers to stay away, and writes the entry for you.

2. **A Python adapter in this folder** - only needed when a site has no feed and
   has to be read some other way. sources/thedrum.py and sources/kreativ.py are
   the two worked examples. Import it below and add it to ADAPTERS.

Both kinds end up in SOURCES and are treated identically from there on.
"""
from __future__ import annotations

import json
import pathlib

from . import creativereview, famouscampaigns, kreativ, thedrum, theinspiration
from ._common import make_rss_source

# Sites that need their own parsing code because they publish no feed.
ADAPTERS = [
    thedrum.SOURCE,
    kreativ.SOURCE,
]

# Sites kept as Python files for historical reasons, though a plain feed is all
# they need. New feed-based sites should go in sites.json instead of here.
ADAPTERS += [
    creativereview.SOURCE,
    theinspiration.SOURCE,
    famouscampaigns.SOURCE,
]

CONFIG = pathlib.Path(__file__).resolve().parent.parent / "sites.json"

# Fallback dot colours, used when an entry in sites.json does not name one.
PALETTE = ["#7c5cff", "#00d1b2", "#ff4d4d", "#f5b301", "#e8453c", "#3d8bfd",
           "#ff7a45", "#25c2a0", "#d65db1", "#8bc34a"]


def _from_config() -> list[dict]:
    """Feed-based sites declared in sites.json."""
    if not CONFIG.exists():
        return []
    try:
        raw = json.loads(CONFIG.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise SystemExit(f"sites.json is not valid JSON: {error}") from error

    built = []
    for index, entry in enumerate(raw.get("sites", [])):
        if entry.get("enabled") is False:
            continue
        missing = [key for key in ("id", "name", "feed") if not entry.get(key)]
        if missing:
            raise SystemExit(f"sites.json entry #{index + 1} is missing: {', '.join(missing)}")
        built.append(make_rss_source(
            id=entry["id"],
            name=entry["name"],
            site=entry.get("site") or entry["feed"],
            feed=entry["feed"],
            accent=entry.get("accent") or PALETTE[index % len(PALETTE)],
            limit=int(entry.get("limit", 40)),
        ))
    return built


def _build() -> list[dict]:
    sources = ADAPTERS + _from_config()
    seen: set[str] = set()
    for source in sources:
        if source["id"] in seen:
            raise SystemExit(f"two sources share the id {source['id']!r} - ids must be unique")
        seen.add(source["id"])
    return sources


SOURCES = _build()
