# Orca Task Coordinator

[English](README.md) | [简体中文](README.zh-CN.md)

Delegate independent tasks to autonomous Poteto sessions in ordinary Orca worktrees. Supports Codex and Claude Code.

Before launch, the coordinator establishes goals, scope, authorization, dependencies, and resource ownership. After startup, Poteto owns execution. One read-only monitoring subagent observes each independent task. The coordinator answers only explicit questions from the executor and summarizes returned results without adding another review or acceptance loop.

Existing project rules, user stop/change instructions, permissions, CI requirements, and release protections still apply. A returned report is not independent verification.

## Install

Install with the [skills CLI](https://skills.sh/docs):

```sh
npx skills add andy00614/orca-task-coordinator --skill orca-task-coordinator
```

Select Codex or Claude Code and your project/global installation scope when prompted.

For a global Codex installation:

```sh
npx skills add andy00614/orca-task-coordinator --skill orca-task-coordinator --agent codex --global
```

For a global Claude Code installation:

```sh
npx skills add andy00614/orca-task-coordinator --skill orca-task-coordinator --agent claude-code --global
```

Alternatively, copy `skills/orca-task-coordinator` into the corresponding skills directory: usually `~/.codex/skills/` for Codex or `~/.claude/skills/` for Claude Code. Keep the runtime scripts together. Start a new session and invoke `$orca-task-coordinator` in Codex or `/orca-task-coordinator` in Claude Code.

The skill requires a working Orca installation, a registered Git repository, an installed Codex or Claude Code executor, Python 3.9+, and a separately installed [`pstack:poteto-mode`](https://github.com/michael-denyer/pstack-claude#install). This repository does not bundle Poteto or Orca. If a dependency is missing, the agent reports it and provides installation guidance rather than installing automatically. Use the target project's own rules and installed tool documentation.

pstack supports both Codex and Claude Code; follow its [upstream installation instructions](https://github.com/michael-denyer/pstack-claude#install) for your agent. The Orca launcher uses `--agent codex` or `--agent claude`; the skills CLI uses `claude-code` as the Claude Code installation identifier.

## Workflow

![Five autonomous Poteto tasks with separate read-only monitors and question-only coordinator replies](docs/assets/workflow.png)

Each Poteto session owns one independent task in its own worktree. Each monitor is a separate read-only subagent. The main agent replies only to explicit questions, asks the user when a decision is required, and summarizes returned results without an additional acceptance pass.

**Slow progress, silence, red CI, and missing steps are reported, not used to steer execution.** No nudging, extra acceptance loop, or automatic rework.

When monitor capacity is limited, queue monitors or let the main agent temporarily observe read-only. Execution sessions can still run independently. Existing authorization, project rules, and release protections remain in force.

## Launcher and validation

See [the launcher contract](skills/orca-task-coordinator/references/launcher-contract.md) for arguments, model selection, baseline branches, logs, and observation semantics. The launcher's historical Claude default is not a recommendation; explicitly pass the user's configured model label. Non-main repositories can select `--base-branch`.

```sh
python3 -B -m unittest discover -s skills/orca-task-coordinator/scripts -p 'test_*.py'
```

Tests use temporary directories and mocked subprocesses. They do not start Orca sessions or prove live end-to-end behavior.
