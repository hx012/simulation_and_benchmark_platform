# Chip Performance Analysis

Independent, platform-agnostic performance analysis algorithms.

The package intentionally has no FastAPI, database, task-model, or filesystem-policy dependencies. Platform adapters validate access to task artifacts or uploaded files and then call this package directly.

Current capability:

- Trace time analysis for MSKPP traces.
- Trace time analysis for ESL traces.
