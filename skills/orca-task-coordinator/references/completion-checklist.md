# Coordinator Handoff Checklist

This checks delegation, monitoring, and reporting, not another implementation or acceptance gate.

## Delegation and monitoring

- [ ] Original goal, scope, authorization, project rules, and necessary attachments were provided before launch.
- [ ] Machine, repository, worktree, actual session/terminal handle, and baseline SHA were recorded without overwriting user work.
- [ ] The bundled launcher was used; delivery and actual startup were recorded separately; independent tasks started concurrently.
- [ ] Each task has one read-only monitor, or monitoring limits were disclosed.
- [ ] Poteto executed autonomously without outer nudging, redesign, rework demands, repeated checks, or extra acceptance.
- [ ] Only explicit questions were answered; monitors forwarded questions without adding authority.

## Results and reporting

- [ ] Returned results, PR/commit, verification scope, failures, and unknowns were summarized honestly.
- [ ] Executor reports, visible state, and independent verification were distinguished; idle, timeout, and old-SHA CI were not called current success.
- [ ] Missing evidence or failure was disclosed without proactive rework or rebuilding the task.
- [ ] Explicit user changes/stops were followed; external writes remain governed by authorization and existing protections.
- [ ] Resource state came from actual results; read-only monitors closed nothing and touched no unrelated resources.
- [ ] Logs were redacted; timing labels were accurate; no unmeasured speedup was claimed.
