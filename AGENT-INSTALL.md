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
2. Confirm which harnesses to support: Antigravity CLI, Codex, Claude Code,
   Cline, and Pi. Do not infer consent from detected configuration
   directories.
3. Check for same-named `goal-ledger*` or legacy `master-plan*` artifacts in
   the global skill directories listed below and, if you are inside a
   project, under its `.agents/`, `.claude/`, `.cline/`, `.clinerules/`, and
   `.pi/`, plus legacy `.claude/commands/`. Report collisions; never delete
   unrelated or legacy files. A project-level skill with the same name can
   shadow or duplicate the global copy. Also check for this toolkit's legacy
   rule copies under `~/.gemini/config/rules/` and the Cline Rules
   directories.

## 3. Install the skills (byte-identical copies)

For each skill `goal-ledger`, `goal-ledger-execute`, `goal-ledger-resume`,
`goal-ledger-status`, `goal-ledger-abandon`, copy the full directory from
`.agents/skills/<skill>/`
(at minimum `SKILL.md`; `goal-ledger` also bundles
`scripts/validate_goal_ledger.py`) to each selected harness's global skills
directory:

| Harness | Destination |
| --- | --- |
| Antigravity CLI (`agy`) | `~/.gemini/antigravity-cli/skills/<skill>/` |
| Codex | `~/.agents/skills/<skill>/` |
| Claude Code | `~/.claude/skills/<skill>/` |
| Cline | `~/.cline/skills/<skill>/` |
| Pi | `~/.agents/skills/<skill>/` |

Codex and Pi share one physical `~/.agents/skills/` copy. If both are
selected, install it once.

Replace whole same-named skill directories so retired bundled resources
cannot linger. Verify each skill's frontmatter `name` matches its directory,
and that all copies are byte-identical across harnesses.

## 4. Install the rule

The rule self-gates: its resume check and start triggers key off
`.goal-ledger/` in the current project, so it is safe to load globally.

1. Copy `rules/shared/goal-ledger.md` to
   `~/.agents/rules/goal-ledger.md`.
2. For each selected harness, merge the marker-guarded block below into its
   user-owned global instruction file:

   | Harness | Instruction file |
   | --- | --- |
   | Antigravity CLI (`agy`) | `~/.gemini/GEMINI.md` |
   | Codex | `~/.codex/AGENTS.md` |
   | Claude Code | `~/.claude/CLAUDE.md` |
   | Cline | `~/.agents/AGENTS.md` |
   | Pi | `~/.pi/agent/AGENTS.md` |

   If the marker exists, replace that block with the current text. Otherwise
   append it once. Create a missing file, but never overwrite, reorder, or
   delete unrelated content.

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

Never write to `~/.codex/rules` or any `.codex/rules` — that path holds
command-execution policy, not guidance.

If a legacy same-tool rule exists in `~/.gemini/config/rules/` or a Cline
Rules directory, report it and ask before removing it. Do not leave both
routes active.

## 5. Validate and report

1. Verify each installed skill directory is byte-identical across the
   selected harness destinations and to the canonical source.
2. Verify every selected harness reaches the shared rule through exactly one
   marker-guarded pointer block.
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

Only on explicit user request: copy the five authoritative skill directories
to `.agents/skills/`, mirror them byte-identically to `.claude/skills/`, and
copy the five thin shims from `.clinerules/workflows/`. Merge the self-gating
rule body from `rules/shared/goal-ledger.md` once into the project's
`AGENTS.md`; ensure `CLAUDE.md` imports `AGENTS.md` exactly once. Do not
duplicate the rule in host rule directories.

Commit the root files, both skill trees, and Cline shims together. Never touch
the project's `.gitignore`, and never gitignore `.goal-ledger/`; report an
exact ignore pattern if it hides an adapter.
