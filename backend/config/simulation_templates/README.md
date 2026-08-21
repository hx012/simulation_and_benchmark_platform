# Simulation Samples

The repository includes an editable V310 single-chip sample for local UI development:

```text
config/simulation_templates/v310/default/single_chip/
├── chip_config/
│   ├── simulator_config.yml
│   └── daw_config.yml
└── workload/
    └── workload.yml
```

The platform copies these files into each user's UploadSession when "Load current sample" is selected. The source files remain unchanged.

To install or replace a validated runtime input package, run:

```bash
uv run python scripts/seed_simulation_sample.py \
  --source ../runtime/SIM-V310-RUN-002/input \
  --simulator-version v310 \
  --chip-variant default \
  --simulation-mode single_chip
```

The installation layout is:

```text
config/simulation_templates/v310/default/single_chip/
├── chip_config/
└── workload/
```

The Backend still accepts the legacy `config/simulation_templates/v310/sample/` layout as a fallback for existing V310 installations.
