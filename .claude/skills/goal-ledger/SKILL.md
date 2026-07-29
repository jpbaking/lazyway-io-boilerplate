---
name: goal-ledger
description: >-
  Plan, delegate, and accept a durable, git-tracked Goal Ledger for multi-phase
  or long-running work: .goal-ledger/GOAL.md plus phase-NNNN.md files, a
  planner/executor role split so a stronger model plans and reviews while
  cheaper models run the phases, approval gates, an isolated goal branch,
  committed recovery markers, a planner-tier review gate, and optional safe
  squashing on acceptance. Use when work needs several distinct phases, may
  span sessions, will be handed to another agent or model, needs crash
  recovery, or the user asks for a persistent goal or execution ledger.
  Sections 1-4 are the shared contract used by the goal-ledger-execute,
  goal-ledger-resume, goal-ledger-status, and goal-ledger-abandon skills.
---

# Goal Ledger — plan, delegate, review

Goal Ledger is a git-tracked execution record for one goal. It survives crashes, context compaction, session changes, and hand-off between agents and model tiers. The files and Git state are authoritative; memory and conversation summaries are not.

This skill is the **planner** procedure. A session running a single delegated phase uses `goal-ledger-execute` instead.

Sections 1–4 are the shared contract used by every Goal Ledger skill.

## 1. Roles and write scope

Goal Ledger separates two roles. A role is an authority level, not a model:

- **Planner** — drafts the plan, owns the goal, prepares Git, delegates phases, reviews the finished work at Gate D, and accepts. Should be the strongest model available.
- **Executor** — runs exactly one assigned phase from its written instructions, then stops. May be a cheaper model, a subagent, or a separate CLI session.

`Execution mode` in `GOAL.md` records which arrangement is in use:

- `solo` — one session holds both roles. Every rule still applies; the gates are not skipped.
- `delegated` — phases owned by `executor` are handed to a separate executor session.

**Write scope.** The executor writes to the ledger, but only inside its lane:

| Target | Planner | Executor |
|---|---|---|
| `GOAL.md` — `## Goal`, `## Execution`, `## Git`, `## Review`, phase list membership | write | **never** |
| `GOAL.md` — mirror line of the assigned phase | write | write |
| `GOAL.md` — `## Handoff` | write | write |
| `GOAL.md` — `## Log` | append | append |
| Assigned phase file — `Status`, sub-task statuses, `## Log`, `## Evidence` | write | write |
| Assigned phase file — `Goal`, `Done when`, `Pattern to follow`, `## Context`, `## Scope`, `## Verify`, `## Escalate when`, sub-task wording | write | **never** |
| Any phase file other than the assigned one | write | **never** |
| Create, delete, renumber, or re-scope phases | yes | **never** |
| `Goal status` | write | **never** |
| Branch, baseline, upstream, squash, push, tag | yes | **never** |
| Phase begin/close commits for the assigned phase | yes | yes |

The executor's one structural freedom: it may append **at most two** fix-up sub-tasks to its own phase to repair a failure of that phase's own `## Verify`. Fix-ups never add capability, widen `## Scope`, or change what the phase is for. Anything beyond that is a plan change, and a plan change is escalation, not initiative.

**Escalate, do not improvise.** When an executor hits a decision the phase file does not answer — an ambiguity, a missing file, a failing check it cannot fix inside its scope, work that needs a file listed under `Out` — it sets its phase to `needs-human — reason: <the exact question>`, updates Handoff, commits, and stops. A stopped phase is a successful hand-off. A phase completed by guessing is a corrupted one.

**Ordinary helper subagents** (search, analysis, and other non-phase delegation) are not executors. Their prompts must still say: `Ignore .goal-ledger and all Goal Ledger skills. Follow only the task in this prompt; do not create, resume, update, or abandon the ledger.` Only a session explicitly handed a phase ID through the `goal-ledger-execute` skill is an executor.

## 2. Ledger location and lifecycle

