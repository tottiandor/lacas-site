# Adding a new publication

*Written for Laca. No coding required.*

This is the thing you'll do most often, so it's worth having one page that
covers it properly. Keep this open the first few times; after that you won't
need it.

---

## The whole job, in one line

Open the project in Claude Code and type:

```bash
python3 add_site.py https://www.designweek.co.uk
```

Swap in whichever publication you want. Use the site's normal home page address
— you don't need to find anything special.

That single command:

- finds the site's **feed** (a machine-readable list of their latest articles,
  which most publications quietly publish)
- fetches it and checks it actually works
- tells you how many stories it found, and how many have pictures and dates
- **checks whether the site has asked not to be visited by programs like ours**
- picks a sensible short name and a colour
- adds it to the list of sources

**Try it with `--dry-run` first.** That shows you the whole report and changes
nothing:

```bash
python3 add_site.py https://www.designweek.co.uk --dry-run
```

---

## Reading what it tells you

A good result looks like this:

```
Looking at https://www.designweek.co.uk
  OK   robots.txt allows it
  searching for a feed...

  feed:    https://www.designweek.co.uk/feed/
  title:   Design Week
  stories: 20
  of those, 20 have a date and 20 have an image

  most recent:
    - 7 things to look out for at LDF 2026
    - FLUORO crafts lo-fi brand world for R.A.D's debut skate shoe
```

Things worth glancing at:

| Line | What you want to see |
|---|---|
| `robots.txt` | **OK**. If it says WARN, read the section below before continuing. |
| `stories` | More than a handful. If it says 1 or 2, it may be the wrong feed. |
| `have a date` | Ideally all of them. Without dates, stories sort oddly. |
| `have an image` | Not essential — cards without pictures still look fine. |
| `most recent` | Recognisable, recent headlines from that publication. |

If the headlines look wrong — comments, job ads, one section of the site rather
than its news — it has probably found a secondary feed. Tell Claude Code and it
can point at the right one.

---

## Making it live

Once you're happy, run it for real (the same command without `--dry-run`), then:

```bash
python3 scrape.py
```

That collects from your new source for the first time. It can take a few
minutes. Then send it up:

```bash
git add -A
git commit -m "Add Design Week"
git push
```

Those three lines are one idea: **save what changed, and send it up.** You'll
use the same three for every change you ever make. Change the words in quotes to
describe what you did.

Your live site updates a minute or two later.

---

## Changing your mind

**To turn a source off without deleting it**, open `sites.json` and add one line
to its entry:

```json
{
  "id": "designweek",
  "name": "Design Week",
  "site": "https://www.designweek.co.uk/",
  "feed": "https://www.designweek.co.uk/feed/",
  "enabled": false
}
```

It stops collecting. Its existing stories fade out of the feed over time. Set it
back to `true` whenever you like.

**To remove it completely**, delete its block from `sites.json`.

Either way, run `python3 scrape.py` afterwards and push, as above.

---

## When it says there's no feed

You'll see:

```
No RSS feed found.

This site needs a Python adapter instead.
```

That's not a failure on your part — some publications simply don't publish a
feed. Those need a small piece of custom code written for that one site.

That's a developer job, or something you can ask Claude Code to do for you. Two
of your five sources are already like this — The Drum and Kreatív — and they're
in the project specifically as worked examples for whoever writes the next one.

Rough guide: a site with a feed takes a minute. A site without one takes an hour
of someone's time, and is more likely to break later if that publication
redesigns their website.

---

## When it warns you about robots.txt

You'll see:

```
WARN robots.txt asks crawlers like ours not to read this site
```

**Stop and think about this one.**

`robots.txt` is a file websites publish saying which automated visitors they do
and don't want. It isn't a lock — nothing technically stops you — it's a request
written down in a standard place.

Ignoring it isn't illegal exactly. But it is a publication saying no, and you
work in their industry. The practical risks are ordinary ones: they block you
without warning and that source quietly dies, or somebody notices and it's an
awkward conversation with people you'd rather be friendly with.

**The clean move is a short email asking.** Most publishers are happy to be
included in something that credits them and sends them readers. It costs you one
message and makes the source dependable instead of precarious.

One of your five sources — Kreatív — is in exactly this position. It was added
deliberately with the previous owner's knowledge, not by accident. The reasoning
and the one-line way to remove it are both written down in `README.md`. You
inherit that decision, so it's worth knowing it's there.

---

## If something goes wrong

Tell Claude Code exactly what you see, including the error message word for
word. That's almost always enough.

Common ones:

**"command not found: python"** — on a Mac the command is `python3`, with a
three. Try again with `python3`.

**"CERTIFICATE_VERIFY_FAILED"** — Python can't read websites yet. Open Finder →
Applications → Python 3.x and double-click **Install Certificates.command**.
Wait for it to finish, then try again. This is the most common Mac problem and
it only has to be done once.

**"already in sites.json"** — you've already added that one. Nothing to do.

**The new source shows zero stories on the site** — run `python3 scrape.py`. The
site only shows what the last collection found; adding a source doesn't collect
from it by itself.

**The site looks unchanged after pushing** — give it two minutes, then reload.
If it's still stale, press Cmd+Shift+R to force a fresh copy.
