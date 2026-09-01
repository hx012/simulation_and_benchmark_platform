# Simulation Samples

Template locations are configured per entry in `simulator_profiles.yml`:

```yaml
chip_config_template_path: simulation_templates/chip_configs/v310/default/single_chip
workload_template_path: simulation_templates/default/single_chip/workload
```

Relative paths are resolved from the directory containing the active
`simulator_profiles.yml`; absolute paths are also supported for server-local
deployments. Chip Config paths are independent per chip profile today. A path
may be shared later without changing application code. Workload templates can
already be reused by multiple chip profiles.

The repository example layout is:

```text
config/simulation_templates/default/
├── single_chip/
│   └── workload/
└── multi_chip/
    └── workload/
config/simulation_templates/chip_configs/
├── v310/default/single_chip/
└── v320/
    ├── default/single_chip/
    ├── default/multi_chip/
    └── high_perf/multi_chip/
```

When an upload session is created, the selected profile's Chip Config is copied
into the session automatically. Ordinary users can preview it but cannot edit
or replace it. Advanced users and administrators can edit/replace Chip Config
and download the combined Chip Config + Workload template ZIP.

To install or replace a validated runtime input package, run:

```bash
uv run python scripts/seed_simulation_sample.py \
  --source ../runtime/SIM-V310-RUN-002/input \
  --chip-config-target config/simulation_templates/chip_configs/v310/default/single_chip \
  --workload-target config/simulation_templates/default/single_chip/workload
```

After installing files, point the relevant profile paths at the resulting Chip
Config and Workload directories. Different profiles can reference the same
Workload directory.

The task creation page exposes the selected template as a ZIP download to
advanced users and administrators. The
archive keeps the upload-ready top-level directories:

```text
chip_config/
workload/
```

Configure the **MSKPP 使用指南** button with `mskpp_guide_url` in the active
`SIMULATOR_PROFILES_FILE`. Internal paths and `http(s)` URLs are supported; an
empty value keeps the button disabled.
