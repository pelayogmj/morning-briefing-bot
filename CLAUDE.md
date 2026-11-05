# Agent Instructions

You're working inside the **WAT framework** (Workflows, Agents, Tools). This architecture separates concerns so that probabilistic AI handles reasoning while deterministic code handles execution. That separation is what makes this system reliable.

## The WAT Architecture

**Layer 1: Workflows (The Instructions)**
- Markdown SOPs stored in `workflows/`
- Each workflow defines the objective, required inputs, which tools to use, expected outputs, and how to handle edge cases
- Written in plain language, the same way you'd brief someone on your team

**Layer 2: Agents (The Decision-Maker)**
- This is your role. You're responsible for intelligent coordination.
- Read the relevant workflow, run tools in the correct sequence, handle failures gracefully, and ask clarifying questions when needed
- You connect intent to execution without trying to do everything yourself
- Example: If you need to pull data from a website, don't attempt it directly. Read `workflows/scrape_website.md`, figure out the required inputs, then execute `tools/scrape_single_site.py`

**Layer 3: Tools (The Execution)**
- Python scripts in `tools/` that do the actual work
- API calls, data transformations, file operations, database queries
- Credentials and API keys are stored in `.env`
- These scripts are consistent, testable, and fast

**Why this matters:** When AI tries to handle every step directly, accuracy drops fast. If each step is 90% accurate, you're down to 59% success after just five steps. By offloading execution to deterministic scripts, you stay focused on orchestration and decision-making where you excel.

## How to Operate

**1. Look for existing tools first**
Before building anything new, check `tools/` based on what your workflow requires. Only create new scripts when nothing exists for that task.

**2. Learn and adapt when things fail**
When you hit an error:
- Read the full error message and trace
- Fix the script and retest (if it uses paid API calls or credits, check with me before running again)
- Document what you learned in the workflow (rate limits, timing quirks, unexpected behavior)
- Example: You get rate-limited on an API, so you dig into the docs, discover a batch endpoint, refactor the tool to use it, verify it works, then update the workflow so this never happens again

**3. Keep workflows current**
Workflows should evolve as you learn. When you find better methods, discover constraints, or encounter recurring issues, update the workflow. That said, don't create or overwrite workflows without asking unless I explicitly tell you to. These are your instructions and need to be preserved and refined, not tossed after one use.

## The Self-Improvement Loop

Every failure is a chance to make the system stronger:
1. Identify what broke
2. Fix the tool
3. Verify the fix works
4. Update the workflow with the new approach
5. Move on with a more robust system

This loop is how the framework improves over time.

## File Structure

**What goes where:**
- **Deliverables**: Final outputs go to cloud services (Google Sheets, Slides, etc.) where I can access them directly
- **Intermediates**: Temporary processing files that can be regenerated

**Directory layout:**
```
.tmp/           # Temporary files (scraped data, intermediate exports). Regenerated as needed.
tools/          # Python scripts for deterministic execution
workflows/      # Markdown SOPs defining what to do and how
.env            # API keys and environment variables (NEVER store secrets anywhere else)
credentials.json, token.json  # Google OAuth (gitignored)
```

**Core principle:** Local files are just for processing. Anything I need to see or use lives in cloud services. Everything in `.tmp/` is disposable.

## Conventions (added Stage 1)

- **Language**: Python 3.13, run through the project's virtualenv at `.venv/`.
  - Setup: `python -m venv .venv` then `.venv/Scripts/python.exe -m pip install -r requirements.txt`
  - Run a tool: `.venv/Scripts/python.exe tools/<script>.py`
  - Run tests: `.venv/Scripts/python.exe -m pytest`
- **Tests**: live in `tests/`, one file per tool (e.g. `tests/test_get_weather.py`). Keep pure logic (parsing, formatting) in small functions separate from network/IO calls so it's testable without live API calls.
- **Never commit secrets**: `.env`, `credentials.json`, and `token.json` are gitignored — real values only ever go in `.env`, never hardcoded in `tools/` scripts or committed elsewhere.

## Conventions (added Stage 2)

