# Learnings

## Stage 1: The plain version (weather briefing)

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
