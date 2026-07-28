---
name: goal-ledger-status
description: >-
  Produce a strictly read-only status and handoff report for the current Goal
  Ledger, including phase progress, owners, next role, next action, blockers,
  review-gate state, Git strategy, matching Goal-ID commits, branch or baseline
  inconsistencies, foreign commits, and dirty crash evidence. Use when the user
  asks for goal status, where the work stands, what remains, whether a phase is
  ready to delegate, or an inter-agent handoff summary. Never modify files,
  commits, branches, or statuses.
---

# Goal Ledger — status and handoff report

This skill is strictly read-only: no status changes, log entries, commits, repairs, branch switches, or cleanup.

Read sections 1–4 of the sibling `goal-ledger` skill. If `.goal-ledger/GOAL.md` is absent, say there is no Goal Ledger and stop.

Read `GOAL.md` and every phase file. When `Repository: yes`, read the current branch, worktree status, and `git log <baseline>..HEAD` with trailers. Report:

Run the validator bundled with the sibling `goal-ledger` skill in read-only mode as `scripts/validate_goal_ledger.py --root <project root>`. Include its errors and warnings in the report. If Python 3 is unavailable, perform the same read-only checks manually.

```text
Goal: <title> — <goal status>
Goal ID: <id>
Outcome: <outcome>
Mode: <solo | delegated>; planner <tier>; executor <tier>
Strategy: <strategy>; start <starting branch>; work <work branch>
Baseline: <short SHA>
Upstreams at start: start <value>; work <value>         (omit without Git)
Phases: <X> done, <Y> skipped, <Z> needs-human, <W> todo, <V> ongoing
Per phase:
- phase-NNNN <status> — <title> (owner: <owner>, <a>/<b> sub-tasks done)
Handoff: <current position>; next <next role> — <next action>
Review: reviewed by <value>; verification <value>; findings <value>
Goal commits: <N>; tree <clean | DIRTY — possible interrupted work>   (omit without Git)
Needs you:
- <exact blocker>                                      (omit if none)
Warnings:
- <branch mismatch / baseline problem / upstream movement / foreign or merge commit / phase state mismatch / begin without close / published history / done phase with no evidence>   (omit if none)
```

When the next action is a delegation, also state which phase is ready and whether its file is executor-ready: exact paths in `Scope: In`, a runnable `## Verify`, and no sub-task that still requires a decision. Report gaps as warnings — do not fix them here.

End with one recommendation: delegate the next phase, resume with `goal-ledger-resume`, run Gate D, review for acceptance, keep the completed record, or use `goal-ledger-abandon` if the user explicitly wants to stop.
