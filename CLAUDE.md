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

## Conventions (added Stage 5)

- **Scheduler**: GitHub Actions (`.github/workflows/morning-briefing.yml`), not Claude's own hosted cloud routines (`RemoteTrigger`). That option was ruled out — its cloud environments have no documented way to hold file-based secrets like our Google `credentials.json`/`token.json` (env vars there are explicitly readable by anyone with environment access; "network secrets" only inject HTTP bearer tokens into requests, not files). GitHub's encrypted repo secrets are built for exactly this.
- **Headless Claude billing**: authenticated via `CLAUDE_CODE_OAUTH_TOKEN` (generated locally with `claude setup-token`, tied to the user's own Pro subscription), never an `ANTHROPIC_API_KEY`. This keeps the automation's Claude usage bounded by the Pro plan's existing limits instead of uncapped pay-per-token billing.
- **Google secrets in CI**: `credentials.json`/`token.json`'s *current* contents are stored as GitHub repo secrets and written to disk at job start. Works because a Desktop-app OAuth client's refresh token doesn't rotate on use — no need to persist an updated token back out after each run.
- **The automation's entry point is `tools/send_morning_briefing.py`, not `tools/morning_briefing.py`.** It fetches calendar+Gmail itself, decides whether there's anything to style, and — when there is — hands the already-fetched raw data directly to headless Claude in the prompt rather than asking Claude to fetch it. Two reasons: Claude's own Bash invocation kept not matching `--allowedTools` patterns reliably and getting silently denied, and this step processes real email content, so giving it no Bash tool at all (only `Read` on the skill file, via both `--tools Read` and `--allowedTools`) closes a real prompt-injection attack surface — worst case from a malicious email is bad text, never an executed command. Sends the result via `tools/send_telegram.py`.
- **Location is inferred from the calendar, not hardcoded.** `resolve_todays_location()` asks a *separate*, minimal headless Claude call (`--tools ""` — no tools whatsoever, not even Read) whether today's events imply travel to a specific city, covering both a structured calendar `location` field and informal titles like "Meeting in Paris" or "Train to Zurich." A returned city name is geocoded via `tools/resolve_location.py` (Open-Meteo's free geocoding API, same zero-cost pattern as the weather call); any failure at any step falls back to the configured home `LOCATION_NAME`/`LAT`/`LON` rather than failing the briefing — this is an enhancement on top of otherwise-complete data, not core data itself.
- **Cross-platform Python invocation**: since CI (Linux, no venv) and local dev (Windows, `.venv/`) differ, `.claude/commands/briefing.md` picks the right Python path adaptively (venv if present, else plain `python`) rather than hardcoding one.
- **Invoking `claude` from Python on Windows — two real gotchas**, both fixed in `tools/send_morning_briefing.py`'s `run_headless_claude()`:
  - Resolve the executable with `shutil.which("claude")`, not a bare `"claude"` string — the npm global install is a `.cmd` wrapper on Windows, and `subprocess.run`'s list-argument form doesn't do the shell's PATHEXT resolution needed to find it (`FileNotFoundError` even though typing `claude` directly works fine).
  - Pass the prompt via **stdin** (`input=prompt`), not as a CLI positional argument — a multi-line prompt-as-argument got silently truncated at the first newline on Windows, since invoking a `.cmd` wrapper routes through `cmd.exe`'s own command-line parsing. Stdin input sidesteps this and works identically on both platforms.
- **Control via Telegram** (`tools/manage_pause_state.py`) — standardized, one canonical form per command:
  - `stop` / `pause` — pause; `continue` / `resume` / `start` — resume.
  - `timezone <city name>` — e.g. `timezone Paris`. Plain city name only, never an IANA string — geocoded via `tools/resolve_location.py`'s `geocode()` (a plain REST call, **not Claude**) to resolve the IANA timezone automatically. `timezone reset` clears it back to automatic.
  - `time HH:MM` — 24h format, e.g. `time 06:30`. Sets the daily send time. `time reset` restores the default (`07:00`).
  - `help` (also `--help`, `-h`, `/help`, `commands`, `?`) — replies with a summary of all commands.
  - Confirmations are sent on the next hourly poll, same mechanism throughout.
