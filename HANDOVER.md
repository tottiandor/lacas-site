# Handover walkthrough

**This file is written for Claude Code, not for Laca.** It is the script for
onboarding him. Follow it in order.

## Who you are talking to

Laca has taken over this project. He works in the creative industries and is
not a developer. He has never used Python, Git, GitHub or a terminal, and has
none of them installed. He is on Windows. He does not have a GitHub account.

He is not stupid — he simply has not done this before. Explain things the way
you would to a smart colleague from a different department.

## How to run this walkthrough

**Rules, in order of importance:**

1. **One step at a time.** Never give him two commands at once. Give one, wait,
   confirm it worked, then continue.
2. **Verify before moving on.** After every install, run the check command
   yourself and tell him what you saw. Do not take "I think it worked" as done.
3. **Run things for him where you can.** You have a terminal. He does not need
   to learn one today. Ask permission, then run it yourself and report back.
4. **No unexplained jargon.** "Repository", "commit", "push", "terminal" all get
   one plain sentence the first time they appear. Never two new words at once.
5. **When something fails, that is normal.** Say so. Ask him to paste exactly
   what he sees. Do not make him feel he broke it.
6. **Let him stop.** At the end of each stage, tell him what is done and what is
   next, so he can walk away and come back.

Deliver the quoted text below in your own voice — it is the substance to cover,
not a script to recite word for word. Adapt to what he says.

---

## Stage 1 — What this thing is

> Hello Laca. I'm going to walk you through this from the very beginning, and
> I'll assume you've never done any of it. Nothing today requires you to write
> code. You can stop whenever you like and pick it up later.
>
> **You've been handed a news website.** Every night it visits five
> creative-industry publications, collects their latest headlines, and puts them
> on one page — so you read across all five in one place instead of visiting
> five websites.
>
> The version it was built on is live here:
> **https://tottiandor.github.io/lacas-site/**
>
> Open it and have a click around before we touch anything:
>
> - The coloured buttons along the top filter by publication.
> - The row underneath filters by topic. Click **AI** — you'll notice it finds
>   the Hungarian articles about *mesterséges intelligencia* as well as the
>   English ones. That's deliberate.
> - Every card has a **Summary** button that opens a longer extract, and a
>   **Read** link that goes to the publisher's own page.
> - The search box searches headlines, summaries, authors and topics at once.

Wait for him to actually look. Ask what he thinks before continuing.

> One thing worth saying plainly, because it matters if this ever gets busy:
> **the site never hosts anyone's articles.** It shows a headline, a picture and
> a couple of sentences that the publisher themselves put out for this purpose,
> and every route leads back to their own website. Those summaries are the
> publishers' own words, not written by us or by me — the popup says so on every
> card. That's the difference between an aggregator and a copyright problem.

---

## Stage 2 — How it works

Keep this short. He needs the shape, not the detail.

> There are three pieces. Once these make sense, everything else follows.
>
> **1. The collector.** A program that visits the five sites and writes down
> what it finds. It's a file called `scrape.py`. When it runs, it produces one
> file of results: `data/news.json`. That file *is* your site's contents.
>
> **2. The schedule.** GitHub — the free service where the project lives — runs
> that collector automatically every night, around 5am. You don't start it.
> Your computer doesn't need to be on. It just happens.
>
> **3. The page.** The website reads that one results file and draws the cards.
> That's all it does.
>
> ```
>   Every night:   the collector visits the 5 sites
>                            ↓
>                  it writes data/news.json
>                            ↓
>                  the website shows what's in it
> ```
>
> It's built this way because it costs nothing and there's nothing to keep
> running or pay for. There is no server. Left completely alone, it keeps
> collecting news every night indefinitely.

Then, only once that has landed:

> **One honest wrinkle.** Two of the five — The Drum and Creative Review —
> refuse connections that come from GitHub's computers. Not from yours; from
> theirs. It's a blanket block on data-centre addresses, nothing personal.
>
> So the automatic nightly run refreshes three of the five. The other two keep
> the stories they already have, and their buttons appear crossed out on the
> page so you can see at a glance. Nothing breaks.
>
> There's an optional one-line fix that runs the collector from your own
> computer instead, where all five work. We'll do it at the end if you want it.
> The site is perfectly usable either way.

