# Goal Ledger family

Goal Ledger is a git-tracked execution record for one goal, designed for crash recovery and hand-off between agents and model tiers. Its state lives in `<project root>/.goal-ledger/`: `GOAL.md` plus `phase-NNNN.md` files. Procedures live in five skills; load exactly one:

| Situation | Load |
|---|---|
| You were handed a phase ID to run (`goal-ledger-execute` + `phase-NNNN`) | **goal-ledger-execute** — run that one phase, then stop |
| New multi-phase or long-running goal | **goal-ledger** — draft, approve, prepare Git, delegate, review |
| Unfinished ledger / "resume" / "continue" / recovery after a crash or compaction | **goal-ledger-resume** — verify, reconcile, continue |
| "where are we" / "goal status" / "what is left" | **goal-ledger-status** — read-only report |
| Explicit "abandon" / "cancel" / "scrap this goal" | **goal-ledger-abandon** — preserve the record and mark it abandoned |

**Roles:** a *planner* owns the goal — it plans, delegates, reviews at Gate D, and accepts; it should be the strongest model available. An *executor* runs one assigned phase from its written instructions and stops; it may be a cheaper model or a separate session. In `solo` mode one session holds both roles, and the gates still apply.

**Resume check:** at the start of every primary-session task, if `.goal-ledger/GOAL.md` exists with a `Goal status:` other than `completed` or `abandoned`, use the `goal-ledger-resume` skill before starting unrelated work. Two exceptions: a session handed a specific phase uses the `goal-ledger-execute` skill instead, and an ordinary helper subagent working from a delegated prompt ignores the ledger entirely. Never overwrite or delete an unfinished ledger.

**When to start:** use Goal Ledger when work needs several distinct phases, may outlive one session, will be handed to another agent or model tier, or the user asks for a persistent goal or execution ledger. Ordinary short planning is not a trigger.

**Git strategy:** strongly recommend an isolated `goal/<goal-id>` branch — with delegation it is what lets the planner review exactly what the executors wrote. If the user stays on the current branch, preserve the same baseline and Goal-ID tracking but apply stricter squash checks. Never rewrite shared or published history automatically, and never push, open a PR, or merge unless the user asks.

**Write scope:** executors write only their own phase file, their phase's mirror line in `GOAL.md`, `## Handoff`, and `## Log`. `Goal status`, the phase list, Git fields, and `## Review` are planner-only. An executor that meets a decision its phase file does not answer sets `needs-human — reason:` and stops rather than guessing.

**Continuity:** ledger files and Git win over memory and conversation summaries. Whenever the planner delegates non-phase work (search, analysis) it must tell that subagent: `Ignore .goal-ledger and all Goal Ledger skills. Follow only the task in this prompt; do not create, resume, update, or abandon the ledger.` Results returned by any delegate are claims until the planner re-runs the check itself.
