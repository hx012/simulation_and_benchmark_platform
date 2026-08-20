# AI Chip Simulation and Benchmark Platform - AI_CONTEXT

## 1. Project Overview

This project builds a unified AI chip simulation and Benchmark platform.

Main goals:

- Provide a web platform for AI chip simulator management.
- Support simulation task creation, execution, result collection and visualization.
- Support Benchmark data management and future performance comparison.
- Provide Trace based micro-architecture analysis capability.

## 2. System Architecture

### Frontend

Responsible for:

- User interaction.
- Simulation configuration.
- Task management UI.
- Result visualization.
- Benchmark presentation.

### Backend

Responsible for:

- Simulation task management.
- Simulator adapter.
- Runtime directory management.
- Result collection.
- Configuration management.

### Runtime

Each simulation task uses an independent runtime directory:

```
runtime/<job_id>/
    result/
    trace/
    logs/
```

This avoids conflicts between concurrent simulation tasks.

## 3. Simulation Capability

The platform supports:

- Multiple simulator versions.
- Multiple chip variants.
- Multiple simulation modes.
- Simulator profile based configuration.
- Workload and hardware configuration management.

Configuration entry:

```
backend/config/simulator_profiles.yml
```

## 4. Trace Visualization

Trace follows Chrome Trace Format.

Current direction:

- Generate trace.json from simulation.
- Use Chromium Catapult trace viewer.
- Reuse mature trace visualization instead of implementing a custom viewer.

Future support:

- Multiple trace comparison.
- Benchmark trace analysis.
- Timeline alignment.

## 5. Development Status

Completed:

- Basic simulation task workflow.
- Frontend/backend separation.
- Runtime isolation.
- Simulator profile design.
- Simulation version/chip variant/simulation mode selection.
- Trace generation verification.

In progress:

- Simulation result page enhancement.
- Trace viewer integration.
- Benchmark framework.

## 6. Development Principles

1. Keep simulator implementation independent from platform code.
2. Use adapters between platform and simulator engines.
3. Keep configurations externalized.
4. Prefer open-source mature visualization tools when possible.
5. Maintain documents together with implementation.

## 7. Future Roadmap

- Benchmark comparison.
- Multi-trace analysis.
- Performance regression analysis.
- AI-assisted development workflow.
