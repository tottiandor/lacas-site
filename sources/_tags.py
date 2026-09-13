"""Topic tagging.

Two kinds of tag end up on an article:

1. **Editorial tags the publisher already assigned** - The Drum's JSON-LD
   `keywords`, Kreatív's /tag/ links, RSS <category> elements. These are the
   specific ones ("Anatomy of an Ad", "9-11").

2. **Topic tags matched from the vocabulary below** - the broad, consistent ones
   ("AI", "Advertising", "Branding") that make filtering useful across the whole
   feed.

The vocabulary is deliberately bilingual. Kreatív publishes in Hungarian, so
matching both languages onto one English label means clicking "AI" finds the
Hungarian articles about mesterséges intelligencia too. That cross-language
filtering is the main reason this file exists rather than just passing the
publishers' own tags straight through.

Adding a topic is one line. Accents are folded before matching, so "reklám" and
"reklam" both hit, and you can write either form.
"""
from __future__ import annotations

import re
import unicodedata

# Canonical label -> terms that should match it, in any language.
TOPICS: dict[str, list[str]] = {
    "AI": ["ai", "a.i.", "artificial intelligence", "genai", "generative ai", "chatgpt",
           "openai", "llm", "machine learning", "deepfake", "algorithm",
           "mesterseges intelligencia", "gepi tanulas"],
    "Advertising": ["advertising", "advert", "ad campaign", "ad of the day", "commercial",
                    "adland", "reklam", "hirdetes", "reklamfilm"],
    "Agencies": ["agency", "agencies", "adland", "holding company", "wpp", "omnicom",
                 "publicis", "havas", "dentsu", "ugynokseg"],
    "Branding": ["brand", "branding", "rebrand", "brand identity", "logo", "marka",
                 "markaepites", "arculat"],
    "Campaigns": ["campaign", "kampany"],
    "Design": ["design", "graphic design", "designer", "dizajn", "tervezo"],
    "Typography": ["typography", "typeface", "font", "lettering", "tipografia", "betutipus"],
    "Photography": ["photography", "photographer", "photo series", "fotografia", "fotos", "foto"],
    "Illustration": ["illustration", "illustrator", "illusztracio"],
    "Packaging": ["packaging", "pack design", "csomagolas"],
    "Film & TV": ["film", "cinema", "movie", "tv", "television", "streaming", "netflix",
                  "documentary", "mozi", "televizio", "teve", "sorozat", "dokumentumfilm"],
    "Music": ["music", "album", "song", "band", "spotify", "zene", "dal", "zenekar"],
    "Gaming": ["gaming", "video game", "esports", "roblox", "fortnite", "twitch",
               "jatek", "videojatek"],
    "Social Media": ["social media", "tiktok", "instagram", "snapchat", "influencer",
                     "creator economy", "youtube", "reddit", "kozossegi media"],
    "Media": ["media", "publisher", "newspaper", "broadcast", "journalism", "sajto",
              "ujsagiro", "mediapiac"],
    "Retail": ["retail", "supermarket", "shopper", "ecommerce", "e-commerce", "amazon",
               "kiskereskedelem", "bolt", "webshop"],
    "Sport": ["sport", "football", "soccer", "olympics", "fifa", "uefa", "nfl", "f1",
              "foci", "labdarugas", "olimpia"],
    "Fashion": ["fashion", "luxury", "couture", "streetwear", "divat"],
    "Food & Drink": ["food", "drink", "beer", "coffee", "snack", "restaurant", "mcdonald",
                     "etel", "ital", "vendeglatas", "sor", "kave"],
    "Sustainability": ["sustainability", "climate", "greenwashing", "net zero", "carbon",
                       "fenntarthatosag", "klima", "kornyezetvedelem"],
    "Health": ["health", "charity", "nhs", "mental health", "cancer", "alzheimer",
               "egeszseg", "jotekonysag", "korhaz"],
    "Awards": ["award", "cannes lions", "d&ad", "clio", "effie", "shortlist", "jury",
               "dij", "palyazat", "zsuri", "nevezes"],
    "OOH": ["ooh", "out of home", "billboard", "outdoor advertising", "poster campaign",
            "oriasplakat", "plakat"],
    "B2B": ["b2b", "business to business"],
    "Politics": ["politics", "election", "government", "minister", "policy",
                 "politika", "valasztas", "kormany", "miniszter"],
    "Careers": ["hire", "hiring", "appoints", "appointment", "promoted", "joins",
                "redundanc", "layoff", "karrier", "kinevez", "csatlakozik", "tavozik"],
    "Business": ["acquisition", "acquires", "merger", "revenue", "profit", "ipo",
                 "funding", "investment", "felvasarlas", "bevetel", "beruhazas"],
}

