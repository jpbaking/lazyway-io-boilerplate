---
name: goal-ledger-resume
description: >-
  Resume and recover an unfinished Goal Ledger after interruption, a crash,
  context compaction, or hand-off from another agent or model tier. Reconcile
  .goal-ledger files with the recorded branch, immutable baseline, Goal-ID
  commit trail, dirty worktree, and committed phase-start markers; verify what
  an executor left behind, repair bookkeeping, and continue execution. Use when
  .goal-ledger/GOAL.md is unfinished, the user says resume or continue the goal,
  an executor stopped mid-phase, or ledger and Git state may disagree.
---

# Goal Ledger — resume and recover

Treat the ledger and Git as evidence left by another agent — possibly a weaker one, possibly mid-sentence. Establish what is verified, repair bookkeeping without discarding work, and continue from the first safe action.

## 1. Establish your role

- If you were handed a specific phase to run, use the
  `goal-ledger-execute` skill instead.
- If you are an ordinary helper subagent working from a delegated prompt, ignore the ledger and this skill and continue only the task you were given. An unfinished ledger is not a blocker for that task and is not worth reporting unless the prompt asks for ledger work.
- Otherwise you are resuming as the **planner**: you own the goal, the plan, `Goal status`, Git, and Gate D.

Read sections 1–4 of the sibling `goal-ledger` skill. If `.goal-ledger/GOAL.md` is missing, say there is no ledger to resume. If status is `completed` or `abandoned`, report that and stop.

## 2. Decide whether this request resumes the goal

- The user asks to resume, or the request matches the recorded Outcome: resume without another intent question.
- The ledger is `blocked-on-human` and the user answers its blockers: record the answers into the affected phase's `## Context` so a re-delegated executor can see them, return affected items to `[todo]`, and continue.
- Status `drafting`: return to Gate A. Status `approved`: if strategy, branch, baseline, or approval commit is missing or inconsistent, return to Gate B; otherwise return to Gate C.
- Status `in-review`: Gate D was started and not finished. Re-run it from the top rather than trusting a partial `## Review`.
- Status `awaiting-acceptance`: report the result and ask for acceptance; do not resume execution.
- An unrelated request: report the unfinished goal and ask whether to resume
  it or use the `goal-ledger-abandon` skill. Never overwrite it silently.

## 3. Reconcile Git

Skip Git steps when `Repository: no`.

1. Verify the current branch equals `Work branch`. If not, do not switch with a dirty tree. Report both branches and ask before switching.
2. Verify the immutable baseline exists and is an ancestor of `HEAD`. If not, stop with the exact inconsistency.
3. Inspect `git log <baseline>..HEAD`, including commit trailers. Classify matching Goal-ID commits, foreign commits, merge commits, and phase begin/close pairs. Record foreign history in Handoff; it may prohibit squashing but does not justify deleting work.
4. Compare locally known starting/work upstream refs with their recorded Gate B SHAs. Record advances, rewinds, divergence, or goal-commit publication in Handoff. On `current-branch`, any upstream movement prohibits automated squash.
5. Inspect the worktree. A phase-begin commit followed by a clean tree means phase work did not start. A dirty tree means work may have stopped mid-phase; inspect the diff and do not discard it.
6. A completed phase without a matching close commit is unverified until its `## Verify` passes. A close commit with stale ledger status may be reconciled after its check passes.

## 4. Verify and repair state

- **Trust nothing an executor recorded.** A `[done]` sub-task is a claim; its `## Evidence` line is a claim. Re-run the phase's `## Verify` and check the sub-task's "done when" yourself. If it passes, keep it done and log `verified on resume`; otherwise return it to `[todo]` and redo it deliberately.
- Read `git diff` for any executor's close commit. Changes outside that phase's `Scope: In` are the most common delegation failure — investigate them before continuing, and log what you found.
- If a phase is `ongoing` with a dirty tree and no close commit, an executor was interrupted. Keep the begin marker and its partial work, re-verify what is provable, and either finish the phase yourself or re-delegate it with the unproven sub-tasks back at `[todo]`.
- If a phase is `needs-human`, its reason is the question to answer. Resolve it, record the answer in that phase's `## Context`, and reopen the affected sub-tasks.
- Repair multiple ongoing items, `GOAL.md`/phase mismatches, missing reason suffixes, stale `Last completed phase`, and stale Handoff fields including `Next role`. The phase file wins status disagreements.
- If an executor edited planner-owned fields — the phase list, `Goal status`, Git fields, `## Review`, or a phase's plan sections — restore them from Git history and log the violation. Do not silently adopt the change.
- Append a resume event to `GOAL.md` and identify the evidence used.
- Run the validator bundled with the sibling `goal-ledger` skill as `scripts/validate_goal_ledger.py --root <project root>`. Repair ledger errors before continuing; record Git warnings in Handoff. If Python 3 is unavailable, check the section 3 invariants and Git contract manually.

## 5. Continue

Re-enter section 7 of the `goal-ledger` skill, or Gate D (section 9) if every phase is already terminal. Preserve its delegation rules, commit identity, phase checks, stop conditions, review gate, acceptance, and squash safeguards.

Before re-delegating any phase, re-read its file as an executor would. Interruption is usually evidence that the phase was under-specified, too large, or ambiguous — fix the phase file first, and log why.
