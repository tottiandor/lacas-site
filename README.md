# Laca's Site

A news aggregator for the creative industries. It collects headlines from a list of
publications every night and shows them on one page — newest first, tagged by topic,
filterable by source.

**Status: working prototype, running end to end.** See
[What to fix first](#what-to-fix-first) for the honest list of what a production version
still needs.

---

## How it works

There is no server and no database. Three moving parts:

```
  GitHub Actions (03:10 UTC nightly)
          |
          |  runs scrape.py, which asks each source for its latest stories
          v
  data/news.json          <-- one file, committed back into the repo
          |
          |  the page fetches it on load, and re-checks every 10 minutes
          v
  index.html on GitHub Pages
```

Because the collector commits its results into the repo, GitHub Pages republishes the
site automatically. Hosting costs nothing and there is nothing to keep running.

**Collection is a scheduled job, not something that happens when someone visits.** The
page only ever reads a file. That is what keeps it free, fast and impossible to overload
— but it also means the freshest a story can be is "since last night's run". Run the
workflow by hand any time you want it sooner.

### Two sources cannot be collected from GitHub

**The Drum and Creative Review return `403 Forbidden` to GitHub's servers.** They block
datacenter IP ranges, which is what GitHub Actions runs on. From an ordinary home or
office connection both work fine.

This was diagnosed rather than guessed. On a GitHub runner, *every* User-Agent gets 403
from those two — a plain Chrome string and no User-Agent at all included — while the
other three sources return 200 from the same runner. So it is the IP range, not our bot
identity, and no combination of headers fixes it. (Disguising the request to get around
an IP block would be evasion, not engineering, so it is not attempted.)

What this means in practice:

- The nightly Action still runs and refreshes **Kreatív, The Inspiration and Famous
  Campaigns**. The other two keep the stories they already have and are marked failed,
  so their chips show struck through on the page. Nothing breaks.
- To refresh all five, the collector has to run from a normal connection.
  **`tools/nightly-local.ps1`** does exactly that and pushes the result — one `schtasks`
  line schedules it nightly, and the comment at the top of the file spells it out.
- The two approaches coexist safely: the local run pulls before it pushes, and the
  collector never loses stories, so whichever runs is an improvement on neither running.

If you would rather have everything in one place, the options are a self-hosted Actions
runner on a normal connection, or asking those two publishers for access that does not
depend on IP.

## What's on the page

- **One main feed** with every source mixed together, newest first. Each card is
  colour-dotted and labelled with the publication it came from.
- **A source filter** per site, with counts, so you can read just one publication.
- **Topic tags** on every card. Click one to filter; click again to clear. Tags come from
  the publisher's own tags where they have them, plus a topic vocabulary that works
  across languages — clicking **AI** finds the Hungarian articles about *mesterséges
  intelligencia* as well as the English ones.
- **Search** across headlines, summaries, authors and tags.
- **A Summary button** on each card, opening a popup with a longer extract, the byline,
  the topic tags and a link through to the article.
- **A "New" flag** on anything first collected in the last 24 hours.

### About those summaries

**The summaries are the publisher's own words, not written by us.** Each one is the
description the publication puts in its own feed (or, for sites without feeds, the
opening of the article). The popup says so explicitly — *"Summary published by
&lt;publication&gt;"*.

This was a deliberate choice: the alternative was calling a language model on every new
article, which needs an API key, costs money nightly, and would leave whoever inherits
this with a bill and a dependency. Sticking to the publisher's text means every article
is treated identically, for ever, with nothing to maintain.

If you later decide you do want written summaries, the place to add it is `scrape.py`,
where each item is assembled — set `fullSummary` from the model instead of the feed, and
change the attribution line in `assets/app.js` (`modal-attrib`) so it stops crediting the
publisher for words they did not write.

---

## Where it is

- **Live site:** <https://tottiandor.github.io/lacas-site/>
- **Repository:** <https://github.com/tottiandor/lacas-site>

Already configured: Pages deploys from `main` at the repository root, Actions has write
permission so the collector can commit, and the nightly workflow has run successfully.

To set the same thing up again from scratch (a fork, or a second copy):

1. Push the folder to a GitHub repository.
2. **Settings → Pages →** *Source* → **Deploy from a branch**, branch `main`, folder `/ (root)`.
3. **Settings → Actions → General → Workflow permissions** → **Read and write permissions**.
   Without this the collector cannot commit what it finds.
4. **Actions → Collect news → Run workflow** for the first collection.

> On a public repo, GitHub **disables scheduled workflows after 60 days with no commits**.
> The collector commits most nights, so it keeps itself alive — but if every source goes
> quiet for two months, re-enable it in the Actions tab.

## Running it on your own machine

Needs Python 3.10+ and nothing else — no `pip install`, no `npm`.

```bash
python scrape.py
```

Then, to view the page (opening `index.html` directly will not work, because browsers
block `fetch` on `file://` URLs):

```bash
python -m http.server 8765
```

Visit <http://localhost:8765>.

---

## Adding a site

### The easy way: one command

```bash
python add_site.py https://www.designweek.co.uk
```

That will:

- find the site's RSS feed (checking what the page advertises, then the usual paths);
- fetch it and confirm it actually parses, reporting how many stories it found and how
  many have dates and images;
- check `robots.txt` and **warn you if the site asks crawlers to stay away**;
- work out a sensible id and display name;
- write the entry into `sites.json`.

Then `python scrape.py`, commit, and the site is live. Add `--dry-run` to see what it
would do without changing anything. `--name`, `--id`, `--accent` and `--limit` override
the guesses.

### The manual way

`sites.json` is plain config — no Python involved:

```json
{
  "sites": [
    {
      "id": "designweek",
      "name": "Design Week",
      "site": "https://www.designweek.co.uk/",
      "feed": "https://www.designweek.co.uk/feed/",
      "accent": "#00a8e8"
    }
  ]
}
```

`id`, `name` and `feed` are required; everything else is optional. Set `"enabled": false`
to switch a source off without deleting it.

### When a site has no feed

Some don't — The Drum and Kreatív are both in this category. Those need a small Python
adapter in `sources/`. Copy whichever example is closer:

- **`sources/thedrum.py`** — reads the JSON-LD structured data the site already publishes.
  *Prefer this approach.* Structured data survives redesigns; CSS class names do not.
- **`sources/kreativ.py`** — reads the rendered HTML and Open Graph tags, for sites with
  no structured data at all.

Then import it and add it to `ADAPTERS` in `sources/__init__.py`. An adapter is just a
dict with a `fetch_items(known)` function returning plain dicts — only `title` and `url`
are required:

```python
{
    "title": "Headline",
    "url": "https://...",
    "summary": "Short text for the card.",
    "full_summary": "Longer text for the Summary popup.",
    "image": "https://...",
    "author": "Jane Smith",
    "category": "Advertising",
    "raw_tags": ["ai", "retail"],             # the publisher's own tags
    "published_at": "2026-09-13T09:00:00Z",   # any readable date format
}
```

`known` maps each canonical URL to what is already stored, so an adapter can skip work it
has already done — both examples use it to avoid re-downloading articles they have read.

### Adding a topic tag

`sources/_tags.py` holds the topic vocabulary. Adding one is a single line, and you can
list terms in any language — they all map onto one label:

```python
"Podcasting": ["podcast", "podcasting", "podcaszt"],
```

Terms of five characters or more match as a prefix, which is what makes Hungarian work
(`media` catches `közmédiáért`). Accents are folded, so write them or don't.

Tags are rebuilt from scratch on every run, so **editing the vocabulary retags the whole
archive** the next time the collector runs, not just new stories. That works because each
item keeps the publisher's original tags in `rawTags` alongside the derived ones.

---

## Sources currently configured

| Source | Method | Notes |
|---|---|---|
| [The Drum](https://www.thedrum.com/) | Front-page JSON-LD + per-article metadata | No RSS feed. Honours the site's 5-second crawl-delay and never re-reads an article. Supplies its own editorial tags. **403s from GitHub — needs the local collector.** |
| [Kreatív](https://kreativ.hu/) | Front-page HTML + Open Graph metadata | Hungarian trade press. No feed. **Collected against the site's robots.txt — see below.** |
| [Creative Review](https://www.creativereview.co.uk/) | RSS | Clean feed: images, authors, dates. **403s from GitHub — needs the local collector.** |
| [The Inspiration](https://theinspiration.com/) | RSS | Image-led: cards show a picture and headline but no summary, because the feed carries none. |
| [Famous Campaigns](https://www.famouscampaigns.com/) | RSS | Clean feed, with the publisher's own categories. |

### Two things to know about the source list

**The Inspiration looks like it has stopped publishing.** Its most recent post is a
farewell notice — *"The inspiration 2010 – 2026. Thank You for Being Part of it."* The
adapter works fine and the back catalogue still shows, but do not expect new stories.
Kept in deliberately.

**Kreativ.hu is collected without permission, by an explicit decision.** Its `robots.txt`
opens with `User-agent: * → Disallow: /`, allowing only a named list of crawlers
(Googlebot, Bingbot, Applebot and several AI crawlers). This collector is not on that
list. The site owner reviewed this and chose to add the source anyway.

Whoever inherits this should know, because it becomes their risk to carry:

- The adapter is deliberately light — a 4-second gap between requests, at most 30 article
  pages a night, never the same page twice, and an honest User-Agent so Kreatív can
  identify and block it if they object.
- **To remove it, delete `kreativ.SOURCE` from `ADAPTERS` in `sources/__init__.py`.** That
  is the whole revert; its stored stories then age out.
- Of the five sources it is the most fragile: it reads rendered HTML, so a redesign will
  break it where a feed would not. If it goes quiet, suspect that first.
- Asking Kreatív for permission remains the clean fix. Technically the scrape works
  regardless — the question is whether the site has asked you not to, and it has.

---

## The data file

`data/news.json` is the contract between the collector and the page. Anything that can
produce this shape can feed the site — a different scraper, a CMS export, a manual list.

```jsonc
{
  "generatedAt": "2026-09-14T01:40:11Z",   // last run that actually changed something
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
      "summary": "Short text, shown on the card.",
      "fullSummary": "Longer text, shown in the Summary popup.",
      "tags": ["AI", "Retail"],          // derived; rebuilt every run
      "rawTags": ["ai", "shoppable"],    // the publisher's own, kept so tags can be rebuilt
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

Behaviours worth knowing:

- **Stories are never lost.** Once collected, an item stays even after it drops off the
  source's front page, up to `MAX_ITEMS` (400) in `scrape.py`.
- **A broken source cannot take the site down.** Its previously collected stories are
  kept, the failure is recorded in `sources[].status`, and its chip shows struck through.
- **Duplicates collapse by URL**, ignoring tracking parameters.
- **Unchanged runs write nothing**, so a commit always means real news arrived.
- `datePrecise: false` means the source gave no date and we used first-seen instead. The
  page marks those with an asterisk.

---

## What to fix first

An honest list for whoever takes this on.

**Worth doing early**

- **Decide how the two blocked sources get collected.** Right now they refresh only
  when `tools/nightly-local.ps1` runs on a normal connection. Scheduling that, or
  standing up a self-hosted runner, is the difference between five live sources and
  three.
- **Nobody is told when a source dies.** `sources[].status` is in the JSON and shows as a
  struck-through chip, but silent failure is the most likely thing to go wrong here. A
  weekly Action that opens an issue when a source fails twice running would cover it.
- **Replace The Inspiration**, or accept it as an archive.
- **Tag quality is uneven.** Publisher tags are specific and good; the vocabulary in
  `sources/_tags.py` is broad but hand-written, so it misses topics nobody has added yet.
  Worth reviewing the tag list after a few weeks of real data.
- **Watch the payload.** At ~800 bytes an item, `MAX_ITEMS: 400` is roughly 320 KB. Fine
  now; if you raise it much, split the JSON by page or month.

**When you add more than about ten sources**

- Collection is sequential. Feeds are quick, but sites needing per-article fetches (The
  Drum, Kreatív) are not — roughly 6 minutes for the current five on a cold start. Run
  sources concurrently before this gets annoying.
- The 25-minute workflow timeout will need raising at around 15–20 scraped sites.

**Editorial calls, not technical ones**

- **Summary length.** Cards show 240 characters, the popup 450, always linked and always
  credited. That is normal aggregator practice, but each publisher's terms are their own.
  If the site becomes public and visible, check the syndication terms of any source you
  lean on heavily.
- **Ranking.** Strictly newest-first, so a busy source can dominate. Interleaving by
  source, or a per-source cap on the front page, may read better as the list grows.

---

## File map

```
START-HERE.txt              >>> the first thing a new owner opens <<<
HANDOVER.md                 the onboarding walkthrough (written for Claude Code)
ADDING-A-SITE.md            plain-language guide to adding a publication
README.md                   this file - the technical reference
index.html                  the page
assets/styles.css           all styling (plain CSS, no build step)
assets/app.js               feed loading, filtering, search, tags, summary popup
scrape.py                   the collector - run this
add_site.py                 >>> adds a new site for you: python add_site.py <url> <<<
tools/nightly-local.ps1     collects from this machine and pushes; for the two
                            sources GitHub's IP ranges cannot reach
sites.json                  >>> feed-based sources live here; no Python needed <<<
sources/__init__.py         the source registry (Python adapters + sites.json)
sources/_common.py          HTTP, text cleanup, RSS parsing, the RSS adapter factory
sources/_tags.py            the topic vocabulary
sources/thedrum.py          worked example: no feed, reads JSON-LD
sources/kreativ.py          worked example: no feed, reads Open Graph tags
sources/creativereview.py   worked example: a plain RSS feed
sources/theinspiration.py
sources/famouscampaigns.py
data/news.json              generated - do not edit by hand
.github/workflows/collect.yml   the nightly job
```

If you change `assets/styles.css` or `assets/app.js`, bump the `?v=` number on those two
links in `index.html`. Without it, browsers and the Pages CDN will serve the old file to
people who have visited before.

No dependencies, no build step, no framework, in either the collector or the page. That is
deliberate: it means this still runs in two years without a maintenance weekend first.

---

Headlines, images and summaries belong to the publications that produced them. Every card
links back to the original article.
