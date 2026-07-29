# Goal Ledger repository instructions

Follow the
[Portable Agent Authoring](https://github.com/jpbaking/portable-agent-authoring)
guides for every skill or harness change.

- Edit skills only under `.agents/skills/`.
- Regenerate `.claude/skills/` as byte-identical full-directory mirrors.
- Keep `.clinerules/workflows/` files as thin invocation shims.
- Keep the distributable self-gating rule in
  `rules/shared/goal-ledger.md`; load it through one pointer per host.
- Keep planner/executor ownership and Git safety consistent across all five
  skills.
- Run `python3 -m unittest discover -s tests -v` after changing the ledger
  validator or its contract.
