# systemd integration

For a long-running Linux host, copy `ascend-platform.service.example` to
`/etc/systemd/system/ascend-platform.service`, then replace `CHANGE_ME` and every
`/path/to/simulation_and_benchmark_platform` value with the deployment user and
absolute repository path.

The service delegates lifecycle and safety checks to `scripts/platform.sh`:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ascend-platform.service
sudo systemctl status ascend-platform.service
```

The unit never removes PostgreSQL volumes. It is a convenient boot-time wrapper
for the single-host deployment. Environments that require independent restart
policies for Backend, Worker, and Frontend should split this template into
separate organization-managed units while keeping the same Compose database.
