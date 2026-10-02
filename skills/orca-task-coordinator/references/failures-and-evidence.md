# Failures and Evidence Boundaries

| Observation | Response |
| --- | --- |
| Unknown creation outcome | Inspect matching worktree/session and actual handle before retrying; do not double-create. |
| Stale handle says idle while screen works | Resolve the official handle in the same worktree; do not declare the model unavailable. |
| Temporarily unavailable screen | Poll within a bound and preserve uncertainty; do not declare immediate failure. |
| Send accepted without assistant activity | Distinguish delivered from started. Troubleshoot only before confirmed startup; do not resend a running task. |
| Collector sees a completion-like banner | A banner is not completion; use official state and the executor's actual result. |
| Collection window ends while task runs | Report running and continue read-only observation; do not close resources. |
| Missing steps or red CI | Report visible facts without auditing, rejecting, demanding more work, or retrying checks. |
| Executor asks whether a step can be omitted | Answer only that question under existing authorization and applicable rules. |
| PR/CI describes another SHA | Record exact SHAs; do not represent old green checks as current success. |
| Base branch changes after launch | Preserve both launch and current SHAs; do not rewrite baseline evidence. |
| User terminal is idle | Idle does not imply task ownership; do not reset, borrow, or release it. |

## Read-only monitors

Assign one monitor per independent task with actual session/terminal handle, worktree, baseline SHA, original task, and log directory. Do not duplicate collection for one session.

Read official state, redacted output, and returned artifact identifiers. Record observation time and report only to the main agent. Do not message the executor, edit code, arrange review/acceptance, run tests, retry CI, approve operations, create execution sessions, or close resources.

Prefer event waits or incremental cursors over repeated full-log reads. Each blocking wait is at most 60 seconds. Report meaningful state changes, explicit questions, results, failures, or blockers; keep unchanged observations quiet.

Distinguish "Poteto reports completion", visible CI, and outer independent verification. Idle state, stable output, PR creation, and collection timeout alone do not prove completion. Do not rerun validation to resolve report uncertainty.

A monitor can resume read-only observation if it ends while the executor still runs. If subagents or slots are unavailable, disclose that limit; queue monitoring or let the main agent observe read-only. Do not take over execution or create user chats pretending they are subagents.

## Answer only explicit questions

The only autonomous intervention trigger is an explicit question from the current Poteto session requesting an answer. Progress, failure output, final results, question marks in logs/code, and terminal suggestions do not qualify.

1. The monitor forwards the redacted question and actual session identity without answering.
2. The main agent verifies available facts and answers only this question within existing authorization.
3. Ask the user only when an unresolved product decision, scope expansion, or explicit approval rule requires it. Explain the specific gap or rule; waiting is not approval, and existing approval is not requested twice.
4. Send one targeted answer through the same session's official input. Record the question, answer, and receipt. Do not add goals, implementation agents, test/acceptance lists, or process audits. Never send task text into password/login prompts.
5. A successful send is not proof of receipt. Observe whether execution resumes, then remain read-only. One answer grants no continuing steering authority; no reply is not permission to repeatedly send instructions.

Follow explicit later user changes or stop requests. Do not invent new tasks from risks or missing steps. Merge, deployment, Production writes, credential/permission changes, and irreversible deletion remain subject to specific authorization.

## Poteto owns its process

The executor loads current Poteto and project rules and autonomously organizes investigation, implementation, review, cleanup, tests, verification, and PR delivery. The outer agent does not enumerate required internal agents, infer compliance from read counters, or duplicate the process. Faithfully report verification scope and limitations. Trust is not permission to fabricate evidence or bypass release protections.