- **Location:** `<project root>/.goal-ledger/`. The project root owns the task's files and has its own repository or project manifest; never place the ledger at a multi-project workspace root.
- **Tracked state:** never add `.goal-ledger/` to `.gitignore`. Verify with `git check-ignore -v .goal-ledger/GOAL.md`. Remove an exact Goal Ledger ignore entry; if a broader user-owned pattern is responsible, explain it and obtain approval before adding a narrow negation or changing that pattern.
- **Contents:** exactly one `GOAL.md` plus one `phase-NNNN.md` per phase. Keep phase files beside `GOAL.md`; another directory level adds no useful information.
- **One current ledger:** never overwrite a goal whose status is not `completed` or `abandoned`. Resume it or use the `goal-ledger-abandon` skill.
- **Completed history:** keep the completed ledger in the final committed snapshot. A later goal may replace `.goal-ledger/` only after its own plan is approved; the previous ledger remains recoverable from Git history.
- **One writer at a time:** the ledger has no locking. Exactly one session may hold a phase. Before delegating, the planner records the delegated phase in Handoff and does not touch that phase file until the executor returns. Never run two executors concurrently against one ledger.

## 3. File format and invariants

Use a stable Goal ID: `YYYYMMDD-<short-kebab-slug>`. If that ID already appears in repository history, append `-2`, `-3`, and so on. The recommended branch is `goal/<goal-id>`.

The `GOAL.md` mirror and sub-task vocabulary is exactly: `[todo]`, `[ongoing]`, `[done]`, `[skipped] — reason: <why>`, and `[needs-human] — reason: <question/error>`. A phase file uses the same value without brackets on its `Status:` line. At most one phase and one sub-task may be ongoing.

`GOAL.md`:

```markdown
# GOAL — <short title>

## Goal
- Goal ID: <stable ID>
- Outcome: <one sentence>
- Done when: <observable completion check>
- Goal status: drafting
- Goal status meaning: drafting | approved | executing | blocked-on-human | in-review | awaiting-acceptance | completed | abandoned
- Last completed phase: none

## Execution
- Execution mode: solo | delegated
- Planner tier: <model or agent that plans, reviews, and accepts>
- Executor tier: <model or agent that runs delegated phases | same>
- Full verification: <one command that must pass at Gate D | manual: <what to check>>

## Git
- Repository: yes | no
- Strategy: isolated-branch | current-branch | none
- Starting branch: <branch | "-">
- Work branch: <branch | "-">
- Baseline commit: <full immutable SHA | "-">
- Starting upstream at start: <ref>@<full SHA> | none | "-"
- Work upstream at start: <ref>@<full SHA> | none | "-"

## Phases
- [todo] phase-0001 — <title>

## Handoff
- Current position: planning
- Next role: planner
- Next action: approve the goal
- Last verified evidence: none
- Blockers: none

## Review
- Reviewed by: none
- Verification result: none
- Diff reviewed: none
- Findings: none

## Log
- created ledger with <N> phases
```

`phase-NNNN.md`:

````markdown
# phase-NNNN — <title>

- Status: todo
- Owner: planner | executor
- Depends on: none
- Goal: <one line>
- Done when: <runnable or observable check>
- Pattern to follow: <path:line to imitate | none>

## Context
<2–6 lines an executor cannot derive from the code alone: why this phase exists,
what decision was already made for them, what the surrounding code assumes>

## Scope
- In: <exact paths or globs this phase may change>
- Out: <paths or areas to leave alone | none>

## Sub-tasks
1. [todo] <one concrete action> — done when: <mechanical check>

## Verify
```sh
<commands runnable from the project root; exit 0 means pass>
```

## Escalate when
- <condition> → stop, set Status: needs-human — reason: <what you need>

## Log
- (append-only, one line per event)

## Evidence
- (append-only: command → observed result)
````

Invariants:

- The phase file's `Status:` is authoritative; the matching bracketed line in `GOAL.md` mirrors it. Repair mismatches in favor of the phase file.
- `Owner:` is `planner` or `executor`. An executor session must refuse a phase owned by `planner`.
- `Last completed phase` identifies the phase most recently completed in execution order, which may differ from numeric phase order; it must name a phase whose status is `done`, or `none` when no phase is done.
- Every phase and sub-task has an observable "done when" check, and every phase has a runnable or explicitly manual `## Verify`.
- Draft 2–7 phases with 2–7 sub-tasks each. Later remediation may push either to 9; past that, the plan was wrong — say so rather than padding it. Add new numbered phases or sub-tasks; never renumber existing ones.
- A skipped phase satisfies dependencies only after verifying that its outputs are unnecessary or updating future todo phases accordingly. Record the reason in both the phase status and logs. Skip a whole phase only with explicit user approval or when verified evidence makes it unnecessary.
- Update `Handoff` whenever execution changes position, evidence, next action, next role, or blockers. It must let a new agent — possibly a weaker one, with no conversation history — continue from it alone.
- Append important events and decisions to logs. Never rewrite history to make a failed attempt disappear.
- Do not store a moving `HEAD` hash in `GOAL.md`. The immutable baseline and Git history are authoritative; a commit cannot reliably record its own hash.
- During drafting, set only `Repository`; use `Strategy: none` and `-` for every other Git field. Gate B replaces those placeholders from live Git state immediately before the first ledger commit.

