# Learnings

## Stage 1: The plain version (weather briefing)

*Draft reflection — edit freely, this is your call, not mine.*

- **What I learned**: TODO
- **What confused me**: TODO
- **What I'd do differently**: TODO

## Stage 2: Calendar + Gmail (MCP and direct API)

### MCP vs. direct API — the factual answer

MCP lets Claude call a tool *while a live, human-driven Claude Code session is open* — the MCP server brokers the call through that running session. It has no trigger of its own; nothing wakes it up on a schedule. A script meant to run unattended (e.g. the 7am morning briefing, with no one watching) has no session for an MCP server to attach to, so it can't use MCP at all. It needs its own credentials and calls the provider's API directly instead — which is exactly what `tools/google_auth.py` + `tools/get_calendar.py` + `tools/get_gmail.py` do, independently of any MCP server.

The two paths are complementary, not competing: MCP is for interactive, ad hoc use (e.g. asking Claude to check today's calendar mid-conversation); direct API access is for scheduled/automated use (the eventual cron job).

Secondary point — **MCP scope**: `claude mcp add --scope project` writes the server config to `.mcp.json` in the repo (shared with anyone who clones it); `--scope user` stores it outside the repo, private to one person across all their projects.

### Personal reflection

*Draft reflection — edit freely, this is your call, not mine.*

- **What I learned**: TODO
- **What confused me**: TODO
- **What I'd do differently**: TODO

## Stage 3: Skills and custom commands

### What "skills" demonstrated here — the factual answer

A skill (`.claude/skills/briefing-style/SKILL.md`) is the same mechanism as `CLAUDE.md` — persistent instructions Claude reads — just scoped to one reusable, swappable file instead of baked into a script or the whole project's instructions. The custom command (`.claude/commands/briefing.md`, run as `/briefing`) is what actually *does* something: it runs the deterministic `tools/` scripts, then explicitly loads the skill to decide how to present the result. Editing `SKILL.md` alone (no code touched) visibly changed the briefing's format from a flowing paragraph to a fixed three-line structure — proving skills only affect *Claude's* own output, never a standalone script's, since a script never reads skill files at all.

### Personal reflection

*Draft reflection — edit freely, this is your call, not mine.*

- **What I learned**: TODO
- **What confused me**: TODO
- **What I'd do differently**: TODO

---

# Claude Code Feature Tour

A quick reference for Claude Code's main extensibility features and when to reach for each one.

## CLAUDE.md
A markdown file checked into the repo (project root, or nested in subdirectories) that gives Claude persistent, repo-specific instructions — build/test/lint commands, architecture notes, conventions, things not to do. It's read automatically at the start of every session in that directory, so it never needs to be re-explained.

**Use it when:** you want every future session in this repo to already know the same context — how to run tests, the directory layout, project-specific rules — without repeating yourself each time. This project's own [CLAUDE.md](CLAUDE.md) is a good example: it defines the whole WAT (Workflows, Agents, Tools) convention for how work here should be organized.

## Skills
Packaged, reusable sets of instructions (and sometimes scripts) for a specific kind of task — e.g. a checklist for code review, a house style for documents, a repo-specific deploy procedure. They show up as `/skill-name` or trigger automatically when the task matches their description.

**Use it when:** you have a recurring, well-defined workflow (not a one-off task) that you want to standardize — so it's performed the same way every time instead of improvised fresh each time.

## Subagents
Separate agent instances you can delegate a task to, either a fresh one (no memory of this conversation, briefed from scratch) or a "fork" (inherits full context, runs in the background). They keep large/noisy intermediate work (research output, exploratory file reads) out of the main conversation's context.

**Use it when:** a task is self-contained enough to brief clearly, and its raw tool output isn't something you need to keep around — e.g. "search the codebase for all usages of X and summarize," or running several independent investigations in parallel.

## Hooks
Shell commands configured in `settings.json` that fire automatically on specific events — before/after a tool call, when a session starts/stops, etc. Unlike instructions to the model, hooks are deterministic: they always run, enforced by the harness, not by the model choosing to comply.

**Use it when:** you need something to happen reliably every time, with no chance of being skipped or forgotten — e.g. auto-formatting a file after every edit, blocking commits that touch a protected path, logging every bash command run.

## MCP (Model Context Protocol)
An open protocol for connecting Claude Code to external tools and data sources — databases, SaaS APIs, internal services — exposed as MCP servers that register new tools in the session (e.g. the Google Drive, Gmail, or Calendar tools visible in this environment).

**Use it when:** you need Claude to interact with a system that isn't just local files/shell — a third-party API, an internal company tool, a specialized data source — and a dedicated integration exists or can be written for it.

## Plugins
Installable bundles that package up slash commands, skills, hooks, and/or subagents together, usually built around a team's specific process (e.g. a deploy plugin, a plugin wrapping an org's code-review playbook). They extend Claude Code's capabilities without you having to assemble the pieces yourself.

**Use it when:** your org already has a packaged workflow (deploy steps, a review process, a data pipeline) that someone has turned into a plugin — install it instead of rebuilding the equivalent skill/hook/command set from scratch.

## Headless mode
Running Claude Code non-interactively from the command line (`claude -p "prompt"` and similar), suitable for scripts, CI pipelines, or automation, rather than the interactive chat UI.

**Use it when:** you want to invoke Claude Code as a step in an automated pipeline — e.g. a CI job that asks it to review a diff, or a script that batch-processes files — without a human driving the conversation.
