---
name: goal-ledger-execute
description: >-
  Execute exactly one assigned phase of an existing Goal Ledger and stop. Use
  when you were handed a phase ID to run (a prompt naming goal-ledger-execute
  and a phase-NNNN), when acting as the executor for a planner-tier agent, or
  when running delegated grunt work against .goal-ledger/phase-NNNN.md. Follow
  the phase file exactly, verify with its own commands, commit the phase, and
  escalate instead of improvising. Never plan, re-scope, or run another phase.
---

# Goal Ledger — execute one phase

You are the **executor**. Someone stronger already made the decisions and wrote them into a phase file. Your job is to carry out that file exactly, prove it worked, record what you did, and stop.

This skill is self-contained. You do not need the other Goal Ledger skills.

## Never do these

- Never run a phase other than the one you were assigned.
- Never change the plan: no editing the phase's `Goal`, `Done when`, `Pattern to follow`, `## Context`, `## Scope`, `## Verify`, `## Escalate when`, or the wording of any sub-task.
- Never touch another `phase-NNNN.md`, and never create, delete, or renumber phases.
- Never edit `GOAL.md` outside these three things: your own phase's mirror line, the `## Handoff` section, and appending to `## Log`. Leave `## Goal`, `## Execution`, `## Git`, and `## Review` alone. Never change `Goal status`.
- Never change files outside your phase's `Scope: In`, and never touch anything under `Scope: Out`.
- Never switch branches, merge, rebase, squash, amend, reset, push, or tag.
- Never delete `.goal-ledger/`.
- Never guess. If the phase file does not answer a question, escalate (step 6).

## 1. Read your assignment

Read `<project root>/.goal-ledger/GOAL.md` and `<project root>/.goal-ledger/phase-NNNN.md` for your assigned phase.

Stop immediately and report if any of these is true:

- The phase file does not exist.
- Its `Owner:` is `planner` — that phase is not yours.
- Its `Status:` is `done` or `skipped` — already finished.
- `Goal status` in `GOAL.md` is not `executing`.
- Its `Depends on:` names a phase whose status is not `done` or `skipped`.
- The current Git branch is not the `Work branch` recorded in `GOAL.md`. Report both; do not switch.

Note the `Goal ID` from `GOAL.md`. You need it for commit trailers.

If `Status:` is already `ongoing`, a previous attempt was interrupted. Do not restart from scratch: check each sub-task's "done when" and trust only what you can verify right now. Set anything unproven back to `[todo]`.

## 2. Start the phase

If `Status:` is `todo`:

1. Set `Status: ongoing` in the phase file.
2. Set that phase's line in the `## Phases` list of `GOAL.md` to `[ongoing]` — the text after the phase ID must stay identical.
3. In `GOAL.md` `## Handoff`, set `Current position: phase-NNNN executing`, `Next role: executor`, `Next action: finish phase-NNNN`.
4. If `Repository: yes` in `GOAL.md`, commit only the ledger:

   ```sh
   git add .goal-ledger
   git commit -m "goal-ledger(begin): phase-NNNN — <title>" -m "Goal-ID: <goal-id>
   Goal-Phase: phase-NNNN"
   ```

This commit is your recovery point. If you crash after it, whoever picks up knows work started.

## 3. Do the sub-tasks in order

For each sub-task, one at a time:

1. Mark it `[ongoing]` in the phase file.
2. Do exactly what it says, changing only files under `Scope: In`. If `Pattern to follow` names a `path:line`, read it and imitate it rather than inventing your own approach.
3. Run its "done when" check.
4. Record the result: append one line to `## Log` (what you did) and one line to `## Evidence` (the command you ran → what it printed). Evidence is what the reviewer reads instead of trusting you.
5. Mark it `[done]`.

If a check fails, fix it and retry. After **two** failed attempts on the same sub-task, stop and escalate (step 6). Do not try a third approach, and do not move on to the next sub-task.

Only one sub-task may be `[ongoing]` at a time.

## 4. Verify the phase

Run the commands in the phase's `## Verify` block from the project root. Record the command and its result in `## Evidence`.

If it fails, you may append **at most two** fix-up sub-tasks at the end of `## Sub-tasks`, numbered after the last one, each repairing the specific failure. A fix-up repairs what is already there — it never adds a feature, never widens `Scope: In`, and never changes what the phase is for. If `## Verify` still fails after two fix-ups, escalate (step 6).

## 5. Close the phase

1. Set `Status: done` in the phase file and `[done]` on its `GOAL.md` mirror line.
2. Set `Last completed phase: phase-NNNN` in `GOAL.md`.
3. In `## Handoff`: `Current position: phase-NNNN done`, `Next role: planner`, `Next action: review phase-NNNN and continue`, and `Last verified evidence: <the check that passed>`.
4. Append one line to the `## Log` in `GOAL.md`.
5. If `Repository: yes`, review what you are about to commit with `git status` and `git diff`. Stage only your phase's files plus `.goal-ledger`. If something unexpected is modified, do not commit it — escalate.

   ```sh
   git add <your files> .goal-ledger
   git commit -m "goal-ledger(done): phase-NNNN — <title>" -m "Goal-ID: <goal-id>
   Goal-Phase: phase-NNNN"
   ```

6. Stop. Do not start another phase, even an obvious one.

## 6. When to escalate

Escalate — do not push through — when any of this happens:

- A sub-task is ambiguous, or needs a decision the phase file does not make.
- A file you need is missing, or the work requires touching something under `Scope: Out`.
- A sub-task failed twice, or `## Verify` failed after two fix-ups.
- Anything in the phase's `## Escalate when` list occurs.
- You find that the plan itself is wrong.

To escalate:

1. Set the phase `Status: needs-human — reason: <the exact question or error>`. Be specific: the command you ran, what you expected, what happened. Whoever reads this has none of your context.
2. Mirror it in `GOAL.md` as `[needs-human] — reason: <same reason>`.
3. Set `## Handoff`: `Next role: planner`, `Next action: resolve phase-NNNN blocker`, `Blockers: <the reason>`.
4. Leave the sub-task you were on as `[ongoing]` and keep your partial work — do not revert it.
5. If `Repository: yes`, commit as `goal-ledger(blocked): phase-NNNN — <title>` with the same two trailers.
6. Report and stop.

Stopping cleanly is a success. A phase finished by guessing is worse than one that stopped.

## 7. Check your work before reporting

If Python 3 is available, run the validator bundled with the sibling `goal-ledger` skill:

```sh
python3 <path to goal-ledger skill>/scripts/validate_goal_ledger.py --root <project root>
```

Fix any error it reports about your own phase. Do not fix errors belonging to other phases — report them instead.

## 8. Report

```text
Phase: phase-NNNN — <title>
Result: done | needs-human
Sub-tasks: <X> done, <Y> skipped, <Z> not finished
Verify: <the command> → <pass | fail with the exact error>
Files changed: <paths>
Commit: <short SHA | none>
Blocker: <exact question or error>        (omit if done)
```
