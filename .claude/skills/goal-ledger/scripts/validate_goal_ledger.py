#!/usr/bin/env python3
"""Validate Goal Ledger files and, when available, their Git contract."""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


PHASE_STATUS_RE = re.compile(
    r"^(todo|ongoing|done|skipped|needs-human)(?: — reason: (.+))?$"
)
GOAL_STATUSES = {
    "drafting",
    "approved",
    "executing",
    "blocked-on-human",
    "in-review",
    "awaiting-acceptance",
    "completed",
    "abandoned",
}
TERMINAL_PHASE_STATUSES = {"done", "skipped"}
EXECUTION_MODES = {"solo", "delegated"}
PHASE_OWNERS = {"planner", "executor"}
HANDOFF_ROLES = {"planner", "executor"}
REVIEWED_GOAL_STATUSES = {"awaiting-acceptance", "completed"}
REVIEW_FIELDS = ("Reviewed by", "Verification result", "Diff reviewed", "Findings")
# 'Findings: none' is a legitimate clean-review result; the rest must be filled in.
REVIEW_COMPLETION_FIELDS = ("Reviewed by", "Verification result", "Diff reviewed")
REQUIRED_PHASE_SECTIONS = (
    "Context",
    "Scope",
    "Sub-tasks",
    "Verify",
    "Escalate when",
    "Log",
    "Evidence",
)
MIN_PHASES = 2
MAX_PHASES = 9
MIN_SUBTASKS = 2
MAX_SUBTASKS = 9
FULL_SHA_RE = re.compile(r"^[0-9a-fA-F]{40,64}$")
UPSTREAM_RE = re.compile(r"^.+@[0-9a-fA-F]{40,64}$")
GOAL_ID_RE = re.compile(r"^\d{8}-[a-z0-9]+(?:-[a-z0-9]+)*$")
PHASE_ID_RE = re.compile(r"^phase-\d{4}$")
FENCE_RE = re.compile(r"(?ms)^```[^\n]*\n(.*?)^```\s*$")
UNDECIDED_RE = re.compile(
    r"(?i)\b(as needed|as appropriate|if necessary|if needed|where relevant|"
    r"and so on|etc\.|somehow|figure out|decide how)\b"
)