---

## Stage 3 — Installing the four things

First tell him what's coming and why, then do them **one at a time**.

> Four things to install. Here's what each is for, so they're not just names:
>
> | What | What it's for |
> |---|---|
> | **Python** | The language the collector is written in. The engine. |
> | **Git** | Moves files between your computer and GitHub. |
> | **A GitHub account** | Free. Where the project lives and where the site is hosted. |
> | **GitHub CLI** | Lets me set GitHub up for you instead of you clicking through menus. |
>
> We'll do them in that order and check each one before moving on.

### 3a. Python

Send him to **https://www.python.org/downloads/** — the big yellow "Download
Python" button.

> **The one thing that matters:** on the first screen of the installer there's a
> checkbox at the bottom saying **"Add python.exe to PATH"**. Tick it before you
> click Install. It's easy to miss and it's the single most common thing that
> goes wrong here. If you miss it, we can fix it, it's just fiddly — so have a
> look before clicking.

Then verify yourself:

```bash
python --version
```

Expect `Python 3.10` or higher. If it says "not found", he almost certainly
missed the PATH checkbox — the fix is to re-run the installer, choose Modify,
and tick it. He may need to close and reopen Claude Code afterwards.

### 3b. Git

Send him to **https://git-scm.com/download/win**. The download starts on its
own. The installer asks a lot of questions — tell him to accept every default
and keep clicking Next.

```bash
git --version
```

### 3c. GitHub account

Send him to **https://github.com/signup**.

> GitHub is where the project will live and where the site is hosted from, both
> free. You'll need a username — it appears in your site's web address, so pick
> something you're happy with. If you choose `lacanews`, your site ends up at
> `lacanews.github.io/lacas-site`.
>
> Use an email address you'll keep. Confirm the email when it arrives, or the
> account won't work properly.

Ask him what username he chose and use it for the rest of the walkthrough.

### 3d. GitHub CLI

Send him to **https://cli.github.com/** (or `winget install --id GitHub.cli`).

```bash
gh --version
```

Then connect it to his account:

```bash
gh auth login
```

Walk him through the prompts: **GitHub.com** → **HTTPS** → **Yes** (authenticate
Git) → **Login with a web browser**. It shows a one-time code; he presses Enter,
the browser opens, he pastes the code and approves.

Confirm with `gh auth status`, and tell him which account it says he is.

> That's the installing done — the only genuinely tedious part. Everything from
> here is quick.

---

## Stage 4 — Run it on his own machine first

Prove it works locally before involving GitHub. It's reassuring and it isolates
problems.

```bash
python scrape.py
```

It takes 5–7 minutes the first time. Tell him that **before** you run it, or
he'll think it has frozen. Explain what's scrolling past: each source being
visited in turn.

Then show him the site running locally:

```bash
python -m http.server 8765
```

and send him to **http://localhost:8765**.

> That's the whole site, running on your own computer, built from the file the
> collector just wrote. Nobody else can see it — it's yours until we publish it.

Explain why opening `index.html` directly doesn't work (browsers block pages
from loading data files off the local disk) so he doesn't try it later and think
it's broken. Stop the server with Ctrl+C when he's done looking.

---

## Stage 5 — Publish it as his own

He is creating **his own copy**, not taking over the original. Say so plainly —
the original keeps running, and his is independent from here on.

Explain the two words he'll keep seeing, once each:

> **Repository** ("repo") — a project folder that GitHub stores and tracks the
> history of. **Push** — sending your changes up to it.

Then do it for him. Ask permission first, then run:

```bash
git init -b main
git add -A
git commit -m "Laca's Site"
gh repo create lacas-site --public --source=. --remote=origin --push
```

If git complains it doesn't know who he is, set it for this project only:

```bash
git config user.name "Laca"
git config user.email "<the email he signed up with>"
```

Then turn on the two settings the collector needs — do these yourself:

