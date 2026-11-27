import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from send_morning_briefing import build_briefing_prompt, load_style_rules, strip_frontmatter


def test_strip_frontmatter_removes_yaml_block():
    text = "---\nname: x\ndescription: y\n---\n\n# Title\nBody"
    assert strip_frontmatter(text) == "# Title\nBody"


def test_strip_frontmatter_leaves_plain_text_alone():
    assert strip_frontmatter("# Title\nBody") == "# Title\nBody"


def test_load_style_rules_reads_real_skill_without_frontmatter():
    rules = load_style_rules()
    assert not rules.startswith("---")
    assert "name: briefing-style" not in rules
    assert "# Briefing Style" in rules


def test_build_briefing_prompt_inlines_rules_and_data():
    prompt = build_briefing_prompt(
        "RULES-HERE", "sunny", "No events today.", "Inbox empty", "clear", "headlines"
    )
    assert "<style_rules>\nRULES-HERE\n</style_rules>" in prompt
    for piece in ("sunny", "No events today.", "Inbox empty", "clear", "headlines"):
        assert piece in prompt
    # The model must not be told to open any file -- it has no tools.
    assert "Read " not in prompt
