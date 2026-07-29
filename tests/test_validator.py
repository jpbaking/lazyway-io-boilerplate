import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / ".agents" / "skills" / "goal-ledger" / "scripts" / "validate_goal_ledger.py"
SPEC = importlib.util.spec_from_file_location("validate_goal_ledger", VALIDATOR_PATH)
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


def goal_text(
    status="executing",
    repository="no",
    strategy="none",
    baseline="-",
    phase2_status="todo",
    mode="delegated",
    review="none",
):
    return f"""# GOAL — Test goal

## Goal
- Goal ID: 20260719-test-goal
- Outcome: Produce a verified result.
- Done when: Every fixture passes validation.
- Goal status: {status}
- Goal status meaning: drafting | approved | executing | blocked-on-human | in-review | awaiting-acceptance | completed | abandoned
- Last completed phase: phase-0001

## Execution
- Execution mode: {mode}
- Planner tier: strong-planner
- Executor tier: cheap-executor
- Full verification: python3 -m unittest discover -s tests

## Git
- Repository: {repository}
- Strategy: {strategy}
- Starting branch: -
- Work branch: -
- Baseline commit: {baseline}
- Starting upstream at start: -
- Work upstream at start: -

## Phases
- [done] phase-0001 — Prepare
- [{phase2_status}] phase-0002 — Verify

## Handoff
- Current position: planning
- Next role: planner
- Next action: verify
- Last verified evidence: fixture
- Blockers: none

## Review
- Reviewed by: {review}
- Verification result: {review}
- Diff reviewed: {review}
- Findings: none

## Log
- created ledger with 2 phases
"""


def phase_text(number, title, status, depends, owner="executor", context=None):
    return f"""# phase-{number:04d} — {title}

- Status: {status}
- Owner: {owner}
- Depends on: {depends}
- Goal: Complete {title.lower()}.
- Done when: The phase fixture passes.
- Pattern to follow: tests/test_validator.py:1

## Context
{context or f"The fixture for {title.lower()} already exists and must not be regenerated."}

## Scope
- In: fixture.txt
- Out: none

## Sub-tasks
1. [done] Perform first action — done when: first evidence exists
2. [done] Perform second action — done when: second evidence exists

## Verify
```sh
python3 -c "print('ok')"
```

## Escalate when
- The fixture file is missing → stop and set Status: needs-human

## Log
- fixture created

## Evidence
- python3 -c "print('ok')" → printed ok
"""


