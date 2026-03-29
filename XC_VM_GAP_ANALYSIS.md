# XC_VM Parity Gap Analysis (StreamRev vs Vateron-Media/XC_VM)

Date: 2026-03-29

## Scope and method

This analysis compares the current StreamRev repository against `https://github.com/Vateron-Media/XC_VM` (default branch, shallow clone) at:

- Architecture and runtime layout
- Admin/Reseller/Player surface area
- CLI and cron coverage
- SQL schema parity
- Module and integration parity

## Executive summary

StreamRev already mirrors important **high-level domain areas** (streams, users, VOD, servers, EPG, lines, modules), but it is currently a **partial parity implementation** compared to XC_VM.

Most visible gaps are:

1. **UI and panel completeness gap** (controller/view count still much smaller)
2. **Reseller and player UX/API completeness gap**
3. **Database schema parity gap** (many XC_VM operational/logging tables absent)
4. **CLI/cron parity gap** (few commands implemented vs XC_VM set)
5. **Operational parity gap** (legacy compatibility endpoints/workflows still limited)

---

## Structural comparison (measured)

### 1) Controllers, views, commands

| Area | StreamRev | XC_VM | Gap |
|---|---:|---:|---:|
| Admin controllers | 42 | 118 | -76 |
| Reseller controllers | 2 | 30 | -28 |
| API controllers | 7 | 9 | -2 |
| Player controllers | 2 | 13 | -11 |
| Views/templates | 1 | 168 | -167 |
| CLI commands | 1 | 24 | -23 |
| Cron jobs | 1 | 21 | -20 |

Interpretation:
- Core building blocks exist, but panel depth and operational breadth are still far from XC_VM runtime expectations.

### 2) Admin feature-name overlap (normalized controller names)

- Approximate overlap: **19 shared areas**
- XC_VM-only areas still missing in StreamRev naming surface: **~99**

Examples missing from StreamRev parity set:
- `users`, `userlogs`, `streamlist`, `streammass`, `streamerrors`, `streamreview`
- `mag*`, `enigma*`, `watch*`, `plex*`, `theftdetection`
- `processmonitor`, `loginlog`, `mysqlsyslog`, `panel_logs`
- granular edit/list/sort flows for bouquets/series/movies/packages/providers/servers

### 3) SQL schema parity

- StreamRev schema tables: **33**
- XC_VM install schema tables: **64**
- Common table names: **19**
- Missing from StreamRev relative to XC_VM: **45** (by table-name comparison)

Notable missing operational tables:
- Activity/logging: `users_logs`, `users_credits_logs`, `lines_logs`, `login_logs`, `panel_logs`, `mysql_syslog`, `syskill_log`, `streams_logs`, `streams_errors`
- Streaming orchestration: `queue`, `signals`, `streams_servers`, `streams_stats`, `servers_stats`, `ondemand_check`
- Device/portal: `mag_events`, `mag_logs`, `mag_claims`, `output_devices`, `output_formats`
- Watch/recording: `watch_folders`, `watch_logs`, `watch_refresh`, `recordings`
- EPG structure: `epg`, `epg_channels`

---

## Key mismatches by domain

## A) Admin panel and UX parity

### Observed mismatch
XC_VM has a much richer page/controller matrix (list/edit/mass/review views per entity), while StreamRev currently exposes fewer endpoints and only one admin HTML view.

### Impact
- Migration users expecting one-to-one menu/workflow parity will hit missing pages and tools.
- Automation scripts relying on specific XC_VM admin routes may fail.

---

## B) Reseller and Player parity

### Observed mismatch
Reseller and player controller counts are still low in StreamRev compared to XC_VM.

### Impact
- High chance of broken reseller workflows (tickets, lines activity, profile editing, dashboard widgets).
- End-user/player web panel flow is likely incomplete for XC_VM-like deployments.

---

## C) Operations, observability, and logs

### Observed mismatch
XC_VM has dedicated logs/stats tables and dedicated controllers for diagnostics, syslogs, restream logs, stream error review, login logs, etc.

### Impact
- Troubleshooting and support workflows are weaker.
- Harder parity for NOC-like operations and reseller support teams.

---

## D) Queue/signal/process lifecycle parity

### Observed mismatch
StreamRev includes scaffolding but lacks full schema+workflow parity for XC_VM queue/signals/stat tracking.

### Impact
- Differences in restart/recovery behavior under load.
- Some background jobs cannot be ported directly from XC_VM ecosystem scripts.

---

## E) Module and ecosystem parity

### Observed mismatch
Module directories exist in StreamRev, but XC_VM has broader controller/data wiring around MAG, Enigma, Watch, Plex, and related admin/reseller pages.

### Impact
- Functional islands exist without full end-to-end operability.

---

## Prioritized TODO list

## P0 (critical parity blockers)

1. **Define parity target matrix** (route-level, DB-table-level, workflow-level) and freeze MVP parity scope.
2. **Close schema blockers first** for required operational tables (queue, signals, logs, streams_servers/stats, login/panel logs).
3. **Implement missing reseller core flows**: dashboard, users, lines, tickets, profile/session/logout.
4. **Implement missing player core flows**: login/logout, listings, live/movies/series/episodes, profile.
5. **Introduce compatibility route map** (aliases/redirects) for high-traffic XC_VM endpoints.

## P1 (high value)

6. **Expand admin list/edit/mass patterns** for streams, users, VOD, series/episodes, servers, providers, MAG/Enigma.
7. **Add observability pages + APIs** for stream errors, restream logs, login logs, mysql syslog, panel logs.
8. **Implement queue + signals execution pipeline** with robust retry and dead-letter behavior.
9. **Add cron parity set** for stream/user/server/cache/watch/recording maintenance.
10. **Increase CLI parity** to match XC_VM operational command surface (startup/watchdog/monitor/scanner/queue/migrations helpers).

## P2 (migration polish)

11. **Rebuild menu and view coverage** for admin/reseller/player parity (incremental feature flags acceptable).
12. **Implement MAG/Enigma deep features** (events, claims, logs, mass actions).
13. **Complete watch/recording workflows** (folders/categories/logs/refresh pipelines).
14. **Add migration checker command** to verify DB + endpoint + config parity against XC_VM baseline.
15. **Ship parity test suite**:
   - Endpoint contract tests
   - Schema conformance tests
   - Cron smoke tests
   - Playback/auth regression tests

---

## Suggested implementation sequence

1. Schema and data migration compatibility
2. Reseller/player minimum parity
3. Admin operations + logs + diagnostics
4. Queue/signals/cron hardening
5. UI/workflow completeness and migration tooling

This order minimizes production migration risk while progressively increasing visible panel parity.
