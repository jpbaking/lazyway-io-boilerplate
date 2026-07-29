---
name: goal-ledger-abandon
description: >-
  Mark the current Goal Ledger abandoned while preserving its files and Git
  history for recovery and audit. Use only when the user explicitly asks to
  abandon, cancel, or scrap the active goal. Never delete .goal-ledger, reset
  commits, discard code, delete a branch, or treat a blocked goal as abandoned
  without explicit confirmation.
---

# Goal Ledger — abandon without erasing history

Abandonment is a durable terminal state, not deletion. Preserve the ledger and work so the decision can be understood or reversed later.

Abandonment is **planner-only**. If you were handed a single phase to execute, you cannot abandon the goal: set that phase to `needs-human — reason:` and stop.

## 1. Load and summarize

Read sections 1–4 of the sibling `goal-ledger` skill. If there is no ledger, say so and stop. If status is already `completed` or `abandoned`, report it and stop.

Show the Goal ID, Outcome, strategy and work branch, phase counts, blockers, matching goal commits, and dirty worktree state. Explain that abandonment will keep the ledger, commits, and code changes.

If a phase is `ongoing`, an executor may still be holding it. Say so and confirm that work has actually stopped before abandoning.

## 2. Confirm abandonment

Ask explicitly: "Mark this goal abandoned while preserving its ledger and work?" Anything short of a clear yes changes nothing.

On confirmation:

1. Set Goal status `abandoned`.
2. Update Handoff: current position `abandoned`, next action `none`, and blockers with the user's reason when provided.
3. Append an abandonment log entry. Do not change phase statuses merely to make them terminal.
4. Run the validator bundled with the sibling `goal-ledger` skill as `scripts/validate_goal_ledger.py --root <project root>`. Repair ledger-format errors before preserving the state; warnings do not prevent abandonment. If Python 3 is unavailable, check the format manually.

## 3. Preserve Git state

When `Repository: yes`:

- If Git preparation never completed (`Strategy: none`, missing baseline, or no approval commit), do not create or switch branches merely to abandon a draft. Save the abandoned ledger locally; commit it only if the user separately asks to record it on the current branch.
- After Git preparation, if the worktree contains partial goal work, ask separately whether to checkpoint those goal-owned changes in the abandonment commit. Default No. Never stage unrelated files.
- After Git preparation, whether or not partial code is included, stage `.goal-ledger/GOAL.md` and create `goal-ledger(abandon): <title>` with the matching Goal ID trailer. If partial work is not included, leave it untouched and report it as uncommitted.
- Never reset, revert, delete the work branch, or rewrite history.
- For an isolated branch with a clean tree, offer to switch back to `Starting branch`; require explicit permission and keep the goal branch intact.
- If partial work remains dirty because checkpointing was declined, stay on the goal branch. Offer a separately authorized checkpoint or recoverable stash, or leave it in place; never carry it onto the starting branch or discard it automatically.
- On `current-branch`, remain on that branch and warn that goal commits are part of its history.

Without Git, save the ledger state and report any remaining files.

## 4. Report

State what was marked abandoned, which files or partial changes were committed, what remains uncommitted, the current branch, and how to recover the record later. Do not offer deletion as routine cleanup.
