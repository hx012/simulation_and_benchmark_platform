# Simulation Samples

The repository keeps one shared template per simulation topology. Every
simulator version and chip variant loads from the same mode directory:

```text
config/simulation_templates/default/
├── single_chip/
│   ├── chip_config/
│   └── workload/
└── multi_chip/
    ├── chip_config/
    └── workload/
```

The platform chooses only by `simulation_mode`, then copies the shared files
into the user's UploadSession when "载入配置样例" is selected. The selected
Simulator Version and Chip Variant do not change the template source.

To install or replace a validated runtime input package, run:

```bash
uv run python scripts/seed_simulation_sample.py \
  --source ../runtime/SIM-V310-RUN-002/input \
  --simulation-mode single_chip
```

The installation layout is:

```text
config/simulation_templates/default/single_chip/
├── chip_config/
└── workload/
```

The task creation page exposes the selected template as a ZIP download. The
archive keeps the upload-ready top-level directories:

```text
chip_config/
workload/
```

Configure the **MSKPP 使用指南** button with `mskpp_guide_url` in the active
`SIMULATOR_PROFILES_FILE`. Internal paths and `http(s)` URLs are supported; an
empty value keeps the button disabled.
