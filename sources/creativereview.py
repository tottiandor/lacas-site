"""Creative Review - standard WordPress RSS feed, so the generic adapter covers it.

This file is the template to copy when adding a new site that has a feed.
"""
from ._common import make_rss_source

SOURCE = make_rss_source(
    id="creativereview",
    name="Creative Review",
    site="https://www.creativereview.co.uk/",
    feed="https://www.creativereview.co.uk/feed/",
    accent="#ff4d4d",
)
