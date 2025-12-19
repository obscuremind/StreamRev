# StreamRev Scripts

This directory contains utility scripts for managing StreamRev.

## Available Scripts

### backup.sh
Backs up the database and configuration files.

```bash
sudo bash scripts/backup.sh
```

Features:
- Database backup to compressed SQL file
- Configuration files backup
- Automatic cleanup of old backups (30 days retention)
- Creates backups in `/backup/streamrev/`

### restore.sh
Restores the database from a backup file.

```bash
sudo bash scripts/restore.sh /backup/streamrev/db_20241219_120000.sql.gz
```

Features:
- Restores database from compressed backup
- Safety confirmation before restore
- Automatic service restart

### monitor.sh
Monitors the health of StreamRev services.

```bash
bash scripts/monitor.sh
```

Checks:
- Service status (MariaDB, Redis, Nginx, StreamRev)
- Port accessibility
- Disk usage
- Memory usage
- API health endpoint
- Recent error logs

### update.sh
Updates StreamRev to the latest version.

```bash
sudo bash scripts/update.sh
```

Features:
- Automatic backup before update
- Git pull latest changes
- Python dependencies update
- Database migrations
- Service restart

### migrate.py
Database migration management tool.

```bash
# Check migration status
python3 scripts/migrate.py status

# Run pending migrations
python3 scripts/migrate.py migrate

# Create new migration
python3 scripts/migrate.py create add_new_feature
```

## Automation

### Cron Jobs

Add to crontab for automated tasks:

```bash
# Daily backup at 2 AM
0 2 * * * /opt/streamrev/scripts/backup.sh

# Hourly health check
0 * * * * /opt/streamrev/scripts/monitor.sh
```

### Systemd Timers

Alternative to cron, using systemd timers:

```ini
# /etc/systemd/system/streamrev-backup.timer
[Unit]
Description=StreamRev Daily Backup

[Timer]
OnCalendar=daily
OnCalendar=02:00
Persistent=true

[Install]
WantedBy=timers.target
```

```ini
# /etc/systemd/system/streamrev-backup.service
[Unit]
Description=StreamRev Backup Service

[Service]
Type=oneshot
ExecStart=/opt/streamrev/scripts/backup.sh
```

Enable timer:
```bash
sudo systemctl enable streamrev-backup.timer
sudo systemctl start streamrev-backup.timer
```

## Script Permissions

All scripts should be executable:

```bash
chmod +x scripts/*.sh
chmod +x scripts/*.py
```

## Environment Variables

Scripts use configuration from:
- `/opt/streamrev/config.json`
- Environment variables
- `/root/.streamrev_db_password`

## Logging

Scripts log to:
- Standard output
- Systemd journal (for systemd services)
- `/var/log/streamrev/` (application logs)

View logs:
```bash
journalctl -u streamrev -f
tail -f /var/log/streamrev/app.log
```