```bash
gh api -X PUT repos/<username>/lacas-site/actions/permissions/workflow -f default_workflow_permissions=write
gh api -X POST repos/<username>/lacas-site/pages -f "source[branch]=main" -f "source[path]=/"
```

> The first lets the nightly collector save what it finds. The second switches
> on the free website hosting.

Then run the first collection on GitHub:

```bash
gh workflow run collect.yml --repo <username>/lacas-site
```

Give it a couple of minutes, then send him to
**https://&lt;username&gt;.github.io/lacas-site/**

> That's yours, live on the internet, on your own address. From tonight it
> updates itself while you sleep.

Expect The Drum and Creative Review to show crossed out — remind him that's the
data-centre block from Stage 2, not something he did.

---

## Stage 6 — Adding a new site

**This is the most important stage.** It is the thing he will actually do again
and again, and he should be able to do it without help. Do not rush it, and have
him do it himself rather than watching you.

> This is the part worth learning properly, because it's the thing you'll come
> back to. Adding a publication is usually one line.
>
> Say you want to add Design Week:
>
> ```
> python add_site.py https://www.designweek.co.uk
> ```
>
> That's it. It goes away and does all of this on its own:
>
> - finds the site's **feed** — a machine-readable list of their latest
>   articles that most publications quietly publish
> - fetches it and checks it actually works, and tells you how many stories it
>   found and how many have pictures and dates
> - **checks whether the site has asked not to be visited by programs like ours,
>   and warns you if it has**
> - picks a sensible name and colour
> - adds it to the list

Have him run it with `--dry-run` first, so he can see the report without
anything changing:

```bash
python add_site.py https://www.designweek.co.uk --dry-run
```

Read the output with him. Then let him run it for real, followed by:

```bash
python scrape.py
git add -A
git commit -m "Add Design Week"
git push
```

Explain those last three as one idea: *save what changed, and send it up.* He
will use that same trio for everything.

Then have him watch the new source appear on his live site a minute later. That
moment is what makes the whole thing feel like his.

### The two things he must understand about adding sites

> **1. Some sites don't have a feed.** The tool will tell you so, in plain
> words. Those need a small piece of custom code — that's a job for a developer,
> or for me if you ask. Two of your five are already like that, and they're
> there as worked examples for whoever does it.
>
> **2. If it warns you about `robots.txt`, stop and think.** That file is how a
> website says who it does and doesn't want visiting. Ignoring it isn't illegal
> exactly — but it's a publication telling you no, and you work in their
> industry. The right move is a short email asking.
>
> One of your five sites is in exactly that position. It was added knowingly,
> not by accident, and the reasoning is written down in the project so it isn't
> a surprise to you later. If that publication ever objects, removing them is
> one line, and `README.md` says which one.

Point him at `ADDING-A-SITE.md` as the page to come back to. He does not need to
read it now.

---

## Stage 7 — Living with it

Cover briefly, then stop:

- **How to tell it's working.** The "Updated X ago" line at the top right. If
  that says days rather than hours, something needs looking at.
- **A crossed-out button** means that source failed on the last run. Its old
  stories are still there. Usually it fixes itself; if it doesn't for a week,
  that source needs attention.
- **The two blocked sources.** Offer the optional fix now: `tools/nightly-local.ps1`
  runs the collection from his own computer, where all five work, and can be
  scheduled nightly with one command — the instructions are in the top of that
  file. His PC has to be awake. If it isn't, nothing breaks.
- **The Inspiration has stopped publishing.** Its last post is a farewell
  notice. Its back catalogue still shows. He may want to replace it — which, now
  he knows Stage 6, he can do himself.

Finish by telling him what he can now do unaided: add a site, run a collection,
publish a change, and tell whether it's healthy. That's the whole job.

---

## If he wants to change how it looks

Colours, fonts and spacing are in `assets/styles.css`. Tell him to ask you
rather than editing it himself, and remind him of the one rule: **after changing
`assets/styles.css` or `assets/app.js`, bump the `?v=` number in `index.html`**,
or browsers keep showing people the old version.
