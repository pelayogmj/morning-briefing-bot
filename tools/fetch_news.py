"""Fetch headline data for the briefing's optional news section.

Deterministic, no Claude involved -- same pattern as weather/calendar/
Gmail: this module only gathers raw data; judging what's actually
significant enough to mention is left entirely to the headless Claude
render step (see tools/send_morning_briefing.py and
.claude/skills/briefing-style/SKILL.md).

All feeds are free, public RSS -- no API key needed (verified live
before relying on them; some commonly-cited alternatives, e.g. the
other El Pais RSS URL, turned out to be dead since 2020).

FEEDS is labeled by what each source actually is: World/Europe/Spain/
Switzerland are regions; Financial is a cross-cutting markets topic,
not a 5th region -- kept as its own distinct label so the prompt built
from this data doesn't imply otherwise.
"""
import sys
import xml.etree.ElementTree as ET

import requests

FEEDS = {
    "World": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "Europe": "https://feeds.bbci.co.uk/news/world/europe/rss.xml",
    "Spain": "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada",
    "Switzerland": "https://www.srf.ch/news/bnf/rss/1646",
    "Financial": "https://feeds.content.dowjones.io/public/rss/mw_topstories",
}

DEFAULT_LIMIT_PER_FEED = 8
REQUEST_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; MorningBriefingBot/1.0)"}


def parse_rss_items(xml_text, limit=DEFAULT_LIMIT_PER_FEED):
    """Extract up to `limit` {title, description} dicts from raw RSS XML.

    Returns [] for an empty/malformed feed rather than raising -- a
    single bad feed should degrade gracefully (skip that category),
    never crash the whole briefing.
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    items = []
    for item in root.findall(".//item")[:limit]:
        title = (item.findtext("title") or "").strip()
        description = (item.findtext("description") or "").strip()
        if title:
            items.append({"title": title, "description": description})
    return items


def fetch_feed(url, timeout=10):
    response = requests.get(url, timeout=timeout, headers=REQUEST_HEADERS)
    response.raise_for_status()
    return response.text


def fetch_all_headlines(limit_per_feed=DEFAULT_LIMIT_PER_FEED):
    """Fetch all configured feeds. Each feed's failure is independently
    non-fatal -- news is an enhancement on an otherwise-complete
    briefing, not core data (same philosophy as the travel-location
    inference), so one dead/slow feed just means one missing category,
    not a failed run.
    """
    headlines_by_category = {}
    for category, url in FEEDS.items():
        try:
            items = parse_rss_items(fetch_feed(url), limit=limit_per_feed)
        except requests.RequestException as exc:
            print(
                f"Warning: could not fetch {category} news feed ({exc}); skipping.",
                file=sys.stderr,
            )
            items = []
        headlines_by_category[category] = items
    return headlines_by_category


def format_headlines_block(headlines_by_category):
    """Build one plain-text, category-labeled block for the styled-
    rendering prompt. Categories with no items (fetch failed, or
    genuinely empty) are omitted from the block entirely."""
    lines = []
    for category, items in headlines_by_category.items():
        if not items:
            continue
        lines.append(f"{category}:")
        for item in items:
            if item["description"]:
                lines.append(f"- {item['title']} -- {item['description']}")
            else:
                lines.append(f"- {item['title']}")

    if not lines:
        return "No headlines available."
    return "\n".join(lines)