- **No fixed daily cron time — hourly polling, self-gated.** The workflow runs every hour (`0 * * * *`); `tools/manage_pause_state.py` is the **only** step that runs unconditionally every time, and it never invokes headless Claude (processing commands + the time decision are both free). It decides **SEND** or **SKIP** by checking: not paused, current local hour in the *effective* timezone (`timezone_override` if set, else `HOME_TIMEZONE`) matches `send_time`'s hour (via stdlib `zoneinfo` — DST-correct automatically, no manual UTC math or cron rewriting), and not already sent today (local date, via `last_sent_date`). All the expensive steps (Node/Claude CLI install, Google credentials, the actual send) are gated behind `if: steps.check_pause.outputs.status == 'SEND'`, so a typical hour costs nothing beyond one Telegram API call. `tools/send_morning_briefing.py` now also takes the state file path as an argument, to record `last_sent_date` after a confirmed successful send (not before — a failure partway through shouldn't falsely mark the day as handled).
  - `zoneinfo` needs the `tzdata` PyPI package explicitly on Windows (no system IANA database, unlike Linux) — in `requirements.txt`.
  - State (`{"paused", "last_update_id", "last_sent_date", "timezone_override", "send_time"}`) lives on the same **dedicated orphan branch**, `briefing-state`, with no shared history with `master` — the main job never checks it out; separate workflow steps clone it into a subdirectory and commit/push there only if something actually changed. `master`'s commit log is never touched by the automation.
  - Test locally against a throwaway file: `python tools/manage_pause_state.py /tmp/test_state.json` (uses local `.env`'s `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID`/`HOME_TIMEZONE`).
  - Confirmed cost: ~275 min/month of GitHub's 2,000 free (private repo) at hourly polling — exhausting the quota stops workflow runs rather than billing, by default (worth the user verifying that toggle in their own billing settings).
- **Daily news section** (`tools/fetch_news.py`, standalone feature tracked separately from the Stage 5 commit): 5 free, no-API-key RSS feeds — World/Europe/Spain/Switzerland (regions) plus Financial (a cross-cutting markets topic, not a 5th region). Each feed's failure is independently non-fatal — one dead/slow feed just skips that category, never fails the briefing (same philosophy as the travel-location inference). Fetched fresh on every actual send (not on the cheap hourly polls) and handed to the same tool-less styled-rendering call as more plain-text data — no new tool access granted.
  - **This removed the "genuinely zero-Claude quiet day" case** — `compose_styled_briefing()` now always runs, even with an empty calendar/inbox, since judging news significance needs Claude's judgment regardless. Accepted trade-off, not an oversight.
  - The news block is the only one of the four that can be fully omitted (no placeholder) — see `.claude/skills/briefing-style/SKILL.md` for the significance/brevity/headline-skepticism rules Claude applies.

## Conventions (added Stage 5, reliability follow-up)

- **GitHub's own `schedule:` cron trigger is unreliable for this repo** — confirmed by direct observation: across several hours, including a dedicated 5-minute-interval test, exactly one scheduled run actually fired, versus many manual ones. GitHub documents `schedule` as best-effort, and low-activity free/private repos appear to be deprioritized further, sometimes for hours. The hourly `schedule:` entry in `.github/workflows/morning-briefing.yml` is kept as a free backup, but is not treated as the primary trigger.
- **Primary trigger: an external cron service pinging `workflow_dispatch` directly** via GitHub's REST API, every 10-15 minutes. Dispatched runs start immediately and reliably (unlike `schedule`), since they're a direct API call rather than GitHub's internal scheduler.
- **`force` input decouples "manually triggered" from "force send"**: `workflow_dispatch` takes a `force` boolean input (default `false`). `FORCE_SEND` is only `1` when that input is explicitly `true`. A plain dispatch (what the external pinger sends) goes through the same `is_time_to_send()` gate a real scheduled run would — required because the pinger fires every few minutes, not once an hour; without this, every ping would force-send immediately.
- **`is_time_to_send()` is "at or past send_time", not an exact hour match** — a delayed trigger (from either `schedule` or the external pinger) still catches up and sends, rather than permanently missing a day because it landed a few minutes outside a single matching hour.
- **One-time setup (done by the user — creating credentials/third-party accounts is outside what Claude does on someone's behalf)**:
  1. GitHub → Settings → Developer settings → Fine-grained tokens → Generate new token. Repository access: this repo only. Permissions: Actions → Read and write.
  2. Sign up for a free external cron-ping service (e.g. cron-job.org).
  3. Create a job there: `POST https://api.github.com/repos/pelayogmj/morning-briefing-bot/actions/workflows/morning-briefing.yml/dispatches`, headers `Authorization: Bearer <token>`, `Accept: application/vnd.github+json`, `X-GitHub-Api-Version: 2022-11-28`, body `{"ref": "master"}`. Schedule every 10-15 minutes.
  4. Leave `force` unset (or `false`) in that body, so pings go through the normal gate instead of force-sending every time.

## Conventions (added: Tasks section)

- **✅ Tasks block** (`tools/get_tasks.py`), inserted between Inbox and News in both briefing paths (`tools/send_morning_briefing.py` and the interactive `/briefing`'s `tools/morning_briefing.py` — News was also backfilled into the latter at the same time, since it had never been added there). Unlike News, Tasks is a **required** block — it always renders one of three fixed cases and is never fully omitted; its fetch failure is treated as a hard failure (`sys.exit(1)`), same tier as Calendar/Gmail/Weather, not News's soft-fail style.
- **List matching, not a hardcoded name**: `is_todo_list_title()` normalizes a Google Tasks list's title (lowercase, strip spaces/hyphens) and matches if it contains `"todo"` — catches "TODOs", "To-Do List", "to do", etc. without depending on one exact literal name. Tasks from every matching list are merged; zero matches falls through naturally to the "all clear" case (not an error).
- **Three rendering cases, in order** (`format_tasks_summary()`): (1) any task due today or overdue → bullet list, overdue ones explicitly labeled with their original due date; (2) else, any dateless open task → one line reporting the count; (3) else → a fixed "to-do list is clear" line. A task with a **future** due date counts toward neither case — it's not today's business yet.
- **Changing `google_auth.py`'s shared `SCOPES` list requires re-consenting, not just redeploying.** `token.json` is scoped to whatever was in `SCOPES` when it was generated — adding a new scope (here, `tasks.readonly`) doesn't retroactively apply to the cached token; `get_credentials()` has no "upgrade scopes" path, only full re-consent. After any `SCOPES` change:
  1. Enable the newly-needed API in Google Cloud Console (same place Calendar/Gmail were enabled).
  2. Delete the local `token.json`.
  3. Run any Google-auth tool locally once (e.g. `tools/get_tasks.py`) to re-trigger interactive OAuth consent and regenerate `token.json` against the full new scope list.
  4. Update the `GOOGLE_TOKEN_JSON` GitHub repo secret with the regenerated file's contents (see Stage 5's "Google secrets in CI") — CI keeps using whatever was last stored there, so skipping this step means local runs work while the scheduled briefing keeps failing on the old, insufficient scope.

## Conventions (added: weather retry/soft-fail fix)

- **`fetch_forecast`'s retry only ever caught `requests.exceptions.ConnectionError`** — a real bug, not a theoretical gap: `requests.exceptions.ReadTimeout` (seen in CI as "Read timed out") is a `Timeout` subclass, not a `ConnectionError` subclass, so a timeout skipped the retry loop entirely and failed on the first attempt. Fixed by catching `(requests.exceptions.ConnectionError, requests.exceptions.Timeout)` together — both are the same kind of "transient upstream blip," which is exactly what this retry exists for.
- **Weather is now soft-fail, like News** — in both `tools/send_morning_briefing.py` and `tools/morning_briefing.py`, a weather fetch failure (even after `fetch_forecast`'s own retries are exhausted) no longer aborts the whole briefing via `sys.exit(1)`. It falls back to a plain `"Weather data is currently unavailable."` line and continues — Calendar/Gmail/Tasks remain hard-fail (still core, still required), but a dead weather API alone shouldn't block an otherwise-complete briefing from sending.
- **Research into the recurring timeouts pointed at Open-Meteo itself, not our code**: GitHub-hosted runners share IP ranges across unrelated jobs worldwide, and Open-Meteo's free tier rate-limits/throttles per source IP — a known, documented pain point (see [open-meteo/open-meteo#853](https://github.com/open-meteo/open-meteo/discussions/853)), consistent with our timeouts correlating with no change in our own (very low) call volume.
- **Added a real second weather source as a fallback**: `tools/get_weather.py`'s `fetch_weather_line()` is now the single entry point both orchestrators call — it tries Open-Meteo first, and only if that fails even after retries, tries MET Norway's free Locationforecast API (`fetch_fallback_forecast`/`parse_fallback_today`/`format_fallback_summary`) before giving up to the plain "unavailable" line. MET Norway needs no API key but its Terms of Service require a descriptive `User-Agent` (app name + contact/repo link) — a generic or missing one gets throttled or blocked.
  - Confirmed live for Zurich (non-Nordic): MET Norway's `complete.json` has `air_temperature_max`/`_min` under each hourly entry's `next_6_hours.details`, but **no `probability_of_precipitation` field for this location** (that field exists in their schema but is Nordic-model-only in practice). The fallback therefore reports a plain "rain is possible"/"no rain is expected" from `precipitation_amount` presence, not a fabricated percentage — honest about having less detail than the primary source, never inventing numbers it doesn't have.

## Bottom Line

You sit between what I want (workflows) and what actually gets done (tools). Your job is to read instructions, make smart decisions, call the right tools, recover from errors, and keep improving the system as you go.

Stay pragmatic. Stay reliable. Keep learning.