## 4. Git contract

If `Repository: no`, use `Strategy: none`, keep Git fields as `-`, skip every Git operation, and never initialize a repository automatically.

For a repository:

- **Clean start:** before preparing Git, classify `git status --porcelain`. Changes inside `.goal-ledger/` are expected planning state. Any other pre-existing change must be resolved by the user: commit it, explicitly authorize a baseline snapshot commit, stash it, or stop. Never absorb unrelated work into the goal.
- **Immutable baseline:** record the full `HEAD` before the first Goal Ledger commit. Every goal commit lives strictly after this baseline.
- **Unborn repository:** if the repository has no `HEAD` commit, stop at Gate B. Ask the user to create an initial commit or explicitly authorize a baseline snapshot commit; never invent a zero SHA, silently initialize history, or continue without an immutable baseline.
- **Recommended isolated branch:** recommend `goal/<goal-id>`. Ask before creating or switching branches. Record the original branch as `Starting branch` and the goal branch as `Work branch`. From a detached `HEAD`, require creation of a named goal branch or stop for user direction; `current-branch` is not valid without a branch. Delegation makes the isolated branch close to mandatory: it is what lets a reviewer read exactly what the executors wrote.
- **Existing goal branch:** if the proposed work branch already exists, inspect it before switching. Reuse it only when it belongs to the same unfinished Goal ID and its history is consistent with the baseline. Otherwise ask the user to choose it deliberately or select a new suffixed Goal ID and branch; never reset or overwrite it.
- **Current-branch fallback:** if the user declines a goal branch, warn that shared or interleaved history can make automatic squashing unavailable. Record both branch fields as the current branch and use `Strategy: current-branch`.
- **Upstream snapshots:** before switching, record the starting branch's upstream ref and full SHA without fetching, or `none`. After choosing the work branch, record its upstream the same way. For `current-branch`, the two snapshots are identical; for a new isolated branch, the work upstream is normally `none`.
- **Commit identity:** every framework-created commit after the baseline has a `Goal-ID: <goal-id>` trailer. Phase commits also have `Goal-Phase: phase-NNNN`. Git history, not hashes copied into the ledger, is the commit ledger.
- **Committed recovery marker:** before doing phase work, set the phase file to `Status: ongoing`, set its `GOAL.md` mirror to `[ongoing]`, update Handoff, and commit the ledger as `goal-ledger(begin): phase-NNNN — <title>`. A clean tree after that commit means no work started; later dirty files identify interrupted work.
- **Phase close:** update the phase, mirror, `Last completed phase`, Handoff, and logs; inspect the worktree; stage only goal-owned changes; then commit as `goal-ledger(done): phase-NNNN — <title>` or `goal-ledger(blocked): phase-NNNN — <title>`.
- **Executors commit their own phase** — begin marker and close commit, nothing else. Executors never merge, rebase, squash, push, tag, switch branches, or touch another phase's commits.
- **Never automatically:** push, force-push, delete a branch, amend, rebase, hard-reset, or touch commits at or before the baseline. Publishing and merging are separate, explicitly requested acts; Goal Ledger prepares a reviewed branch and stops there.

### Optional squash on acceptance

Offer squashing only after Gate D passes and the user accepts the finished result. Before offering, require all of these:

1. The worktree is clean.
2. The current branch equals `Work branch`.
3. Every commit in `<baseline>..HEAD` carries the matching Goal ID.
4. The range has no merge commit or foreign/interleaved commit.
5. No goal commit is reachable from either recorded upstream or any locally known remote-tracking ref. If the goal branch was published for handoff, keep its commits and recommend a squash merge at integration time instead of rewriting the branch. If publication is uncertain, do not automate the squash.
6. For `current-branch`, its upstream ref still points to the SHA recorded at Gate B. If that ref advanced, rewound, or diverged, do not automate the squash even when the local goal range itself contains no foreign commit.

If any check fails, keep the commits and explain why. If all pass and the user explicitly chooses squash: soft-reset to the baseline, set the goal status to `completed`, update Handoff to completed with no next action, append the acceptance/squash event, retain the entire `.goal-ledger/`, stage the accepted snapshot, and create one meaningful commit with the Goal ID trailer. If the user declines squash: make the same terminal ledger updates and create a final `goal-ledger(complete): <title>` commit. The completed ledger must remain in either result.

