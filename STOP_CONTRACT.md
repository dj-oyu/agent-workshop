# Persistent stop

`stop` decisions from bridge/adaptive persist `control.stopped` in state. Later `run`, adaptive cycles, and restored checkpoints cannot run actions while it is true. A bridge `continue` or `revise` cannot clear it. `resume` only displays a brief; it never unpauses.

Explicit operator commands:

```
python3 loop.py stop state.json --note 'observed stopping condition'
python3 loop.py unpause state.json --note 'reason the stopping condition is now resolved'
```

Unpause does not grant permissions, replay unknown effects, or change task statuses. Reconciliation still requires a trusted read-only/idempotent verifier. Stop and unpause use the state lock. Stop does not cancel a currently executing command or an already-submitted external job; such operations need their own cancellation/reconciliation adapter. A busy state refuses control changes rather than pretending cancellation occurred.

Regression tests: a bridge stop survives a fresh process; continue cannot unpause; explicit unpause permits pending work; adaptive stop prevents the second action and subsequent planner invocation; checkpoint restore preserves the stopped state.
