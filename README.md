# Orca Task Coordinator

An English agent skill for delegating independent tasks to autonomous Poteto sessions in ordinary Orca worktrees.

Before launch, the coordinator establishes goals, scope, authorization, dependencies, and resource ownership. After startup, Poteto owns execution. One read-only monitoring subagent observes each independent task. The coordinator answers only explicit questions from the executor and summarizes returned results without adding another review or acceptance loop.

Existing project rules, user stop/change instructions, permissions, CI requirements, and release protections still apply. A returned report is not independent verification.

## Install

Copy `skills/orca-task-coordinator` into your Codex skills directory (usually `~/.codex/skills/`). Keep the runtime scripts together. Start a new session and invoke `$orca-task-coordinator`.

The skill requires a working Orca installation, a registered Git repository, an installed executor, Python 3.9+, and a separately installed `pstack:poteto-mode`. This repository does not bundle Poteto or Orca. Use the target project's own rules and installed tool documentation.

## Workflow

1. Prepare complete task briefs and establish shared-file ownership.
2. Launch independent ordinary worktrees/sessions concurrently.
3. Confirm actual assistant activity, not just accepted input.
4. Monitor read-only; forward explicit questions to the main agent.
5. Answer the question within existing authorization, then return to monitoring.
6. Receive results and report scope, evidence, failures, and limitations honestly.

When monitor capacity is limited, queue monitors or let the main agent temporarily observe read-only. Execution sessions can still run independently. Silence, slow progress, red CI, and missing steps are reportable facts, not automatic steering triggers.

## Launcher and validation

See [the launcher contract](skills/orca-task-coordinator/references/launcher-contract.md) for arguments, model selection, baseline branches, logs, and observation semantics. The launcher's historical Claude default is not a recommendation; explicitly pass the user's configured model label. Non-main repositories can select `--base-branch`.

```sh
python3 -B -m unittest discover -s skills/orca-task-coordinator/scripts -p 'test_*.py'
```

Tests use temporary directories and mocked subprocesses. They do not start Orca sessions or prove live end-to-end behavior.