# Tags that should not be title-cased.
ACRONYMS = {"ai", "ooh", "tv", "usa", "uk", "us", "b2b", "b2c", "dei", "cgi", "vr", "ar",
            "nft", "seo", "pr", "cmo", "ceo", "cco", "bbc", "itv", "nhs", "f1", "fifa",
            "uefa", "nfl", "mi", "rtl"}

# Publisher tags that add nothing - site-wide boilerplate rather than a topic.
STOPWORDS = {"featured", "news", "uncategorised", "uncategorized", "kreativ",
             "kreativ online", "kreativ magazin", "napi friss", "cikk", "home"}

MAX_TAGS = 6


def fold(text: str) -> str:
    """Lowercase and strip accents, so Hungarian matches with or without them."""
    decomposed = unicodedata.normalize("NFKD", (text or "").lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def prettify(raw: str) -> str:
    """Turn a slug or loose label into a presentable tag."""
    text = re.sub(r"[-_/]+", " ", (raw or "").strip()).strip()
    text = re.sub(r"\s+", " ", text)
    if not text:
        return ""
    words = []
    for word in text.split(" "):
        words.append(word.upper() if fold(word) in ACRONYMS else
                     (word if word[:1].isupper() else word.capitalize()))
    return " ".join(words)


def _term_pattern(term):
    """Match a term at a word start, allowing suffixes on anything long enough.

    Hungarian is agglutinative - "media" has to match "kozmediaert" - and English
    inflects too ("brand" -> "branding"). So terms of five characters or more match
    as a prefix. Short ones keep a closing boundary, because "ai" matching as a
    prefix would tag every article containing "aid".
    """
    folded = re.escape(fold(term))
    return '\\b' + folded + ("" if len(term) >= 5 else '\\b')


_TOPIC_PATTERNS = {
    label: re.compile("|".join(_term_pattern(t) for t in terms))
    for label, terms in TOPICS.items()
}

# A publisher calling something "Artificial Intelligence" and us calling it "AI"
# should produce one tag, not two. Map every vocabulary term to its canonical label.
_SYNONYMS = {fold(term): label for label, terms in TOPICS.items() for term in terms}
_SYNONYMS.update({fold(label): label for label in TOPICS})


def derive_tags(*, title: str = "", summary: str = "", raw_tags=None, section: str = "") -> list[str]:
    """Editorial tags first, then any topics matched from title and summary."""
    tags: list[str] = []
    seen: set[str] = set()

    def add(candidate: str) -> None:
        label = prettify(candidate)
        # Collapse a publisher's wording onto our canonical label where they mean
        # the same thing, so "Artificial Intelligence" and "AI" do not both appear.
        label = _SYNONYMS.get(fold(label), label)
        key = fold(label)
        if not label or key in seen or key in STOPWORDS or len(label) > 34:
            return
        seen.add(key)
        tags.append(label)

    # 1. What the publisher called it.
    if section:
        add(section)
    for raw in (raw_tags or []):
        add(raw)

    # 2. What the vocabulary recognises. Matched on title and summary only -
    #    matching the publisher's own tags too would just restate them.
    haystack = fold(f"{title} {summary}")
    for label, pattern in _TOPIC_PATTERNS.items():
        if fold(label) not in seen and pattern.search(haystack):
            add(label)

    return tags[:MAX_TAGS]
