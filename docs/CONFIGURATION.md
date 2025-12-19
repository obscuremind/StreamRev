# StreamRev Configuration Guide

This guide covers all configuration options for StreamRev.

## Configuration File

The main configuration file is located at `/opt/streamrev/config.json`.

### Configuration Structure

```json
{
  "database": {...},
  "redis": {...},
  "api": {...},
  "streaming": {...},
  "paths": {...},
  "security": {...},
  "logging": {...}
}
```

## Database Configuration

```json
"database": {
  "host": "127.0.0.1",
  "port": 3306,
  "user": "streamrev",
  "password": "your-password",
  "name": "streamrev"
}
```

### Options

- **host**: Database server hostname or IP
- **port**: Database server port (default: 3306)
- **user**: Database username
- **password**: Database password
- **name**: Database name

## Redis Configuration

```json
"redis": {
  "host": "127.0.0.1",
  "port": 6379,
  "password": null,
  "db": 0
}
```

### Options

- **host**: Redis server hostname
- **port**: Redis server port (default: 6379)
- **password**: Redis password (null if no password)
- **db**: Redis database number (0-15)

## API Configuration

```json
"api": {
  "host": "0.0.0.0",
  "port": 5000,
  "secret_key": "your-secret-key",
  "debug": false
}
```

### Options

- **host**: API server bind address
- **port**: API server port
- **secret_key**: Secret key for JWT tokens (must be random and secure)
- **debug**: Enable debug mode (false in production)

### Generating Secret Key

```bash
openssl rand -base64 32
```

## Streaming Configuration

```json
"streaming": {
  "ffmpeg_path": "/usr/bin/ffmpeg",
  "base_url": "http://your-domain.com",
  "max_connections_per_user": 1,
  "transcode_profiles": {...}
}
```

### Options

- **ffmpeg_path**: Path to FFmpeg binary
- **base_url**: Base URL for streaming
- **max_connections_per_user**: Default max connections per user

### Transcode Profiles

```json
"transcode_profiles": {
  "low": {
    "video_bitrate": "800k",
    "audio_bitrate": "64k",
    "preset": "veryfast"
  },
  "medium": {
    "video_bitrate": "2000k",
    "audio_bitrate": "128k",
    "preset": "veryfast"
  },
  "high": {
    "video_bitrate": "4000k",
    "audio_bitrate": "192k",
    "preset": "medium"
  }
}
```

#### Profile Options

- **video_bitrate**: Target video bitrate (e.g., "2000k")
- **audio_bitrate**: Target audio bitrate (e.g., "128k")
- **preset**: FFmpeg encoding preset (ultrafast, veryfast, fast, medium, slow)

## Paths Configuration

```json
"paths": {
  "streams": "/var/streams",
  "live": "/var/streams/live",
  "vod": "/var/streams/vod",
  "logs": "/var/log/streamrev"
}
```

### Options

- **streams**: Base directory for streams
- **live**: Directory for live streams
- **vod**: Directory for VOD content
- **logs**: Directory for log files

## Security Configuration

```json
"security": {
  "allowed_ips": [],
  "rate_limit": {
    "enabled": true,
    "requests_per_minute": 60
  }
}
```

### Options

- **allowed_ips**: Whitelist of IP addresses (empty = all allowed)
- **rate_limit.enabled**: Enable rate limiting
- **rate_limit.requests_per_minute**: Max requests per minute per IP

### IP Whitelist

To restrict access to specific IPs:

```json
"allowed_ips": ["192.168.1.100", "10.0.0.0/24"]
```

## Logging Configuration

```json
"logging": {
  "level": "INFO",
  "file": "/var/log/streamrev/app.log",
  "max_size": "100MB",
  "backup_count": 5
}
```

### Options

- **level**: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- **file**: Log file path
- **max_size**: Maximum log file size before rotation
- **backup_count**: Number of backup log files to keep

### Log Levels

- **DEBUG**: Detailed information for debugging
- **INFO**: General informational messages
- **WARNING**: Warning messages
- **ERROR**: Error messages
- **CRITICAL**: Critical errors

## Environment Variables

Configuration can also be set via environment variables:

```bash
# Database
export DB_HOST=127.0.0.1
export DB_PORT=3306
export DB_USER=streamrev
export DB_PASSWORD=your-password
export DB_NAME=streamrev

# Redis
export REDIS_HOST=127.0.0.1
export REDIS_PORT=6379
export REDIS_PASSWORD=

# API
export API_HOST=0.0.0.0
export API_PORT=5000
export SECRET_KEY=your-secret-key
export DEBUG=false

# FFmpeg
export FFMPEG_PATH=/usr/bin/ffmpeg

# Streaming
export STREAM_BASE_URL=http://your-domain.com
export MAX_CONNECTIONS_PER_USER=1

# System
export LOG_LEVEL=INFO
```

Environment variables take precedence over config file values.

## Nginx Configuration

Nginx configuration file: `/etc/nginx/sites-available/streamrev`

