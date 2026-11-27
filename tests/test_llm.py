import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from llm import LLMError, build_command


def test_build_command_claude_grants_no_tools():
    command = build_command("claude")
    assert command[1:3] == ["-p", "--permission-prompts"]
    tools_index = command.index("--tools")
    assert command[tools_index + 1] == ""
    assert "--allowedTools" not in command


def test_build_command_unknown_provider_raises():
    with pytest.raises(LLMError, match="Unknown LLM_PROVIDER 'nope'"):
        build_command("nope")
