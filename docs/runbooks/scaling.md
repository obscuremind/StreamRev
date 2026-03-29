# Runbook: Scaling guidance

- Scale API workers by changing orchestrator `uvicorn --workers` setting.
- Offload watchdog/monitor to dedicated hosts by removing optional entries from the process plan and running them via cron/systemd.
- Use external Redis/MariaDB for multi-node deployments.
- Prefer reverse proxy/load balancer in front of Uvicorn for production TLS and buffering.

- Default orchestrator workers: `queue-worker`, `scheduler-worker`, `migration-worker` (all optional/non-critical).
