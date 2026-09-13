"""THEINSPIRATION.COM - WordPress RSS feed.

Note: this feed is image-led. Items carry a thumbnail and a title but no text
summary, so cards for this source render without a description. That is the
feed's own shape, not a parsing failure.
"""
from ._common import make_rss_source

SOURCE = make_rss_source(
    id="theinspiration",
    name="The Inspiration",
    site="https://theinspiration.com/",
    feed="https://theinspiration.com/feed/",
    accent="#f5b301",
)
