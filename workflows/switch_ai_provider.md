# Switch the automated briefing to a different AI provider

## Objective
Move the unattended briefing (GitHub Actions → `tools/send_morning_briefing.py`)
from Claude to another provider without changing what the briefing does.

## Why it's a small change
The AI is used for exactly two "text in, text out" calls, both through
`tools/llm.py`'s `run_llm()`:
1. Travel-city inference from today's calendar titles.
2. Styling the final briefing. The style rules from
   `.claude/skills/briefing-style/SKILL.md` are inlined into the prompt.

Python fetches all data (Google APIs, weather, RSS) and sends Telegram itself.
The model is never given tools, so any provider's headless CLI works.

## Requirement: free beyond one subscription
Researched November 2026. Re-check before switching, since these terms change:

| Provider | Headless CLI | Free unattended login | Notes |
|---|---|---|---|
| Claude (current) | `claude -p` | Subscription token from `claude setup-token` → `CLAUDE_CODE_OAUTH_TOKEN` secret. Doesn't change between runs. | Cleanest option. |
| Gemini | `gemini -p` | Free Google AI Studio API key → `GEMINI_API_KEY` secret. No billing account; rate-limited, far above 2 calls/day. | On the free tier Google may use prompts to improve its products, and prompts contain email subjects/snippets. AI Pro subscription login in CI is undocumented; don't rely on it. |
| OpenAI | `codex exec` | No free API tier. ChatGPT subscription via `$CODEX_HOME/auth.json`. | The file refreshes on every run and must be saved back after each job. OpenAI advises against it for public repos. Most fragile option. |

## Steps
1. **Add the provider to `PROVIDERS` in `tools/llm.py`.** Each entry needs an
   executable plus arguments that (a) read the prompt from stdin, (b) grant **no
   tools**, and (c) print only the reply text. Check the CLI's current docs for the
   exact flags; never give it shell/file tools, since the briefing prompt contains
   untrusted email text.
2. **Add a test** in `tests/test_llm.py` for the new entry's argument list.
3. **Workflow** (`.github/workflows/morning-briefing.yml`):
   - Replace the "Install Claude Code CLI" step with the new CLI's install, pinned
     to an exact version.
   - Add the provider's secret to the "Send morning briefing" step's `env`.
4. **GitHub repo settings:** add that secret, and set the repo *variable*
   `LLM_PROVIDER` to the new name (Settings → Secrets and variables → Actions →
   Variables).
5. **Test:** run the workflow manually with `force` checked. The briefing must
   arrive with the same five-block format. If the format drifts, adjust wording
   in `build_briefing_prompt()`, not `SKILL.md`, unless the rule itself changes.

## Not affected
- The interactive `/briefing` command stays Claude Code specific (it's a
  Claude Code slash command and skill). Other agents can follow
  `workflows/morning_briefing.md` with `tools/morning_briefing.py` instead.
- The trigger (Apps Script → `workflow_dispatch`) and Telegram commands are
  provider-independent.
