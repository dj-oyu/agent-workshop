# Portable checkpoint validation

- Original v0.2 archive checksum manifest passed; 9 existing tests passed.
- Prior-turn live-state was read in this fresh agent/process; resume did not replay the completed action (attempts stayed 2, artifact SHA and mtime unchanged).
- Added checkpoint.py and five tests; all 14 tests passed.
- Exported a synthetic two-stage job after stage 1. `pending-case.zip` contains one pending stage, one completed stage, explicit artifact, evidence logs and SHA256 manifest.
- Restored into a new directory. Prior done becomes unknown and blocks dependents. Explicit trusted read-only reconcile passed; then loop.py resumed. Only stage 2 action executed; completed stage attempts stayed 1; original workspace did not acquire stage 2 output.

Commands:

```
python3 checkpoint.py export path/to/state.json case.zip --include artifact.txt
python3 checkpoint.py restore case.zip new-case-directory
python3 loop.py reconcile new-case-directory/state.json --task completed-task --note "Trusted read-only revalidation of restored artifact"
python3 loop.py run new-case-directory/state.json
```

Limits: the archive is not authorization to execute its commands. Only trusted plans may run. Hashes detect corruption, not an attacker able to replace the manifest. Explicit includes are essential; arbitrary unlisted inputs are not captured. Scripts with embedded absolute original workspace paths are refused rather than rewritten. Active running state is refused at export. This does not add an external scheduler or prove continuous autonomous operation. Private operational checkpoints must remain separate from public code.

Independent review found the original restore wrongly retained done when artifacts were omitted. Fixed: every restored done becomes unknown until explicit verify-only reconciliation. Missing artifact regression confirms dependent remains pending and action is never replayed.