## 5. Draft the ledger

1. Inspect the project and establish the outcome, overall "done when", approach, phases, dependencies, and checks.
2. Decide the execution mode. Choose `delegated` when phases are separable and much of the work is mechanical; choose `solo` when nearly every phase needs judgment. Record the planner and executor tiers.
3. Assign each phase an `Owner`. Keep for the planner anything that decides architecture, picks between designs, touches security or migrations, or cannot be checked mechanically. Give executors the bounded, repetitive, verifiable work.
4. Inspect Git state before writing so pre-existing changes can be distinguished from ledger files later.
5. Establish the `Full verification` command — the project's own suite, the thing Gate D will run. If none exists, either make building it phase-0001 or record `manual: <what to check>` honestly.
6. If no ledger exists, create `.goal-ledger/GOAL.md` with status `drafting` and every phase file. Do not change application code.
7. If an older ledger is `completed` or `abandoned`, preserve it until the new plan is approved. Draft the proposed replacement in the conversation or a temporary location outside the project, then write it into `.goal-ledger/` only after Gate A. The new goal's first commit records the replacement, leaving the previous ledger in Git history.

### Writing phases a weaker model can execute

The plan is the hand-off. Assume the executor has no conversation history, no memory of your reasoning, will read only what `## Scope` names, and will do exactly what the words say. Every ambiguity you leave becomes a guess you have to find at Gate D.

- **Decide in the plan, not in the phase.** No sub-task may require choosing between designs, naming a new abstraction, or judging how far to go. If a sub-task contains "as needed", "appropriately", "if necessary", or "refactor", it is a planner decision that has not been made yet.
- **Name exact paths.** `src/auth/session.ts` — never "the relevant file", "related tests", or "wherever this is used". If the executor must find call sites, make finding them a sub-task with the search command written out.
- **Prefer imitation over invention.** Fill `Pattern to follow` with a real `path:line` and say what to copy from it. "Add a handler shaped like the one at `src/api/users.ts:40`" beats a paragraph of specification.
- **Make `## Verify` runnable.** Copy-pasteable commands from the project root where exit 0 means pass. "Check that it looks right" is not a check. If it is genuinely manual, write `- manual:` and describe the observation precisely.
- **Write `## Escalate when` before the work, not after.** List the two or three ways this phase realistically goes wrong and state the stop condition for each. This is what converts a weak model's failure into a clean hand-off instead of a mess.
- **Keep `Out` honest.** Name the neighbouring files an eager executor would otherwise "improve".
- **Size each phase for one sitting.** A phase an executor cannot finish before its context fills is a phase that will be abandoned mid-way.

Run the bundled `scripts/validate_goal_ledger.py --root <project root> --no-git` after drafting. If Python 3 is unavailable, check every invariant in section 3 manually and report that deterministic validation was unavailable.

## 6. Approval and Git preparation gates

**Gate A — approve the goal:** show Outcome, Done when, the one-line phase list with owners, and the execution mode. Ask for approval. Apply feedback to the ledger and repeat until approved, then set status `approved` and update Handoff.

**Gate B — choose and prepare the Git strategy:** resolve non-ledger dirty changes first and verify the ledger is not ignored. Strongly recommend the isolated goal branch and explain that it makes recovery, hand-off, review, abandonment, and optional squashing deterministic. Ask permission to create/switch to it. If declined, show the current-branch warning and obtain explicit confirmation. Record all Git metadata, then commit the approved ledger as `goal-ledger(approve): <title>` with the Goal ID trailer.

**Gate C — execute:** ask whether to start execution. On yes, set Goal status `executing` and enter the loop. A single clear response such as "approved, create the branch, and go" may satisfy Gates A–C. The original task request never pre-approves an unseen ledger or a branch change.

## 7. Execution loop

