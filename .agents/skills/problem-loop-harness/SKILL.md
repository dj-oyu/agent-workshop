---
name: problem-loop-harness
description: Build and resume evidence-driven problem-solving loops for multi-step work, stalled tasks, external jobs, or work that must survive interruption. Use when durable state, adaptive replanning, and verified completion are needed, not for a one-off factual answer.
---

# Problem Loop Harness

Turn the user's outcome into an executable, resumable loop rather than a one-shot checklist. The scripts in this skill directory provide state and evidence handling; you provide reasoning and authorized tools. Resolve script paths relative to this SKILL.md, not the case working directory.

## Begin or resume

- Read [PLAYBOOK.md](PLAYBOOK.md) for loop design. Establish the outcome and evidence that would prove it, then inspect current work before assigning new owners or repeating actions.
- Keep each case's plan, state, inputs, logs, and outputs in a private workspace outside the skill checkout. `init` uses the plan's parent as the command working root; put plan and state together there.
- For a new case, use the schema and CLI in [README.md](README.md), with `example.json` only as a synthetic template. Choose bounded commands and meaningful verification for this task. Do not run the example over existing files.
- For an existing case, use `sh <skill-dir>/restore.sh <case>/state.json` to inspect evidence, blockers, and next work. This displays state; it does not execute or unpause it.

## Close the feedback loop

Execute a bounded step, inspect its actual result, test the current hypothesis, and choose the next step. When a step stalls, identify an observation that distinguishes causes; revise the plan rather than retrying unchanged work. Continue independent authorized work while another step waits. Close stages using verified outcomes, not an agent's completed turn or a sent instruction.

Use [CONNECTORS.md](CONNECTORS.md) and `bridge.py` to exchange an evidence-bound request/decision with the available reasoning agent. Verify scope before accepting commands. The `authorized` field is a record, not permission or a sandbox. Unknown side effects require reconciliation before any resend; `reconcile` runs the verifier only, so its verifier must itself be safe and authorized.

For long waits, bind the case to an actually available durable scheduler/event system. Save its accepted job/wake ID, what state to inspect, next action, notification threshold, and termination condition. Do not call a wake configured until registration succeeds. If no scheduler is available, explicitly retain that gap rather than claiming autonomous continuation. This package does not implement an external scheduler.

## Stop, preserve, and restore

Read [STOP_CONTRACT.md](STOP_CONTRACT.md) for persistent stop/unpause. A stopped loop is not permission to auto-unpause. Stop prevents future steps; it does not cancel an in-flight external job.

Use `checkpoint.py` as documented in [README.md](README.md) when moving environments. Export only explicitly selected case files to an authorized private destination. Restored completed steps become unknown until verification; do not replay their actions. Checkpoint hashes detect corruption, not trusted provenance.

Keep public code and private case checkpoints separate. Save and read back each through its authorized storage, recording the tested revision. Finish only when the user outcome is verified or the exact remaining blocker, owner, evidence, and next action are preserved. Skill installation alone neither starts a daemon nor guarantees future wakes.
