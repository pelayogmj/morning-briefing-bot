"""Provider-neutral "text in, text out" LLM call for the automated briefing.

Every prompt this project sends is fully self-contained (all data and the
style rules are already in it), so the model is never granted any tools --
that is what makes swapping providers a one-setting change. Pick the
provider with the LLM_PROVIDER env var (default: claude). To add another
provider, see workflows/switch_ai_provider.md.
"""
import os
import shutil
import subprocess

DEFAULT_PROVIDER = "claude"
TIMEOUT_SECONDS = 300

# provider -> (executable, args). Each entry must: read the prompt from
# stdin, grant the model no tools at all, and print only the reply text.
PROVIDERS = {
    "claude": (
        "claude",
        ["-p", "--permission-prompts", "none", "--tools", "", "--output-format", "text"],
    ),
}


class LLMError(RuntimeError):
    pass


def build_command(provider):
    """Return the argv list for `provider`. Raises LLMError if unknown.

    shutil.which (not the bare name) resolves platform-specific
    executable extensions -- on Windows an npm global install is a .cmd
    wrapper, which subprocess.run's list form can't find on its own.
    """
    if provider not in PROVIDERS:
        known = ", ".join(sorted(PROVIDERS))
        raise LLMError(f"Unknown LLM_PROVIDER '{provider}' (known: {known})")
    executable, args = PROVIDERS[provider]
    return [shutil.which(executable) or executable, *args]


def run_llm(prompt, provider=None):
    """Send `prompt` to the configured provider and return its reply text.

    The prompt goes via stdin, not as an argument: a multi-line argument
    gets truncated at the first newline when Windows routes a .cmd
    wrapper through cmd.exe. encoding="utf-8" is explicit because the
    briefing uses emoji, which Windows' default cp1252 can't decode.
    """
    provider = provider or os.environ.get("LLM_PROVIDER") or DEFAULT_PROVIDER
    result = subprocess.run(
        build_command(provider),
        input=prompt,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=TIMEOUT_SECONDS,
    )
    if result.returncode != 0:
        raise LLMError(
            f"{provider} failed (exit {result.returncode}): {result.stderr.strip()}"
        )
    return result.stdout.strip()