class LedgerValidator:
    def __init__(self, root, check_git=True):
        self.root = Path(root).resolve()
        self.ledger = self.root / ".goal-ledger"
        self.check_git = check_git
        self.errors = []
        self.warnings = []
        self.goal_fields = {}
        self.goal_phases = {}
        self.phase_data = {}
        self.git_unavailable = False

    def error(self, message):
        self.errors.append(message)

    def warn(self, message):
        self.warnings.append(message)

    @staticmethod
    def read_text(path):
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("{} is not valid UTF-8: {}".format(path, exc))

    @staticmethod
    def section_body(text, section):
        """Return the body of a '## <section>' block, or None when absent."""
        match = re.search(
            r"(?ms)^## {}\s*\n(.*?)(?=^## |\Z)".format(re.escape(section)), text
        )
        return match.group(1) if match else None

    @classmethod
    def field_map(cls, text, section=None):
        if section is not None:
            text = cls.section_body(text, section) or ""
        fields = {}
        for match in re.finditer(r"(?m)^- ([A-Za-z][A-Za-z ]+): (.*)$", text):
            fields[match.group(1)] = match.group(2).strip()
        return fields

    @staticmethod
    def is_placeholder(value):
        """True for unfilled template text such as '<runnable check>'."""
        value = value.strip()
        return not value or (value.startswith("<") and value.endswith(">"))

    @staticmethod
    def parse_status(value):
        match = PHASE_STATUS_RE.fullmatch(value)
        if not match:
            return None, None
        status, reason = match.groups()
        if reason and status not in ("skipped", "needs-human"):
            return None, None
        return status, reason

    def require_field(self, fields, name, context):
        value = fields.get(name)
        if value is None or value == "":
            self.error("{} is missing '{}'.".format(context, name))
            return ""
        return value

    def validate(self):
        if not self.ledger.is_dir():
            self.error("{} does not exist.".format(self.ledger))
            return self.result()
        self.validate_goal()
        self.validate_phase_files()
        self.validate_cross_file_state()
        self.validate_git_fields()
        if self.check_git:
            self.validate_git()
        return self.result()

    def validate_goal(self):
        goal_path = self.ledger / "GOAL.md"
        if not goal_path.is_file():
            self.error(".goal-ledger/GOAL.md is missing.")
            return
        try:
            text = self.read_text(goal_path)
        except ValueError as exc:
            self.error(str(exc))
            return
        for section in ("Goal", "Execution", "Git", "Handoff", "Review"):
            if self.section_body(text, section) is None:
                self.error("GOAL.md is missing the '## {}' section.".format(section))
            self.goal_fields.update(self.field_map(text, section))

        goal_id = self.require_field(self.goal_fields, "Goal ID", "GOAL.md")
        if goal_id and not GOAL_ID_RE.fullmatch(goal_id):
            self.error("Goal ID must be YYYYMMDD-short-kebab-slug; got '{}'.".format(goal_id))

        for name in ("Outcome", "Done when", "Goal status", "Last completed phase"):
            self.require_field(self.goal_fields, name, "GOAL.md")
        goal_status = self.goal_fields.get("Goal status", "")
        if goal_status and goal_status not in GOAL_STATUSES:
            self.error("Unknown Goal status '{}'.".format(goal_status))

        execution_mode = self.require_field(self.goal_fields, "Execution mode", "GOAL.md")
        if execution_mode and execution_mode not in EXECUTION_MODES:
            self.error(
                "Execution mode must be solo or delegated; got '{}'.".format(execution_mode)
            )
        for name in ("Planner tier", "Executor tier", "Full verification"):
            value = self.require_field(self.goal_fields, name, "GOAL.md")
            if value and self.is_placeholder(value):
                self.error("GOAL.md '{}' is still a placeholder.".format(name))

        for name in REVIEW_FIELDS:
            self.require_field(self.goal_fields, name, "GOAL.md")

        repository = self.require_field(self.goal_fields, "Repository", "GOAL.md")
        if repository not in ("yes", "no"):
            self.error("Repository must be yes or no; got '{}'.".format(repository))
        for name in (
            "Strategy",
            "Starting branch",
            "Work branch",
            "Baseline commit",
            "Starting upstream at start",
            "Work upstream at start",
        ):
            self.require_field(self.goal_fields, name, "GOAL.md")
        for name in (
            "Current position",
            "Next role",
            "Next action",
            "Last verified evidence",
            "Blockers",
        ):
            self.require_field(self.goal_fields, name, "GOAL.md")
        next_role = self.goal_fields.get("Next role", "")
        if next_role and next_role not in HANDOFF_ROLES:
            self.error("Handoff 'Next role' must be planner or executor; got '{}'.".format(next_role))

        phase_pattern = re.compile(
            r"(?m)^- \[([^\]]+)\] (phase-\d{4}) — (.+)$"
        )
        for match in phase_pattern.finditer(text):
            status_value, phase_id, title = match.groups()
            if phase_id in self.goal_phases:
                self.error("GOAL.md lists {} more than once.".format(phase_id))
            self.goal_phases[phase_id] = {"status_value": status_value, "title": title}
            status, reason = self.parse_status(status_value)
            if status is None:
                self.error("GOAL.md has invalid status '[{}]' for {}.".format(status_value, phase_id))
            elif status in ("skipped", "needs-human") and not reason:
                self.error("{} status requires '— reason: <why>'.".format(phase_id))

        if not MIN_PHASES <= len(self.goal_phases) <= MAX_PHASES:
            self.error(
                "GOAL.md must list {}–{} phases; found {}.".format(
                    MIN_PHASES, MAX_PHASES, len(self.goal_phases)
                )
            )

    def validate_phase_files(self):
        expected_files = {"GOAL.md"}
        expected_files.update("{}.md".format(phase_id) for phase_id in self.goal_phases)
        actual_entries = {entry.name for entry in self.ledger.iterdir()}
        extras = sorted(actual_entries - expected_files)
        missing = sorted(expected_files - actual_entries)
        if extras:
            self.error("Unexpected .goal-ledger entries: {}.".format(", ".join(extras)))
        if missing:
            self.error("Missing .goal-ledger entries: {}.".format(", ".join(missing)))

        ongoing_subtasks = []
        owners = {}
        for phase_id in sorted(self.goal_phases):
            phase_path = self.ledger / "{}.md".format(phase_id)
            if not phase_path.is_file():
                continue
            try:
                text = self.read_text(phase_path)
            except ValueError as exc:
                self.error(str(exc))
                continue
            fields = self.field_map(text.split("\n## ", 1)[0])
            heading = re.search(r"(?m)^# (phase-\d{4}) — (.+)$", text)
            if not heading:
                self.error("{} has an invalid heading.".format(phase_path.name))
                title = ""
            else:
                heading_id, title = heading.groups()
                if heading_id != phase_id:
                    self.error("{} heading identifies {}.".format(phase_path.name, heading_id))
                if title != self.goal_phases[phase_id]["title"]:
                    self.error("{} title does not match GOAL.md.".format(phase_id))

            status_value = self.require_field(fields, "Status", phase_path.name)
            status, reason = self.parse_status(status_value)
            if status is None:
                self.error("{} has invalid Status '{}'.".format(phase_path.name, status_value))
            elif status in ("skipped", "needs-human") and not reason:
                self.error("{} Status requires '— reason: <why>'.".format(phase_path.name))
            if status_value != self.goal_phases[phase_id]["status_value"]:
                self.error("{} Status does not match its GOAL.md mirror.".format(phase_id))

            owner = self.require_field(fields, "Owner", phase_path.name)
            if owner and owner not in PHASE_OWNERS:
                self.error(
                    "{} Owner must be planner or executor; got '{}'.".format(
                        phase_path.name, owner
                    )
                )
            owners[phase_id] = owner

            depends = self.require_field(fields, "Depends on", phase_path.name)
            done_when = self.require_field(fields, "Done when", phase_path.name)
            self.require_field(fields, "Goal", phase_path.name)
            if done_when and self.is_placeholder(done_when):
                self.error("{} still contains a placeholder Done when.".format(phase_path.name))
            pattern = self.require_field(fields, "Pattern to follow", phase_path.name)
            if pattern and self.is_placeholder(pattern):
                self.error(
                    "{} 'Pattern to follow' is a placeholder; use a path:line or 'none'.".format(
                        phase_path.name
                    )
                )

            self.validate_phase_sections(phase_path.name, phase_id, text, status, owner)

            dependencies = [] if depends == "none" else [item.strip() for item in depends.split(",")]
            for dependency in dependencies:
                if not PHASE_ID_RE.fullmatch(dependency):
                    self.error("{} has invalid dependency '{}'.".format(phase_id, dependency))

            subtask_pattern = re.compile(
                r"(?m)^(\d+)\. \[([^\]]+)\] (.+?) — done when: (.+)$"
            )
            subtask_body = self.section_body(text, "Sub-tasks") or ""
            subtasks = []
            for match in subtask_pattern.finditer(subtask_body):
                number, status_text, action, check = match.groups()
                sub_status, sub_reason = self.parse_status(status_text)
                if sub_status is None:
                    self.error("{} sub-task {} has invalid status '[{}]'.".format(phase_id, number, status_text))
                elif sub_status in ("skipped", "needs-human") and not sub_reason:
                    self.error("{} sub-task {} requires a reason.".format(phase_id, number))
                if not action.strip() or self.is_placeholder(check):
                    self.error("{} sub-task {} lacks an observable check.".format(phase_id, number))
                undecided = UNDECIDED_RE.search(action) or UNDECIDED_RE.search(check)
                if undecided and owner == "executor":
                    self.warn(
                        "{} sub-task {} leaves a decision to the executor "
                        "('{}'); an executor cannot resolve it.".format(
                            phase_id, number, undecided.group(0)
                        )
                    )
                if sub_status == "ongoing":
                    ongoing_subtasks.append("{} sub-task {}".format(phase_id, number))
                    if status != "ongoing":
                        self.warn(
                            "{} sub-task {} is ongoing while its phase is {}.".format(
                                phase_id, number, status or "invalid"
                            )
                        )
                subtasks.append({"number": int(number), "status": sub_status})

            numbered_lines = re.findall(r"(?m)^\d+\. .+$", subtask_body)
            if len(numbered_lines) != len(subtasks):
                self.error("{} contains malformed numbered sub-task lines.".format(phase_path.name))
            if not MIN_SUBTASKS <= len(subtasks) <= MAX_SUBTASKS:
                self.error(
                    "{} must contain {}–{} sub-tasks; found {}.".format(
                        phase_path.name, MIN_SUBTASKS, MAX_SUBTASKS, len(subtasks)
                    )
                )
            if [item["number"] for item in subtasks] != list(range(1, len(subtasks) + 1)):
                self.error("{} sub-tasks must be numbered consecutively from 1.".format(phase_path.name))

            self.phase_data[phase_id] = {
                "status": status,
                "status_value": status_value,
                "dependencies": dependencies,
                "subtasks": subtasks,
                "owner": owner,
            }

        if len(ongoing_subtasks) > 1:
            self.error("More than one sub-task is ongoing: {}.".format(", ".join(ongoing_subtasks)))

        if (
            self.goal_fields.get("Execution mode") == "delegated"
            and owners
            and "executor" not in owners.values()
        ):
            self.warn("Execution mode is delegated but no phase is owned by an executor.")

    def validate_phase_sections(self, name, phase_id, text, status, owner):
        """Check the executor-facing sections a delegated phase depends on."""
        bodies = {}
        for section in REQUIRED_PHASE_SECTIONS:
            body = self.section_body(text, section)
            if body is None:
                self.error("{} is missing the '## {}' section.".format(name, section))
            bodies[section] = body or ""

        context = bodies["Context"].strip()
        if self.is_placeholder(context):
            self.error("{} has an empty or placeholder '## Context'.".format(name))

        scope = self.field_map(bodies["Scope"])
        for key in ("In", "Out"):
            value = scope.get(key)
            if value is None:
                self.error("{} '## Scope' is missing the '- {}:' line.".format(name, key))
            elif self.is_placeholder(value):
                self.error(
                    "{} '## Scope' has a placeholder '- {}:' line.".format(name, key)
                )
        if scope.get("In", "").strip() == "none":
            self.error("{} '## Scope' must name at least one in-scope path.".format(name))

        verify = bodies["Verify"]
        fences = [block.strip() for block in FENCE_RE.findall(verify)]
        manual = [
            line.strip()
            for line in re.findall(r"(?m)^- manual: *(.*)$", verify)
            if line.strip()
        ]
        runnable = [block for block in fences if not self.is_placeholder(block)]
        if not runnable and not manual:
            self.error(
                "{} '## Verify' needs a runnable command block or a '- manual: <check>' line.".format(
                    name
                )
            )
        elif not runnable and owner == "executor":
            self.warn(
                "{} is executor-owned but '## Verify' is manual only; "
                "an executor cannot judge a subjective check.".format(name)
            )

        escalate = [
            line for line in bodies["Escalate when"].splitlines() if line.strip().startswith("- ")
        ]
        if not escalate or all(self.is_placeholder(line.strip()[2:]) for line in escalate):
            self.error("{} '## Escalate when' needs at least one real stop condition.".format(name))

        if status == "done":
            evidence = [
                line.strip()
                for line in bodies["Evidence"].splitlines()
                if line.strip().startswith("- ") and not line.strip().startswith("- (")
            ]
            if not evidence:
                self.warn(
                    "{} is done but '## Evidence' records nothing; "
                    "its result is unverified.".format(phase_id)
                )

    def validate_cross_file_state(self):
        ongoing_phases = [
            phase_id for phase_id, data in self.phase_data.items() if data["status"] == "ongoing"
        ]
        if len(ongoing_phases) > 1:
            self.error("More than one phase is ongoing: {}.".format(", ".join(ongoing_phases)))

        for phase_id, data in self.phase_data.items():
            for dependency in data["dependencies"]:
                if dependency not in self.phase_data:
                    self.error("{} depends on missing {}.".format(phase_id, dependency))
                elif dependency == phase_id:
                    self.error("{} cannot depend on itself.".format(phase_id))

        visiting = set()
        visited = set()

        def visit(phase_id):
            if phase_id in visiting:
                self.error("Phase dependency cycle includes {}.".format(phase_id))
                return
            if phase_id in visited or phase_id not in self.phase_data:
                return
            visiting.add(phase_id)
            for dependency in self.phase_data[phase_id]["dependencies"]:
                visit(dependency)
            visiting.remove(phase_id)
            visited.add(phase_id)

        for phase_id in self.phase_data:
            visit(phase_id)

        last_completed = self.goal_fields.get("Last completed phase", "")
        done_phases = sorted(
            phase_id for phase_id, data in self.phase_data.items() if data["status"] == "done"
        )
        if done_phases and last_completed == "none":
            self.error("Last completed phase is none even though completed phases exist.")
        if last_completed != "none":
            if last_completed not in self.phase_data:
                self.error("Last completed phase '{}' does not exist.".format(last_completed))
            elif self.phase_data[last_completed]["status"] != "done":
                self.error("Last completed phase '{}' is not done.".format(last_completed))

        goal_status = self.goal_fields.get("Goal status", "")
        statuses = [data["status"] for data in self.phase_data.values()]
        for phase_id, data in self.phase_data.items():
            if data["status"] in ("ongoing", "done"):
                unsatisfied = [
                    dependency
                    for dependency in data["dependencies"]
                    if dependency in self.phase_data
                    and self.phase_data[dependency]["status"] not in TERMINAL_PHASE_STATUSES
                ]
                if unsatisfied:
                    self.error(
                        "{} is {} before dependencies are terminal: {}.".format(
                            phase_id, data["status"], ", ".join(unsatisfied)
                        )
                    )
            if data["status"] == "done":
                unfinished = [
                    item["number"]
                    for item in data["subtasks"]
                    if item["status"] not in TERMINAL_PHASE_STATUSES
                ]
                if unfinished:
                    self.error(
                        "{} is done but sub-tasks are unfinished: {}.".format(
                            phase_id, ", ".join(str(number) for number in unfinished)
                        )
                    )
        if goal_status in ("in-review", "awaiting-acceptance", "completed"):
            nonterminal = [status for status in statuses if status not in TERMINAL_PHASE_STATUSES]
            if nonterminal:
                self.error("Goal status '{}' requires every phase to be done or skipped.".format(goal_status))
        if goal_status in REVIEWED_GOAL_STATUSES:
            unreviewed = [
                name
                for name in REVIEW_COMPLETION_FIELDS
                if self.goal_fields.get(name, "none") == "none"
            ]
            if unreviewed:
                self.error(
                    "Goal status '{}' requires Gate D review; '## Review' still has "
                    "'none' for: {}.".format(goal_status, ", ".join(unreviewed))
                )
        if goal_status == "blocked-on-human" and "needs-human" not in statuses:
            blockers = self.goal_fields.get("Blockers", "none")
            if blockers == "none":
                self.warn("Goal is blocked-on-human but no phase or Handoff blocker records why.")
        if goal_status == "executing" and not ongoing_phases:
            self.warn("Goal is executing but no phase is currently ongoing; this is valid only at a phase boundary.")

    def git(self, *args):
        try:
            return subprocess.run(
                ["git", "-C", str(self.root)] + list(args),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
        except OSError:
            if not self.git_unavailable:
                self.error("git is unavailable; run with --no-git or install git.")
                self.git_unavailable = True
            return None

    def validate_git_fields(self):
        repository = self.goal_fields.get("Repository")
        strategy = self.goal_fields.get("Strategy")
        goal_status = self.goal_fields.get("Goal status")
        git_state_fields = (
            "Starting branch",
            "Work branch",
            "Baseline commit",
            "Starting upstream at start",
            "Work upstream at start",
        )
        if repository == "no":
            if strategy != "none":
                self.error("Repository no requires Strategy none.")
            for name in git_state_fields:
                if self.goal_fields.get(name) != "-":
                    self.error("Repository no requires '{}' to be '-'.".format(name))
            return
        if repository != "yes":
            return
        if strategy == "none":
            if goal_status not in ("drafting", "approved", "abandoned"):
                self.error("Goal status '{}' cannot use Strategy none.".format(goal_status))
            for name in git_state_fields:
                if self.goal_fields.get(name) != "-":
                    self.error("Unprepared Git strategy requires '{}' to be '-'.".format(name))
            return
        if strategy not in ("isolated-branch", "current-branch"):
            self.error("Unknown Git strategy '{}'.".format(strategy))
            return
        baseline = self.goal_fields.get("Baseline commit")
        if not baseline or not FULL_SHA_RE.fullmatch(baseline):
            self.error("Prepared Git strategy requires a full immutable Baseline commit.")
        for name in ("Starting branch", "Work branch"):
            if self.goal_fields.get(name) in (None, "", "-"):
                self.error("Prepared Git strategy requires '{}'.".format(name))
        for name in ("Starting upstream at start", "Work upstream at start"):
            upstream = self.goal_fields.get(name)
            if upstream != "none" and (not upstream or not UPSTREAM_RE.fullmatch(upstream)):
                self.error(
                    "Prepared Git strategy requires '{}' as <ref>@<full SHA> or none.".format(name)
                )

    def validate_git(self):
        repository = self.goal_fields.get("Repository")
        strategy = self.goal_fields.get("Strategy")
        goal_status = self.goal_fields.get("Goal status")
        baseline = self.goal_fields.get("Baseline commit")
        if repository != "yes":
            return

        inside = self.git("rev-parse", "--is-inside-work-tree")
        if inside is None:
            return
        if inside.returncode != 0:
            self.error("GOAL.md says Repository yes, but the project is not in a readable Git worktree.")
            return
        head = self.git("rev-parse", "--verify", "HEAD")
        if head.returncode != 0:
            self.error("Git repository has no initial commit; create or authorize a baseline commit before Gate B.")
            return

        if strategy == "none":
            if goal_status == "approved":
                self.warn("Goal is approved but Git preparation has not completed yet.")
            return
        if strategy not in ("isolated-branch", "current-branch"):
            return
        if not baseline or not FULL_SHA_RE.fullmatch(baseline):
            return
        exists = self.git("cat-file", "-e", "{}^{{commit}}".format(baseline))
        if exists.returncode != 0:
            self.error("Baseline commit '{}' does not exist.".format(baseline))
            return
        ancestor = self.git("merge-base", "--is-ancestor", baseline, "HEAD")
        if ancestor.returncode != 0:
            self.error("Baseline commit is not an ancestor of HEAD.")

        branch = self.git("symbolic-ref", "--quiet", "--short", "HEAD")
        current_branch = branch.stdout.strip() if branch.returncode == 0 else "(detached)"
        work_branch = self.goal_fields.get("Work branch")
        if work_branch not in (None, "", "-") and current_branch != work_branch:
            self.warn("Current branch '{}' differs from Work branch '{}'.".format(current_branch, work_branch))

        log = self.git("log", "--format=%H%x1f%B%x1e", "{}..HEAD".format(baseline))
        if log.returncode != 0:
            self.error("Could not inspect commits after baseline: {}".format(log.stderr.strip()))
            return
        goal_id = self.goal_fields.get("Goal ID", "")
        for record in log.stdout.split("\x1e"):
            record = record.strip()
            if not record:
                continue
            parts = record.split("\x1f", 1)
            commit = parts[0]
            message = parts[1] if len(parts) == 2 else ""
            subject = message.splitlines()[0] if message else ""
            trailer_ids = re.findall(r"(?m)^Goal-ID: (.+)$", message)
            if subject.startswith("goal-ledger(") and goal_id not in trailer_ids:
                self.error("Framework commit {} lacks matching Goal-ID trailer.".format(commit[:12]))
            elif trailer_ids and goal_id not in trailer_ids:
                self.warn("Commit {} carries a foreign Goal-ID.".format(commit[:12]))
            elif not trailer_ids:
                self.warn("Commit {} is foreign to this goal and can prohibit squashing.".format(commit[:12]))
            phase_trailers = re.findall(r"(?m)^Goal-Phase: (phase-\d{4})$", message)
            for phase_id in phase_trailers:
                if phase_id not in self.phase_data:
                    self.error("Commit {} references unknown {}.".format(commit[:12], phase_id))

    def result(self):
        return {
            "valid": not self.errors,
            "errors": self.errors,
            "warnings": self.warnings,
            "phases": len(self.phase_data),
        }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Project root containing .goal-ledger")
    parser.add_argument("--no-git", action="store_true", help="Skip live Git repository checks")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = parser.parse_args(argv)

    validator = LedgerValidator(args.root, check_git=not args.no_git)
    result = validator.validate()
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        for message in result["errors"]:
            print("ERROR: {}".format(message))
        for message in result["warnings"]:
            print("WARNING: {}".format(message))
        if result["valid"]:
            print("Goal Ledger valid ({} phases, {} warnings).".format(result["phases"], len(result["warnings"])))
        else:
            print("Goal Ledger invalid ({} errors, {} warnings).".format(len(result["errors"]), len(result["warnings"])))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
