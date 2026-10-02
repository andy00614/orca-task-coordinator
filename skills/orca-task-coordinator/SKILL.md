---
name: orca-task-coordinator
description: Delegate independent tasks across projects to autonomous Poteto sessions in ordinary Orca worktrees. Assign a read-only monitor per task, answer only explicit executor questions, and summarize returned results. Use for parallel delegation, startup, monitoring, and handoff; do not add a second execution or acceptance workflow.
---

# Orca Task Coordinator

The main agent establishes goals, scope, authorization, and resource ownership before launch. Poteto owns execution; each independent task has one read-only monitoring subagent. After actual startup, an explicit question from Poteto requesting an answer is the only trigger for autonomous coordinator intervention.

## Prepare the task

- Use the user's selected, available machine. Verify its identity, registered Orca repository ID, checkout, and worktree before writes; do not substitute historical paths or another machine.
- Read the installed Orca skill and current CLI schema. Use ordinary worktrees and sessions by default; orchestration dispatch adds another protocol and is used only when explicitly requested and supported.
- Inspect dirty files without overwriting, resetting, or silently stashing them. Select the authorized base branch, fetch safely, and record its immutable SHA. A moving branch name is not evidence of the launch baseline.
- Read the target project's AGENTS.md / CLAUDE.md and applicable module, path rules, and task documentation. Discover the actual structure; `.agents/modules/` is optional.
- Split independent concerns into separate tasks, worktrees, and sessions. Establish ownership or dependency order for shared files and resources before launch. Group PRs by whether they can be reviewed, deployed, and rolled back independently.
- Give Poteto the complete problem and readable attachments, not an inaccessible document link or item number. Clarify missing goals or authorization; leave investigation details to the executor. Other independent tasks can proceed.
- Use the [task brief](references/routing-brief.md). Preserve the user's original task; do not append implementation plans, test matrices, acceptance checklists, or internal subagent requirements. Code work defaults to PR-ready without merging; other work follows the requested deliverable. Preserve existing authorization and ready/draft requirements.

## Launch independent tasks

- Use bundled `scripts/launch_task.py` and its sibling `startup_bench.py` as documented in the [launcher contract](references/launcher-contract.md). Verify both are readable on the selected machine; cloud visibility does not imply local installation.
- Load the installed `pstack:poteto-mode` by name in each session. If unavailable, locate a legitimately readable installation; report absence rather than pretending it loaded.
- Use the user's selected agent/model or the established configuration. Do not turn benchmark settings into permanent preferences or guess model menu labels. The helper's historical defaults are not user preferences.
- Start independent calls concurrently; do not wait for one task's full collection window before launching the next. Record task name, worktree, branch, baseline SHA, session/terminal handle, model, log directory, and ownership. Never borrow or release user-owned terminals.
- An accepted send only proves delivery. Observe a real assistant reply or tool activity for that task before claiming it started. Before confirmed startup, use bounded troubleshooting and the documented same-request observation mechanism. After startup, do not resend tasks.
- If creation has an unknown outcome, inspect matching resources and real handles before any retry. Do not duplicate worktrees or sessions. A bounded startup wait expiring is neither completion nor a reason to clean unrelated logs.

## Monitor without steering

- Poteto owns investigation, design, implementation delegation, independent review, tests, verification, PRs, and CI under its current skill and project rules. The outer coordinator does not audit its process, add tests, or run another acceptance pass.
- Assign one read-only monitoring subagent per independent task; give it real resource identities, baseline SHA, original task, and log directory. Prefer events or incremental cursors. If monitoring capacity is unavailable, disclose it and queue monitors or temporarily observe read-only from the main agent; this does not take over execution. See [monitor boundaries](references/failures-and-evidence.md#read-only-monitors).
- Monitors report meaningful changes, explicit questions, returned results, failures, and blockers. Slow progress, silence, red CI, missing steps, and different implementation choices are not intervention triggers. Do not nudge, redesign, reject results, request extra steps, retry CI, rebuild execution sessions, or assign extra reviewers.
- Only the main agent answers Poteto's explicit question, limited to that question and existing authorization. Monitors forward it without answering or messaging the executor. Ask the user only for a necessary unresolved decision or authorization. See [question handling](references/failures-and-evidence.md#answer-only-explicit-questions).
- Receive final reports, PRs/commits, verification scope, failures, and unknowns as returned. Do not label executor reports as outer independent verification or proactively demand continuation. Use the [handoff checklist](references/completion-checklist.md).
- Follow later explicit user changes or stop instructions. This skill grants no additional merge, deployment, Production write, permission, or cleanup authority; existing specific authorization need not be requested again.
- Read-only monitors never close terminals, delete worktrees, kill processes, or maintain Git. Separately authorized cleanup uses exact task-owned paths/PIDs/IDs, never global prune/gc or other people's resources. See [quality ownership](references/quality-and-efficiency.md).
