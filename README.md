# Orca Task Coordinator

An English agent skill for delegating independent tasks to autonomous Poteto sessions in ordinary Orca worktrees.

Before launch, the coordinator establishes goals, scope, authorization, dependencies, and resource ownership. After startup, Poteto owns execution. One read-only monitoring subagent observes each independent task. The coordinator answers only explicit questions from the executor and summarizes returned results without adding another review or acceptance loop.

Existing project rules, user stop/change instructions, permissions, CI requirements, and release protections still apply. A returned report is not independent verification.

## Install

Copy `skills/orca-task-coordinator` into your Codex skills directory (usually `~/.codex/skills/`). Keep the runtime scripts together. Start a new session and invoke `$orca-task-coordinator`.

The skill requires a working Orca installation, a registered Git repository, an installed executor, Python 3.9+, and a separately installed `pstack:poteto-mode`. This repository does not bundle Poteto or Orca. Use the target project's own rules and installed tool documentation.

## Workflow

### Five tasks, five read-only monitors

Each Poteto session owns one independent task in its own worktree. Each monitor is a separate subagent; dotted arrows represent read-only observation.

```mermaid
flowchart TB
    C("🧭 Main agent<br/>Define goals, scope & authorization")

    P1("🥔 Poteto 1")
    P2("🥔 Poteto 2")
    P3("🥔 Poteto 3")
    P4("🥔 Poteto 4")
    P5("🥔 Poteto 5")

    M1("👀 Monitor 1")
    M2("👀 Monitor 2")
    M3("👀 Monitor 3")
    M4("👀 Monitor 4")
    M5("👀 Monitor 5")

    R("📬 Main agent receives<br/>Progress · Questions · Results")

    C --> P1 & P2 & P3 & P4 & P5
    P1 -.-> M1
    P2 -.-> M2
    P3 -.-> M3
    P4 -.-> M4
    P5 -.-> M5
    M1 & M2 & M3 & M4 & M5 --> R

    classDef coordinator fill:#FFF0D9,stroke:#E7A34C,color:#513719,stroke-width:2px
    classDef executor fill:#FFF6CB,stroke:#D6B747,color:#51451E,stroke-width:2px
    classDef monitor fill:#E4F3FF,stroke:#79B5DF,color:#22465F,stroke-width:2px
    class C coordinator
    class P1,P2,P3,P4,P5 executor
    class M1,M2,M3,M4,M5,R monitor
```

### The feedback loop

Only an explicit question from Poteto triggers a reply. The answer goes back to the same session; execution remains autonomous.

```mermaid
flowchart TB
    E("📬 Update from a monitor") --> Q{"💬 Poteto explicitly<br/>asks for an answer?"}
    Q -->|Yes| A("🧭 Main agent answers only that question<br/>Ask the user if a decision is required")
    A --> P("🥔 Same Poteto session<br/>continues autonomously")
    P --> W("👀 Continue read-only monitoring")

    Q -->|No| D{"📦 Final result returned?"}
    D -->|No| W
    D -->|Yes| H("🌿 Receive & summarize<br/>Results, failures & limitations")

    classDef monitor fill:#E4F3FF,stroke:#79B5DF,color:#22465F,stroke-width:2px
    classDef decision fill:#EFE7FF,stroke:#B19AD9,color:#463465,stroke-width:2px
    classDef coordinator fill:#FFF0D9,stroke:#E7A34C,color:#513719,stroke-width:2px
    classDef executor fill:#FFF6CB,stroke:#D6B747,color:#51451E,stroke-width:2px
    classDef result fill:#E6F5E8,stroke:#87BA8D,color:#2C5132,stroke-width:2px
    class E,W monitor
    class Q,D decision
    class A coordinator
    class P executor
    class H result
```

**Slow progress, silence, red CI, and missing steps are reported, not used to steer execution.** No nudging, extra acceptance loop, or automatic rework.

When monitor capacity is limited, queue monitors or let the main agent temporarily observe read-only. Execution sessions can still run independently. Existing authorization, project rules, and release protections remain in force.

## Launcher and validation

See [the launcher contract](skills/orca-task-coordinator/references/launcher-contract.md) for arguments, model selection, baseline branches, logs, and observation semantics. The launcher's historical Claude default is not a recommendation; explicitly pass the user's configured model label. Non-main repositories can select `--base-branch`.

```sh
python3 -B -m unittest discover -s skills/orca-task-coordinator/scripts -p 'test_*.py'
```

Tests use temporary directories and mocked subprocesses. They do not start Orca sessions or prove live end-to-end behavior.
