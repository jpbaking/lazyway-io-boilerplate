# Goal Ledger — agent-guided install

You are an AI coding agent installing Goal Ledger. Follow these steps
exactly. This procedure is merge-aware — it never blindly overwrites files
the user already owns — and it is the only install path; there are no
install scripts.

Goal Ledger is a **user-global** toolkit: its skills and rule install once
per user into each harness's global discovery paths. Nothing is installed
into projects — the per-project footprint is the runtime `.goal-ledger/`
directory the skills create during use, which is a **committed, git-tracked
execution record** (never gitignore it). Project-level adapter install is an
explicit opt-in (see the last section).

Source repository: `https://github.com/jpbaking/goal-ledger`. If the user
named a fork or tag, substitute it below.

## 1. Acquire the sources

Obtain the sources in a temporary directory (never inside a project):

- `git clone --depth 1 https://github.com/jpbaking/goal-ledger <tmp>/goal-ledger`
  (add `--branch <tag>` for a pinned tag), or
- download and extract `https://github.com/jpbaking/goal-ledger/archive/refs/heads/main.zip`, or
- `gh repo clone jpbaking/goal-ledger <tmp>/goal-ledger`.

Copy from this staging directory below; delete it when done.

## 2. Survey before writing

1. If the current project has `.tmp-agent-scratch/MASTER-PLAN.md` with a plan
   status other than `done`, STOP and report it — an unfinished legacy plan
   must be resumed, finished, abandoned, or migrated before installing.
2. Ask (or infer from the user's request) which harnesses to support: Codex,
   Claude Code, Antigravity, Cline, Gemini CLI. Default: all.
3. Check for same-named `goal-ledger*` or legacy `master-plan*` artifacts in
   the global skill directories listed below and, if you are inside a
   project, under its `.agents/`, `.claude/`, `.cline/`, `.clinerules/`, and
   `.claude/commands/`. Report collisions; never delete unrelated or legacy
   files. A project-level skill with the same name can shadow or duplicate
   the global copy.

## 3. Install the skills (byte-identical copies)

For each skill `goal-ledger`, `goal-ledger-execute`, `goal-ledger-resume`,
`goal-ledger-status`, `goal-ledger-abandon`, copy the full directory from
`skills/shared/<skill>/`
(at minimum `SKILL.md`; `goal-ledger` also bundles
`scripts/validate_goal_ledger.py`) to each selected harness's global skills
directory:

| Harness | Destination |
| --- | --- |
| Codex (and Gemini CLI) | `~/.agents/skills/<skill>/` |
| Claude Code | `~/.claude/skills/<skill>/` |
| Antigravity | `~/.gemini/config/skills/<skill>/` |
| Cline | `~/.cline/skills/<skill>/` |

Cursor needs **no separate copy**: it natively discovers `~/.agents/skills/`
(and `~/.claude/skills/` / `~/.codex/skills/` as compatibility paths). Do
not install to `~/.cursor/skills/` — that would create a duplicate.

Replace whole same-named skill directories so retired bundled resources
cannot linger. Verify each skill's frontmatter `name` matches its directory,
and that all copies are byte-identical across harnesses.

## 4. Install the rule

The rule self-gates: its resume check and start triggers key off
`.goal-ledger/` in the current project, so it is safe to load globally.

1. Copy `rules/shared/goal-ledger.md` to `~/.agents/rules/goal-ledger.md`
   (neutral shared location) and `~/.gemini/config/rules/goal-ledger.md`
   (auto-loaded by Antigravity).
2. Cline: copy it to `~/Cline/Rules/goal-ledger.md` on Linux, or
   `~/Documents/Cline/Rules/goal-ledger.md` on macOS/Windows (if both exist,
   use the populated one).
3. Codex, Claude Code, and Gemini CLI load global guidance from user-owned
   files — merge, never overwrite. Append this marker-guarded block once
   (skip if the marker is present) to `~/.codex/AGENTS.md`,
   `~/.claude/CLAUDE.md`, and — when Gemini CLI is selected —
   `~/.gemini/GEMINI.md` (create any that are missing):

   ```markdown
   <!-- goal-ledger:global-rule -->
   Read and follow `~/.agents/rules/goal-ledger.md`. In particular: at the
   start of every primary-session task, if the project contains
   `.goal-ledger/GOAL.md` with a `Goal status:` other than `completed` or
   `abandoned`, use the `goal-ledger-resume` skill before unrelated work —
   unless you were handed a specific `phase-NNNN` to run, in which case use
   `goal-ledger-execute` for that phase only.
   <!-- /goal-ledger:global-rule -->
   ```

Cursor has no file-based global rules (User Rules are app settings). If
the user works in Cursor, print the pointer block above and ask them to
paste it into Cursor Settings → Rules once.

Never write to `~/.codex/rules` or any `.codex/rules` — that path holds
command-execution policy, not guidance.

## 5. Validate and report

1. Verify each installed skill directory is byte-identical across the
   selected harness destinations and to the canonical source.
2. Verify every selected harness reaches the rule through exactly one path
   (auto-loaded global rule or one merged pointer block — not both for the
   same harness).
3. Remove the temporary staging directory.
4. Report every file created, changed, or intentionally left alone, plus
   collisions and warnings from step 2. Note the install is per-user and
   per-machine.
5. Tell the user: ask their strongest model to use the `goal-ledger` skill
   for multi-phase work; it plans, delegates phases, and reviews at Gate D.
   Cheaper models run individual phases via `goal-ledger-execute`
   (`goal-ledger-resume` for recovery/handoff, `goal-ledger-status` for a
   read-only report, `goal-ledger-abandon` to stop while preserving
   history). Remind them `.goal-ledger/` directories are committed project
   data — never gitignored.

## Project-level adapter install (opt-in only)

Only on explicit user request: copy the five skill directories to the
project's `.agents/skills/` and `.claude/skills/`, and the rule to
`.agents/rules/goal-ledger.md` and `.claude/rules/goal-ledger.md`
(byte-identical). Claude Code needs no `CLAUDE.md` bridge — it
auto-discovers `.claude/rules/`. Whether the team commits or gitignores the
adapters is the project's own policy — never touch the project's
`.gitignore` yourself. Never gitignore `.goal-ledger/`; if existing ignore
rules hide the adapters from a harness, report the exact pattern instead of
changing it.