- **MCP vs. direct API access — pick based on whether a human session is involved:**
  - MCP servers (added via `claude mcp add`) let *me* (Claude, in an interactive session) call a tool while you're actively chatting. They have no independent trigger — nothing invokes them on their own.
  - Anything that must run unattended (e.g. a 7am scheduled briefing with no one watching) cannot rely on MCP. It needs its own direct API access instead — see `tools/google_auth.py`, which both `tools/get_calendar.py` and `tools/get_gmail.py` use for direct, non-MCP Google API calls.
  - Rule of thumb: interactive/ad hoc → MCP is fine. Scheduled/unattended → direct API only.
- **Google OAuth**: `credentials.json` (OAuth client, downloaded from Google Cloud Console, type "Desktop app") and `token.json` (cached user token + refresh token, generated by the one-time interactive consent flow) are both gitignored and must never be committed. New dependencies for this: `google-api-python-client`, `google-auth-httplib2`, `google-auth-oauthlib`.
- **MCP config scope**: `.mcp.json` (created by `claude mcp add --scope project ...`) lives at the project root and is committed/shareable with anyone who clones the repo. `--scope user` instead stores config outside the repo, private to one person across all their projects, and never appears in `.mcp.json`.

## Conventions (added Stage 3)

- **Skills vs. tools — different layers, don't confuse them**: `tools/` scripts gather raw *data* deterministically (weather/calendar/email). Presenting that data as a human-readable briefing is a separate, Claude-rendered layer: `.claude/skills/briefing-style/SKILL.md` holds the tone/format rules, and `.claude/commands/briefing.md` (invoked as `/briefing`) is what actually runs the tools and applies that skill. A skill has no effect on a standalone script — it only shapes *my* output while I'm actively working.
- **`/briefing`'s fixed format**: always exactly three lines in order — greeting+weather, calendar, email — never reordered or merged into a paragraph. See `.claude/skills/briefing-style/SKILL.md` for the exact rules; edit that file (not this one) to change the briefing's tone/format.
- **Retry transient network errors, don't just fail**: `tools/get_weather.py`'s `fetch_forecast` retries up to 3 times (2s delay) on `ConnectionResetError` before giving up, since Open-Meteo resets connections occasionally for no real reason. Reserve this pattern for genuinely transient errors — don't retry on actual HTTP error responses.

## Conventions (added Stage 4)

- **Hooks enforce; prompts only ask.** This project's `.claude/settings.json` wires four hooks, all implemented as small, testable scripts in `.claude/hooks/` (logic lives in Python, not opaque JSON matcher strings):
  - `block_sensitive_read.py` (PreToolUse/`Read`): blocks reading `.env`, `credentials.json`, or `token.json` outright.
  - `block_destructive_bash.py` (PreToolUse/`Bash`): blocks `rm -rf`, `git push --force`/`-f`, `git reset --hard`, `git clean -f` — an enforced backstop on Claude's own existing safety guidelines.
  - `require_security_review.py` (PreToolUse/`Bash`): blocks `git commit` unless a security review has been recorded for the *currently staged* diff (see below).
  - `run_tests_on_py_edit.py` (PostToolUse/`Edit|Write`): runs `pytest` automatically after any `.py` file is edited and surfaces failures immediately. Can't block the edit (already happened), only report.
- **Security-review gate is a custom convention, not a built-in Claude Code feature.** Hooks have no memory of what happened earlier in a session, so "has a review already run?" is tracked via `.claude/.security-review-passed` (gitignored) — a hash of `git diff --cached` written by `tools/mark_security_reviewed.py`. Workflow: run the `security-review` skill (or, if it can't run — e.g. no `origin` remote configured — do a manual review) → confirm it's clean → `.venv/Scripts/python.exe tools/mark_security_reviewed.py` → then `git commit` is unblocked for that exact staged diff. Any further staging changes invalidate it again.
- **Subagent**: `.claude/agents/email-triager.md` — reads unread email via `tools/get_gmail.py` and returns a ranked shortlist by urgency. Runs in its own isolated context; invoke explicitly ("use the email-triager subagent...") or let Claude match it by task.

## Bottom Line

You sit between what I want (workflows) and what actually gets done (tools). Your job is to read instructions, make smart decisions, call the right tools, recover from errors, and keep improving the system as you go.

Stay pragmatic. Stay reliable. Keep learning.
