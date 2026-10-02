# Local Launcher Contract

## Package and dependencies

- `scripts/launch_task.py`: ordinary task startup and bounded read-only collection.
- `scripts/startup_bench.py`: shared startup probe. Its separate benchmark CLI runs only when explicitly requested.
- `scripts/test_launch_task.py` and `scripts/test_packaging.py`: offline tests with mocked processes; no live Orca calls.

Keep both runtime scripts together on the user's selected machine. Verify the actual installation and registered repository; visibility from a cloud task does not imply local availability. Dependencies are Python 3.9+, the standard library, Orca CLI/runtime, Git, a registered repository, and an installed executor. Python tests do not prove a live task launch.

| Parameter | Contract |
| --- | --- |
| `--name`, `--fetch-worktree` | Required: unique task name and verified checkout path. |
| `--repo-id` | Required: actual registered repository ID, no private default. |
| `--prompt-file` / `--prompt-text` | Exactly one; sends the task unchanged without a benchmark nonce. |
| `--base-branch` | Origin branch name, default `main`; e.g. `master` or `staging`, without `origin/`. |
| `--agent` | `claude` or `codex`; helper default is `claude`. |
| `--model` | Claude exact current menu label; helper historical default is `Sonnet 5.5`. Codex accepts only `configured`. Select based on the user/configuration, not this default. |
| `--user-start-utc` | Optional timezone-aware request timestamp for end-to-end timing. |
| `--log-dir` | Optional new directory outside the skill; default `~/.local/state/orca-task-coordinator/<name>-logs`. |
| `--collect-seconds` | Default 900, range 0–900. |
| `--poll-seconds` | Default 120, range 1–120. |

```sh
python3 "$SKILL_DIR/scripts/launch_task.py" \
  --name '<unique-task-name>' \
  --repo-id '<actual-registered-repo-id>' \
  --fetch-worktree '<verified-checkout-path>' \
  --base-branch '<authorized-origin-branch>' \
  --agent claude --model '<configured-current-menu-label>' \
  --prompt-file '<readable-complete-task-file>' \
  --collect-seconds 900 --poll-seconds 120
```

Replace placeholders with observed values. For Codex use `--agent codex --model configured`. Prefer prompt files or reliable argument passing over fragile shell escaping. Preserve established model/effort settings.

## Startup and observation

The helper fetches the selected branch, resolves its SHA, creates an ordinary worktree from that branch, and checks that HEAD matches the fetched SHA before sending. This preserves the existing baseline consistency check for non-main projects. Unknown creation outcomes are inspected rather than blindly recreated.

The main coordinator prepares calls; a transport task executes and returns them without another routing layer. Start independent calls concurrently rather than serializing 900-second collections. Current Orca CLI documentation governs handles, base-branch support, and menu selection; do not guess model slugs or menu keys.

Record real resource identities, the accepted request ID, and actual assistant activity separately. The helper observes the same submitted request without inventing another task. Permission/trust/login prompts are not automatically approved.

A collection window is not a task deadline. On expiry, preserve sessions and resources and continue read-only monitoring; send no continuation directive. Only a later explicit executor question triggers an answer.

## Receipts and evidence

Logs must be new and outside the skill. Existing logs/worktrees require inspecting actual state rather than rebuilding. `startup.json` records UTC/elapsed steps, selected base branch and SHA, resources, model, send receipt, and startup evidence. `terminal.jsonl` records source, time, cursor, and metadata; collection status/end files record observation outcome.

Output reports `STARTED` or `BLOCKED`, then `COLLECTED` after collection. Startup failure exits nonzero. Exit zero after startup and collection labels such as `blocked`, `unknown`, or `awaiting_parent_review` do not mean task completion, successful verification, or permission for outer review/rework.

The helper does not merge, deploy, edit PRs, close terminals, or delete worktrees. After collection, the read-only monitor remains responsible for observation. Preserve missing evidence rather than filling it in as success.

## Timing and offline checks

Distinguish user request, delegation, local arrival, process start, creation, model selection, send, observed activity, and report. Record UTC plus local monotonic durations. Do not subtract monotonic clocks across machines. Only request-to-reply is end-to-end; unobserved stages stay unknown.

```sh
python3 -B -m unittest discover -s "$SKILL_DIR/scripts" -p 'test_*.py'
```

Offline tests cover import side effects, arguments, log protection, unknown creation, collection expiry, prompt preservation, branch selection, and timing with temporary directories and mocked processes. Do not launch a live task or benchmark merely to validate packaging.