### Basic Configuration

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### SSL Configuration

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    ssl_certificate /etc/ssl/certs/your-cert.pem;
    ssl_certificate_key /etc/ssl/private/your-key.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
}
```

### Performance Tuning

```nginx
# Enable caching
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=streamrev:10m;

location /vod/ {
    proxy_cache streamrev;
    proxy_cache_valid 200 1h;
    proxy_cache_use_stale error timeout updating;
}
```

## Database Optimization

### MariaDB Configuration

Edit `/etc/mysql/mariadb.conf.d/50-server.cnf`:

```ini
[mysqld]
# Performance
max_connections = 200
innodb_buffer_pool_size = 1G
innodb_log_file_size = 256M

# Query Cache
query_cache_type = 1
query_cache_limit = 2M
query_cache_size = 64M
```

### Indexes

Ensure proper indexes are created:

```sql
-- User lookup
CREATE INDEX idx_username ON users(username);
CREATE INDEX idx_exp_date ON users(exp_date);

-- Stream lookup
CREATE INDEX idx_category ON streams(category_id);
CREATE INDEX idx_status ON streams(status);

-- Activity tracking
CREATE INDEX idx_user_activity ON user_activity(user_id, created_at);
```

## Redis Optimization

Edit `/etc/redis/redis.conf`:

```
# Memory
maxmemory 256mb
maxmemory-policy allkeys-lru

# Persistence (optional)
save 900 1
save 300 10
save 60 10000

# Network
bind 127.0.0.1
port 6379
```

## FFmpeg Configuration

### System Limits

For high concurrent transcoding, increase system limits:

```bash
# Edit /etc/security/limits.conf
* soft nofile 65536
* hard nofile 65536
```

### Hardware Acceleration

Enable hardware acceleration if available:

```json
"transcode_profiles": {
  "high": {
    "video_codec": "h264_nvenc",
    "audio_codec": "aac",
    "preset": "fast"
  }
}
```

#### Supported Hardware Acceleration

- **NVIDIA**: h264_nvenc, hevc_nvenc
- **Intel QSV**: h264_qsv, hevc_qsv
- **AMD**: h264_amf, hevc_amf
- **VA-API**: h264_vaapi, hevc_vaapi

## Systemd Configuration

Service file: `/etc/systemd/system/streamrev.service`

### Performance Options

```ini
[Service]
# Resource limits
LimitNOFILE=65536
LimitNPROC=4096

# Restart policy
Restart=always
RestartSec=10
StartLimitBurst=3
StartLimitInterval=60s

# Environment
Environment="PYTHONUNBUFFERED=1"
```

## Monitoring

### Log Rotation

Create `/etc/logrotate.d/streamrev`:

```
/var/log/streamrev/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        systemctl reload streamrev
    endscript
}
```

### Health Checks

Configure health check endpoint:

```bash
# Check API health
curl http://localhost:5000/health

# Check with monitoring tool
*/5 * * * * curl -f http://localhost:5000/health || systemctl restart streamrev
```

## Backup Configuration

### Database Backup

```bash
#!/bin/bash
# /opt/streamrev/scripts/backup-db.sh

mysqldump -u streamrev -p streamrev | gzip > /backup/streamrev-$(date +%Y%m%d).sql.gz

# Keep last 30 days
find /backup -name "streamrev-*.sql.gz" -mtime +30 -delete
```

### Configuration Backup

```bash
# Backup configuration files
tar -czf /backup/streamrev-config-$(date +%Y%m%d).tar.gz \
    /opt/streamrev/config.json \
    /etc/nginx/sites-available/streamrev
```

## Troubleshooting

### View Configuration

```bash
# View current configuration
cat /opt/streamrev/config.json

# Test database connection
mysql -u streamrev -p streamrev -e "SELECT VERSION();"

# Test Redis connection
redis-cli ping
```

### Common Issues

#### API Not Starting

Check configuration syntax:
```bash
python3 -c "import json; json.load(open('/opt/streamrev/config.json'))"
```

#### Database Connection Failed

Verify credentials:
```bash
mysql -u streamrev -p -e "SHOW DATABASES;"
```

#### FFmpeg Not Found

Check path:
```bash
which ffmpeg
ffmpeg -version
```

## Security Hardening

### Firewall Rules

```bash
# Allow only necessary ports
ufw allow 22/tcp   # SSH
ufw allow 80/tcp   # HTTP
ufw allow 443/tcp  # HTTPS
ufw enable
```

### File Permissions

```bash
# Configuration files
chmod 600 /opt/streamrev/config.json
chown www-data:www-data /opt/streamrev/config.json

# Directories
chmod 755 /var/streams
chown www-data:www-data /var/streams
```

### Disable Debug Mode

In production, always set:
```json
"api": {
  "debug": false
}
```

## Performance Tuning

### System Optimization

```bash
# Edit /etc/sysctl.conf
net.core.somaxconn = 1024
net.ipv4.tcp_max_syn_backlog = 2048
net.ipv4.ip_local_port_range = 1024 65535
```

Apply changes:
```bash
sysctl -p
```

## Support

For configuration help:
- Documentation: https://github.com/obscuremind/StreamRev/docs
- Issues: https://github.com/obscuremind/StreamRev/issues
