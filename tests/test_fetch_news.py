import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from fetch_news import format_headlines_block, parse_rss_items

SAMPLE_RSS = """<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <title>Sample Feed</title>
    <item>
      <title>First headline</title>
      <description>A short description of the first story.</description>
    </item>
    <item>
      <title>Second headline</title>
      <description>Another description here.</description>
    </item>
  </channel>
</rss>
"""

SAMPLE_RSS_MISSING_DESCRIPTION = """<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <item>
      <title>Headline with no description</title>
    </item>
  </channel>
</rss>
"""

SAMPLE_RSS_EMPTY = """<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <title>Empty Feed</title>
  </channel>
</rss>
"""


def test_parse_rss_items_normal():
    items = parse_rss_items(SAMPLE_RSS)
    assert items == [
        {"title": "First headline", "description": "A short description of the first story."},
        {"title": "Second headline", "description": "Another description here."},
    ]


def test_parse_rss_items_respects_limit():
    items = parse_rss_items(SAMPLE_RSS, limit=1)
    assert len(items) == 1
    assert items[0]["title"] == "First headline"


def test_parse_rss_items_missing_description():
    items = parse_rss_items(SAMPLE_RSS_MISSING_DESCRIPTION)
    assert items == [{"title": "Headline with no description", "description": ""}]


def test_parse_rss_items_empty_feed():
    assert parse_rss_items(SAMPLE_RSS_EMPTY) == []


def test_parse_rss_items_malformed_xml():
    assert parse_rss_items("this is not xml at all <<<") == []


def test_format_headlines_block_populated():
    headlines = {
        "World": [{"title": "Big story", "description": "Details here."}],
        "Spain": [],
        "Switzerland": [{"title": "Local news", "description": ""}],
    }
    block = format_headlines_block(headlines)
    assert "World:" in block
    assert "- Big story -- Details here." in block
    assert "Spain:" not in block  # empty category omitted
    assert "Switzerland:" in block
    assert "- Local news" in block


def test_format_headlines_block_all_empty():
    headlines = {"World": [], "Spain": [], "Switzerland": [], "Europe": [], "Financial": []}
    assert format_headlines_block(headlines) == "No headlines available."