class ValidatorTests(unittest.TestCase):
    def make_ledger(self, root, goal=None, phase1_status="done", phase2_status="todo"):
        ledger = root / ".goal-ledger"
        ledger.mkdir()
        (ledger / "GOAL.md").write_text(goal or goal_text(phase2_status=phase2_status), encoding="utf-8")
        (ledger / "phase-0001.md").write_text(
            phase_text(1, "Prepare", phase1_status, "none"), encoding="utf-8"
        )
        (ledger / "phase-0002.md").write_text(
            phase_text(2, "Verify", phase2_status, "phase-0001"), encoding="utf-8"
        )

    def git(self, root, *args):
        return subprocess.run(
            ["git", "-C", str(root)] + list(args),
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).stdout.strip()

    def commit_fixture(self, root, subject, *body_parts):
        fixture = root / "fixture.txt"
        previous = fixture.read_text(encoding="utf-8") if fixture.exists() else ""
        fixture.write_text(previous + subject + "\n", encoding="utf-8")
        self.git(root, "add", "fixture.txt")
        args = ["commit", "-q", "-m", subject]
        for part in body_parts:
            args.extend(("-m", part))
        self.git(root, *args)
        return self.git(root, "rev-parse", "HEAD")

    def test_valid_non_git_ledger(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_ledger(root)
            result = VALIDATOR.LedgerValidator(root, check_git=False).validate()
            self.assertTrue(result["valid"], result)

    def test_no_git_mode_still_checks_ledger_git_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            invalid_goal = goal_text().replace("- Work branch: -", "- Work branch: leftover")
            self.make_ledger(root, goal=invalid_goal)

            result = VALIDATOR.LedgerValidator(root, check_git=False).validate()

            self.assertFalse(result["valid"])
            self.assertIn("Repository no requires 'Work branch'", "\n".join(result["errors"]))

    def test_detects_mirror_mismatch_and_extra_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_ledger(root)
            phase = root / ".goal-ledger" / "phase-0002.md"
            phase.write_text(phase.read_text(encoding="utf-8").replace("Status: todo", "Status: ongoing"), encoding="utf-8")
            (root / ".goal-ledger" / "notes.md").write_text("unexpected", encoding="utf-8")
            result = VALIDATOR.LedgerValidator(root, check_git=False).validate()
            self.assertFalse(result["valid"])
            joined = "\n".join(result["errors"])
            self.assertIn("does not match", joined)
            self.assertIn("Unexpected", joined)

    def test_log_field_does_not_shadow_handoff_field(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            goal = goal_text().replace(
                "- created ledger with 2 phases", "- Next action: retry tests"
            )
            self.make_ledger(root, goal=goal)
            validator = VALIDATOR.LedgerValidator(root, check_git=False)

            result = validator.validate()

            self.assertTrue(result["valid"], result)
            self.assertEqual(validator.goal_fields["Next action"], "verify")

    def test_reason_suffix_is_rejected_for_done_status(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            invalid = "done — reason: should not be accepted"
            goal = goal_text().replace("[done] phase-0001", f"[{invalid}] phase-0001")
            self.make_ledger(root, goal=goal, phase1_status=invalid)

            result = VALIDATOR.LedgerValidator(root, check_git=False).validate()

            self.assertFalse(result["valid"])
            self.assertIn("invalid status", "\n".join(result["errors"]))

    def test_ongoing_subtask_in_nonongoing_phase_warns(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_ledger(root)
            phase = root / ".goal-ledger" / "phase-0002.md"
            phase.write_text(
                phase.read_text(encoding="utf-8").replace(
                    "1. [done] Perform first action", "1. [ongoing] Perform first action"
                ),
                encoding="utf-8",
            )

            result = VALIDATOR.LedgerValidator(root, check_git=False).validate()

            self.assertTrue(result["valid"], result)
            self.assertIn("while its phase is todo", "\n".join(result["warnings"]))

    def test_expanded_subtask_check_placeholder_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_ledger(root)
            phase = root / ".goal-ledger" / "phase-0002.md"
            phase.write_text(
                phase.read_text(encoding="utf-8").replace(
                    "first evidence exists", "<runnable or observable check>"
                ),
                encoding="utf-8",
            )

            result = VALIDATOR.LedgerValidator(root, check_git=False).validate()

            self.assertFalse(result["valid"])
            self.assertIn("lacks an observable check", "\n".join(result["errors"]))

    def test_prepared_strategy_requires_structured_upstream_snapshots(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            goal = goal_text(
                repository="yes", strategy="current-branch", baseline="a" * 40
            )
            goal = goal.replace("- Starting branch: -", "- Starting branch: main")
            goal = goal.replace("- Work branch: -", "- Work branch: main")
            goal = goal.replace("- Starting upstream at start: -", "- Starting upstream at start: malformed")
            goal = goal.replace("- Work upstream at start: -", "- Work upstream at start: none")
            self.make_ledger(root, goal=goal)

            result = VALIDATOR.LedgerValidator(root, check_git=False).validate()

            self.assertFalse(result["valid"])
            self.assertIn("Starting upstream at start", "\n".join(result["errors"]))

    def test_skipped_phase_with_reason_can_satisfy_dependency(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            skipped = "skipped — reason: verified unnecessary"
            goal = goal_text(phase2_status="todo").replace("[done] phase-0001", f"[{skipped}] phase-0001")
            goal = goal.replace("Last completed phase: phase-0001", "Last completed phase: none")
            self.make_ledger(root, goal=goal, phase1_status=skipped)
            result = VALIDATOR.LedgerValidator(root, check_git=False).validate()
            self.assertTrue(result["valid"], result)

    def test_last_completed_phase_follows_forward_dependency_completion_order(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            goal = goal_text(phase2_status="done")
            self.make_ledger(root, goal=goal, phase1_status="done", phase2_status="done")
            ledger = root / ".goal-ledger"
            (ledger / "phase-0001.md").write_text(
                phase_text(1, "Prepare", "done", "phase-0002"), encoding="utf-8"
            )
            (ledger / "phase-0002.md").write_text(
                phase_text(2, "Verify", "done", "none"), encoding="utf-8"
            )

            result = VALIDATOR.LedgerValidator(root, check_git=False).validate()

            self.assertTrue(result["valid"], result)

    def test_unborn_repository_has_actionable_error(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            goal = goal_text(status="approved", repository="yes", strategy="none")
            self.make_ledger(root, goal=goal)
            result = VALIDATOR.LedgerValidator(root, check_git=True).validate()
            self.assertFalse(result["valid"])
            self.assertIn("no initial commit", "\n".join(result["errors"]))

    def test_commit_trailer_classification_in_fixture_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.git(root, "init", "-q")
            self.git(root, "config", "user.name", "Goal Ledger Test")
            self.git(root, "config", "user.email", "goal-ledger@example.invalid")
            baseline = self.commit_fixture(root, "baseline")
            branch = self.git(root, "branch", "--show-current")
            matching = self.commit_fixture(
                root,
                "goal-ledger(done): phase-0001 — Prepare",
                "Goal-ID: 20260719-test-goal\nGoal-Phase: phase-0001",
            )
            missing = self.commit_fixture(root, "goal-ledger(begin): phase-0002 — Verify")
            foreign = self.commit_fixture(root, "feat: unrelated", "Goal-ID: 20260719-other-goal")
            unclassified = self.commit_fixture(root, "docs: unrelated")
            unknown_phase = self.commit_fixture(
                root,
                "test: unknown phase trailer",
                "Goal-ID: 20260719-test-goal\nGoal-Phase: phase-9999",
            )
            goal = goal_text(
                repository="yes", strategy="current-branch", baseline=baseline
            )
            goal = goal.replace("- Starting branch: -", f"- Starting branch: {branch}")
            goal = goal.replace("- Work branch: -", f"- Work branch: {branch}")
            goal = goal.replace("- Starting upstream at start: -", "- Starting upstream at start: none")
            goal = goal.replace("- Work upstream at start: -", "- Work upstream at start: none")
            self.make_ledger(root, goal=goal)

            result = VALIDATOR.LedgerValidator(root, check_git=True).validate()

            errors = "\n".join(result["errors"])
            warnings = "\n".join(result["warnings"])
            self.assertFalse(result["valid"])
            self.assertNotIn(matching[:12], errors + warnings)
            self.assertIn(f"Framework commit {missing[:12]} lacks matching Goal-ID", errors)
            self.assertIn(f"Commit {foreign[:12]} carries a foreign Goal-ID", warnings)
            self.assertIn(f"Commit {unclassified[:12]} is foreign to this goal", warnings)
            self.assertIn(f"Commit {unknown_phase[:12]} references unknown phase-9999", errors)

    def test_owner_must_be_planner_or_executor(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_ledger(root)
            phase = root / ".goal-ledger" / "phase-0002.md"
            phase.write_text(
                phase.read_text(encoding="utf-8").replace("Owner: executor", "Owner: intern"),
                encoding="utf-8",
            )

            result = VALIDATOR.LedgerValidator(root, check_git=False).validate()

            self.assertFalse(result["valid"])
            self.assertIn("Owner must be planner or executor", "\n".join(result["errors"]))

    def test_phase_without_runnable_or_manual_verify_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_ledger(root)
            phase = root / ".goal-ledger" / "phase-0002.md"
            phase.write_text(
                phase.read_text(encoding="utf-8").replace(
                    '```sh\npython3 -c "print(\'ok\')"\n```',
                    "Check that the result looks right.",
                ),
                encoding="utf-8",
            )

            result = VALIDATOR.LedgerValidator(root, check_git=False).validate()

            self.assertFalse(result["valid"])
            self.assertIn("'## Verify' needs a runnable command block", "\n".join(result["errors"]))

    def test_manual_only_verify_warns_for_executor_owned_phase(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_ledger(root)
            phase = root / ".goal-ledger" / "phase-0002.md"
            phase.write_text(
                phase.read_text(encoding="utf-8").replace(
                    '```sh\npython3 -c "print(\'ok\')"\n```',
                    "- manual: confirm the banner renders",
                ),
                encoding="utf-8",
            )

            result = VALIDATOR.LedgerValidator(root, check_git=False).validate()

            self.assertTrue(result["valid"], result)
            self.assertIn("'## Verify' is manual only", "\n".join(result["warnings"]))

    def test_scope_requires_in_and_out_lines(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_ledger(root)
            phase = root / ".goal-ledger" / "phase-0002.md"
            phase.write_text(
                phase.read_text(encoding="utf-8").replace("- Out: none\n", ""),
                encoding="utf-8",
            )

            result = VALIDATOR.LedgerValidator(root, check_git=False).validate()

            self.assertFalse(result["valid"])
            self.assertIn("'## Scope' is missing the '- Out:' line", "\n".join(result["errors"]))

    def test_placeholder_scope_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_ledger(root)
            phase = root / ".goal-ledger" / "phase-0002.md"
            phase.write_text(
                phase.read_text(encoding="utf-8").replace(
                    "- In: fixture.txt", "- In: <exact paths this phase may change>"
                ),
                encoding="utf-8",
            )

            result = VALIDATOR.LedgerValidator(root, check_git=False).validate()

            self.assertFalse(result["valid"])
            self.assertIn("placeholder '- In:' line", "\n".join(result["errors"]))

    def test_escalate_when_requires_a_real_condition(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_ledger(root)
            phase = root / ".goal-ledger" / "phase-0002.md"
            phase.write_text(
                phase.read_text(encoding="utf-8").replace(
                    "- The fixture file is missing → stop and set Status: needs-human",
                    "- <condition> → stop and set Status: needs-human — reason: <what you need>",
                ),
                encoding="utf-8",
            )

            result = VALIDATOR.LedgerValidator(root, check_git=False).validate()

            self.assertFalse(result["valid"])
            self.assertIn("'## Escalate when' needs at least one real stop condition", "\n".join(result["errors"]))

    def test_missing_execution_section_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            goal = goal_text()
            start = goal.index("## Execution")
            goal = goal[:start] + goal[goal.index("## Git") :]
            self.make_ledger(root, goal=goal)

            result = VALIDATOR.LedgerValidator(root, check_git=False).validate()

            self.assertFalse(result["valid"])
            joined = "\n".join(result["errors"])
            self.assertIn("missing the '## Execution' section", joined)
            self.assertIn("Execution mode", joined)

    def test_acceptance_requires_gate_d_review(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            goal = goal_text(status="awaiting-acceptance", phase2_status="done")
            self.make_ledger(root, goal=goal, phase1_status="done", phase2_status="done")

            result = VALIDATOR.LedgerValidator(root, check_git=False).validate()

            self.assertFalse(result["valid"])
            self.assertIn("requires Gate D review", "\n".join(result["errors"]))

    def test_acceptance_passes_once_review_is_recorded(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            goal = goal_text(
                status="awaiting-acceptance", phase2_status="done", review="strong-planner: pass"
            )
            self.make_ledger(root, goal=goal, phase1_status="done", phase2_status="done")

            result = VALIDATOR.LedgerValidator(root, check_git=False).validate()

            self.assertTrue(result["valid"], result)

    def test_in_review_requires_every_phase_terminal(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_ledger(root, goal=goal_text(status="in-review"))

            result = VALIDATOR.LedgerValidator(root, check_git=False).validate()

            self.assertFalse(result["valid"])
            self.assertIn(
                "Goal status 'in-review' requires every phase to be done or skipped",
                "\n".join(result["errors"]),
            )

    def test_undecided_wording_in_executor_subtask_warns(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_ledger(root)
            phase = root / ".goal-ledger" / "phase-0002.md"
            phase.write_text(
                phase.read_text(encoding="utf-8").replace(
                    "Perform first action", "Update the related callers as needed"
                ),
                encoding="utf-8",
            )

            result = VALIDATOR.LedgerValidator(root, check_git=False).validate()

            self.assertTrue(result["valid"], result)
            self.assertIn("leaves a decision to the executor", "\n".join(result["warnings"]))

    def test_undecided_wording_is_allowed_for_planner_owned_phase(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_ledger(root)
            phase = root / ".goal-ledger" / "phase-0002.md"
            phase.write_text(
                phase.read_text(encoding="utf-8")
                .replace("Owner: executor", "Owner: planner")
                .replace("Perform first action", "Update the related callers as needed"),
                encoding="utf-8",
            )

            result = VALIDATOR.LedgerValidator(root, check_git=False).validate()

            self.assertTrue(result["valid"], result)
            self.assertNotIn("leaves a decision", "\n".join(result["warnings"]))

    def test_done_phase_without_evidence_warns(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_ledger(root)
            phase = root / ".goal-ledger" / "phase-0001.md"
            phase.write_text(
                phase.read_text(encoding="utf-8").replace(
                    '- python3 -c "print(\'ok\')" → printed ok',
                    "- (append-only: command → observed result)",
                ),
                encoding="utf-8",
            )

            result = VALIDATOR.LedgerValidator(root, check_git=False).validate()

            self.assertTrue(result["valid"], result)
            self.assertIn("its result is unverified", "\n".join(result["warnings"]))

    def test_numbered_lines_outside_subtasks_are_not_parsed_as_subtasks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ledger = root / ".goal-ledger"
            ledger.mkdir()
            (ledger / "GOAL.md").write_text(goal_text(), encoding="utf-8")
            (ledger / "phase-0001.md").write_text(
                phase_text(
                    1,
                    "Prepare",
                    "done",
                    "none",
                    context="Background:\n1. The fixture predates this goal.\n2. Keep its format.",
                ),
                encoding="utf-8",
            )
            (ledger / "phase-0002.md").write_text(
                phase_text(2, "Verify", "todo", "phase-0001"), encoding="utf-8"
            )

            result = VALIDATOR.LedgerValidator(root, check_git=False).validate()

            self.assertTrue(result["valid"], result)

    def test_missing_git_binary_has_actionable_error(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            goal = goal_text(status="approved", repository="yes", strategy="none")
            self.make_ledger(root, goal=goal)

            with mock.patch.object(VALIDATOR.subprocess, "run", side_effect=FileNotFoundError):
                result = VALIDATOR.LedgerValidator(root, check_git=True).validate()

            self.assertFalse(result["valid"])
            self.assertEqual(
                [error for error in result["errors"] if "git is unavailable" in error],
                ["git is unavailable; run with --no-git or install git."],
            )


if __name__ == "__main__":
    unittest.main()
