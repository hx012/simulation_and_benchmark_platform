# Simulation Samples

Runtime sample assets are intentionally not bundled here. Install a validated input package with:

```bash
python scripts/seed_simulation_sample.py \
  --source ../runtime/SIM-V310-RUN-002/input \
  --simulator-version v310
```

The resulting layout is:

```text
config/simulation_templates/v310/sample/
├── chip_config/
└── workload/
```

The platform copies this sample into each user's UploadSession before editing. The source sample remains unchanged.