1. Select the first `[todo]` phase whose dependencies are all `[done]` or safely `[skipped]` under section 3.
2. If `Execution mode` is `delegated` and the phase `Owner` is `executor`, delegate it (section 8) and wait. Otherwise run it yourself.
3. To run a phase yourself: set the phase file to `Status: ongoing` and its `GOAL.md` mirror to `[ongoing]`, update Handoff and logs, and create the committed recovery marker from section 4.
4. For each sub-task: mark `[ongoing]` before work; perform it; run its check; immediately mark `[done]`, `[skipped] — reason:`, or after two failed attempts `[needs-human] — reason:`; append to the phase `## Log` and record command results in `## Evidence`; update Handoff.
5. Run the phase's `## Verify`. If it fails, add a fix-up sub-task. After two failed fix-up rounds, mark the phase `needs-human`.
6. Review the overall Goal and remaining phases. Amend only future `[todo]` phases, logging why — this is a planner-only power. Skip an entire phase only under the skip rule in section 3.
7. Close and commit the phase under section 4. If nothing actionable remains, set Goal status `blocked-on-human` in that close commit (or create a blocked-state commit if no phase was closed), then stop.
8. At a phase boundary, compact context if useful, then re-anchor from `GOAL.md`, the next phase file, and Git. After uncertain or interrupted state, use the `goal-ledger-resume` skill.
9. Continue without asking between phases. When every phase is terminal and none needs human, set Goal status `in-review` and go to Gate D.

Run the bundled validator without `--no-git` after reconciliation, before each phase close, and before acceptance. Treat errors as blockers; record warnings that affect handoff or squash safety. If Python 3 is unavailable, perform the same checks manually and say so in the report.

## 8. Delegate a phase

Only for `Execution mode: delegated` and `Owner: executor`.

1. Re-read the phase file as if you had never seen it. If any sub-task needs a decision, any path is vague, or `## Verify` is not runnable, fix the phase file now — this is the last cheap moment.
2. Set Handoff: `Current position: phase-NNNN delegated`, `Next role: executor`, `Next action: execute phase-NNNN`. Commit the ledger. The executor creates its own begin marker.
3. Hand the executor this prompt and nothing else. It carries no context on purpose; everything it needs is in the ledger:

   ```text
   Use the goal-ledger-execute skill.
   Project root: <absolute path>
   Phase: phase-NNNN
   Execute that phase only. Do not plan, re-scope, or continue to another phase.
   ```

   For an in-session subagent, pass the same text as the task prompt.
4. Do not touch the phase file while the executor holds it.
5. When it returns, do not trust its summary. Read the phase file's `## Evidence`, re-run `## Verify` yourself, and read `git diff` for its close commit. Then either continue the loop, or return the phase to `[todo]` with a corrected plan and log why.
6. If the executor returned `needs-human`, answer the question in the phase `## Context` or `## Log`, return affected sub-tasks to `[todo]`, and re-delegate — or take the phase back yourself.

## 9. Gate D — planner review

Runs after every phase is terminal and before `awaiting-acceptance`. **Planner tier only.** An executor session that reaches this point stops and sets `Next role: planner`.

In `solo` mode, Gate D still runs; re-anchor from a compacted or fresh context first so the review is not just a recollection of writing the code.

1. Run the `Full verification` command. Record the exact result.
2. Read `git diff <baseline>..HEAD` in full — this is the only step that sees what the executors actually wrote, rather than what they reported.
3. Check for scope drift: every changed path should fall under some phase's `Scope: In`. Investigate anything that does not.
4. Read each phase's `## Evidence` against its `## Verify`. A phase marked done whose evidence does not show its check passing is unverified — re-run it.
5. Confirm the goal's own `Done when` actually holds. Phases passing individually does not prove the outcome.
6. Run the validator without `--no-git`.
7. Record the result in `## Review`: `Reviewed by`, `Verification result`, `Diff reviewed` (the range and whether it was read in full), and `Findings`.

Findings become work, not caveats: append fix-up sub-tasks to the relevant phase and reopen it, or add a new numbered remediation phase. Re-run Gate D afterwards. When it passes clean, set Goal status `awaiting-acceptance`, update Handoff, include that state in the final commit, report, and ask the user to review the result.

After acceptance, apply the optional squash procedure or create the completion commit. Do not delete the ledger. Pushing, opening a PR, and merging happen only when the user asks for them.

## 10. Report when execution stops

```text
Goal: <title> — <in-review | awaiting-acceptance | blocked-on-human>
Goal ID: <id>
Mode: <solo | delegated>; planner <tier>; executor <tier>
Strategy: <isolated-branch | current-branch | none> on <work branch>
Phases: <X> done, <Y> skipped, <Z> needs-human, <W> todo
Commits: <N> matching goal commits since <baseline>   (omit without Git)
Review: <verification result | not started>
Needs you:
- phase-NNNN sub-task N: <exact question or error>    (omit if none)
```
