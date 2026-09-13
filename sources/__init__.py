"""The list of sites Laca's Site pulls from.

ADDING A NEW SITE
-----------------
1. Create sources/<yoursite>.py.
2. If the site has an RSS feed (most do - try <site>/feed/ or <site>/rss.xml),
   copy sources/creativereview.py and change the four values. That's the whole job.
   If it has no feed, copy sources/thedrum.py and adapt the parsing.
3. Import it below and add its SOURCE to the list.

Nothing else in the project needs to change: the scraper, the JSON feed and the
front end all pick the new source up automatically.
"""
from . import creativereview, famouscampaigns, kreativ, thedrum, theinspiration

SOURCES = [
    thedrum.SOURCE,
    creativereview.SOURCE,
    theinspiration.SOURCE,
    famouscampaigns.SOURCE,
    kreativ.SOURCE,
]
