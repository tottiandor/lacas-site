# Laca's Site

A prototype news aggregator for the creative industries. It collects headlines from
a list of publications and shows them on one page, newest first, updating on its own
throughout the day.

**Status: working prototype.** It runs end to end and is ready to be handed to whoever
builds it out. See [What to fix first](#what-to-fix-first) for the honest list of what a
production version still needs.

---

## How it works

There is no server and no database. The whole thing is three moving parts:

```
  GitHub Actions (every 20 min)
          |
          |  runs scrape.py, which asks each source for its latest stories
          v
  data/news.json          <-- one file, committed back into the repo
          |
          |  the page fetches it, and re-fetches every 90 seconds
          v
  index.html on GitHub Pages
```

Because the collector commits its results into the repo, GitHub Pages republishes the
site automatically. Hosting cost is zero and there is nothing to keep running.

**How live is "live"?** New stories appear within roughly 20–40 minutes of publication.
GitHub runs scheduled jobs on a best-effort basis, so the gap varies. That is genuinely
quasi-live rather than instant — see [What to fix first](#what-to-fix-first) if you need
it faster.

---

## Getting it online

1. Push this folder to a GitHub repository.
2. **Settings → Pages →** set *Source* to **Deploy from a branch**, branch `main`, folder `/ (root)`.
3. **Settings → Actions → General →** under *Workflow permissions*, select
   **Read and write permissions**. Without this the collector cannot commit what it finds.
4. **Actions → Collect news → Run workflow** to do the first collection by hand.

The site is then live at `https://<your-username>.github.io/<repo-name>/`.

> One gotcha worth knowing: on a public repo, GitHub **disables scheduled workflows after
> 60 days with no commits**. The collector commits regularly, so it keeps itself alive —
> but if all sources go quiet for two months, re-enable it in the Actions tab.

## Running it on your own machine

Needs Python 3.10+ and nothing else — no `pip install`, no `npm`.

```bash
python scrape.py
```

Then, to view the page (opening `index.html` directly will not work, because the browser
blocks `fetch` on `file://` URLs):

```bash
python -m http.server 8765
```

Visit <http://localhost:8765>.

---

## Adding a site

This is the part that was designed to be easy. **One new file, one new line.**

### If the site has an RSS feed

Most do. Try `https://thesite.com/feed/` or `/rss.xml` in a browser — if you get a wall of
XML, you are in business. Copy `sources/creativereview.py` and change the values:

```python
# sources/designweek.py
from ._common import make_rss_source

SOURCE = make_rss_source(
    id="designweek",                             # short, no spaces; used internally
    name="Design Week",                          # shown on the site
    site="https://www.designweek.co.uk/",        # linked in the footer
    feed="https://www.designweek.co.uk/feed/",   # the feed itself
    accent="#00a8e8",                            # the source's dot colour
)
```

Then register it in `sources/__init__.py`:

```python
from . import creativereview, designweek, famouscampaigns, thedrum, theinspiration

SOURCES = [
    ...
    designweek.SOURCE,
]
```

That is the whole job. Titles, links, images, authors, categories and publication dates
are all pulled out automatically.

### If the site has no feed

Copy `sources/thedrum.py` instead and adapt it. It is the worked example of a site with
no feed, and it shows the approach worth copying: **look for structured data before you
parse HTML.** The Drum's homepage embeds a JSON-LD listing of its front-page stories,
which survives site redesigns; CSS class names do not.

An adapter is just a dictionary with a `fetch_items(known)` function. That function
returns a list of plain dicts, and every key except `title` and `url` is optional:

```python
{
    "title": "Headline",
    "url": "https://...",
    "summary": "One or two sentences.",
    "image": "https://...",
    "author": "Jane Smith",
    "category": "Advertising",
    "published_at": "2026-09-13T09:00:00Z",  # any readable date format
}
```

`known` maps each canonical URL to what is already stored, so an adapter can skip work it
has already done. `sources/thedrum.py` uses it to avoid re-downloading article pages it
has already read.

### Before you add a site, check two things

1. **`https://thesite.com/robots.txt`** — if `User-agent: *` is followed by
   `Disallow: /`, the site is asking not to be crawled. Respect it, or write and ask
   them for permission.
2. **Does it set a `Crawl-delay`?** If so, pass it to `fetch(url, crawl_delay=N)` as
   `sources/thedrum.py` does.

---

## Sources currently configured

| Source | Method | Notes |
|---|---|---|
| [The Drum](https://www.thedrum.com/) | Front-page JSON-LD + per-article metadata | No RSS feed. Honours the site's 5-second crawl-delay; reads at most 20 new article pages per run and never re-reads one. |
| [Creative Review](https://www.creativereview.co.uk/) | RSS | Clean feed: images, authors, dates. ~12 items. |
| [The Inspiration](https://theinspiration.com/) | RSS | Image-led, so cards have no summary text. **See the warning below.** |
| [Famous Campaigns](https://www.famouscampaigns.com/) | RSS | Clean feed. ~10 items. |
| [Kreatív](https://kreativ.hu/) | Front-page HTML + Open Graph metadata | Hungarian trade press. No feed. **Added by owner decision despite robots.txt — see below.** ~25 items. |

### Two things to know about the source list

**The Inspiration appears to have closed.** Its most recent post is titled *"The
inspiration 2010 – 2026. Thank You for Being Part of it."* — a farewell notice. The
adapter works, but the well may have run dry. Worth replacing with a live publication.

**Kreativ.hu is collected without permission, by an explicit decision.** Its
`robots.txt` opens with `User-agent: * → Disallow: /`, allowing only a named list of
crawlers (Googlebot, Bingbot, Applebot and several AI crawlers). This collector is not on
that list. The site owner reviewed this and chose to add the source anyway.

Whoever inherits this should know that, because it is now their risk to carry:

- The adapter is written to be as light as possible — a 4-second gap between requests
  (slower than any named crawler is asked for), at most 10 article pages per run, never
  the same page twice, and an honest User-Agent so Kreatív can identify and block it.
- **To remove it, delete its line from `sources/__init__.py`.** That is the whole revert;
  its stored stories then age out of the feed.
- **The clean fix is a short email to Kreatív asking to be allowed.** They maintain that
  file carefully, so there is a real person to ask, and a clearly-identified aggregator
  that links back is an easy yes for many publishers. If permission comes, delete the
  warning block at the top of `sources/kreativ.py` and nothing else changes.
- Of the five sources this is the most fragile: it reads rendered HTML, so a site redesign
  will break it where an RSS feed would not. If it starts returning nothing, that is the
  first thing to suspect.

---

## The data file

`data/news.json` is the contract between the collector and the page. Anything that can
produce this shape can feed the site — a different scraper, a CMS export, a manual list.

```jsonc
{
  "generatedAt": "2026-09-13T22:52:04Z",   // last run that actually changed something
  "itemCount": 107,
  "sources": [
    { "id": "thedrum", "name": "The Drum", "site": "https://...",
      "accent": "#00d1b2", "status": "ok", "error": null, "count": 40 }
  ],
  "items": [
    {
      "id": "3db295ad",                    // stable hash of the URL
      "title": "Headline",
      "url": "https://...",
      "source": "thedrum",
      "sourceName": "The Drum",
      "accent": "#00d1b2",
      "summary": "One or two sentences.",
      "image": "https://...",
      "author": "Jane Smith",
      "category": "Advertising",
      "publishedAt": "2026-09-13T09:00:00Z",
      "datePrecise": true,                 // false = we fell back to first-seen time
      "firstSeenAt": "2026-09-13T09:12:00Z",
      "enrichAttempts": 1
    }
  ]
}
```

A few behaviours worth knowing:

- **Stories are never lost.** Once collected, an item stays in the file even after it
  drops off the source's front page, up to `MAX_ITEMS` (400) in `scrape.py`.
- **A broken source cannot take the site down.** If a source fails, its previously
  collected stories are kept, the failure is recorded in `sources[].status`, and its chip
  on the page shows struck through.
- **Duplicates collapse by URL**, ignoring tracking parameters, so the same story picked
  up twice appears once.
- **Unchanged runs write nothing**, which keeps the commit history meaningful — a commit
  means real news arrived.
- `datePrecise: false` means the source gave us no date and we used the time we first saw
  the story instead. The page marks those with an asterisk.

---

## What to fix first

An honest list for whoever takes this on.

**Worth doing early**

- **Replace The Inspiration** with a publication that is still publishing.
- **Get written permission from Kreatív**, as above. It is the one source running
  against a site's stated wishes, and the only one that carries any real risk.
- **Add a `/health` view.** `sources[].status` is already in the JSON but only surfaces as
  a struck-through chip. A source that silently dies is the most likely failure here, and
  right now nobody gets told. A weekly Action that opens an issue when a source fails
  twice running would cover it.
- **Watch the payload size.** At ~600 bytes per item, `MAX_ITEMS: 400` is about 250 KB —
  fine. If you raise it much past that, split the JSON by page or by month.

**When you add more than ~10 sources**

- Collection is currently sequential. Feeds are fast, but sites needing per-article
  fetches (like The Drum) are not. Run sources concurrently before this becomes a problem.
- Consider moving from "commit the JSON" to a small API if the commit noise gets tiring.
  The front end only needs the JSON shape above to stay the same.

**Editorial decisions that are not really technical**

- **Summary length.** Cards show up to 240 characters and always link to the publisher.
  That is normal aggregator practice, but each publisher's terms are their own, and a
  cease-and-desist is cheaper to avoid than to answer. If the site becomes public and
  visible, it is worth a quick check of each source's syndication terms — and a friendly
  email to any publisher you are leaning on heavily.
- **Ranking.** Everything is strictly newest-first. A busy source can dominate the top of
  the page. Interleaving by source, or a simple per-source cap on the front page, may read
  better once there are more sites.

---

## File map

```
index.html                  the page
assets/styles.css           all styling (plain CSS, no build step)
assets/app.js               fetch, filter, search, auto-refresh (no framework)
scrape.py                   the collector - run this
sources/__init__.py         >>> the list of sites; add yours here <<<
sources/_common.py          HTTP, text cleanup, RSS parsing, the RSS adapter factory
sources/thedrum.py          worked example: a site with no feed
sources/creativereview.py   worked example: a site with a feed (copy this one)
sources/theinspiration.py
sources/famouscampaigns.py
sources/kreativ.py            worked example: a site with no feed, using Open Graph tags
data/news.json              generated - do not edit by hand
.github/workflows/collect.yml   the every-20-minutes job
```

No dependencies, no build step, no framework, in either the collector or the page. That is
deliberate: it means this still runs in two years without a maintenance weekend first.

---

Headlines, images and summaries belong to the publications that produced them. Every card
links back to the original article.
