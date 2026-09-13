"""Famous Campaigns - standard WordPress RSS feed."""
from ._common import make_rss_source

SOURCE = make_rss_source(
    id="famouscampaigns",
    name="Famous Campaigns",
    site="https://www.famouscampaigns.com/",
    feed="https://www.famouscampaigns.com/feed/",
    accent="#7c5cff",
)
