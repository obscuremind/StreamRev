# StreamRev Docker Deployment

This guide covers deploying StreamRev using Docker and Docker Compose.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- 4GB+ RAM
- 20GB+ disk space

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/obscuremind/StreamRev.git
cd StreamRev
```

### 2. Configure Environment

Create `.env` file:

```bash
cat > .env <<EOF
# Database
DB_PASSWORD=your_secure_db_password
MYSQL_ROOT_PASSWORD=your_secure_root_password

# Application
SECRET_KEY=$(openssl rand -base64 32)
FLASK_DEBUG=false

# Optional
TZ=UTC
EOF
```

### 3. Start Services

```bash
docker-compose up -d
```

Services will be available at:
- StreamRev API: http://localhost:5000
- Web Interface: http://localhost:80
- Nginx Proxy: http://localhost:8080

### 4. Check Status

```bash
docker-compose ps
docker-compose logs -f streamrev
```

## Configuration

### Docker Compose Services

#### streamrev
Main application container running Flask API and web interface.

**Ports:**
- 5000: API
- 80: Web interface

**Volumes:**
- `./streams`: Media files storage
- `./logs`: Application logs

#### mariadb
Database container with automatic schema initialization.

**Environment:**
- `MYSQL_ROOT_PASSWORD`: Root password
- `MYSQL_DATABASE`: streamrev
- `MYSQL_USER`: streamrev
- `MYSQL_PASSWORD`: User password

**Volume:**
- `mariadb-data`: Persistent database storage

#### redis
Cache and session storage.

**Volume:**
- `redis-data`: Persistent cache storage

#### nginx
Reverse proxy for serving streams and static content.

**Port:**
- 8080: HTTP proxy

## Customization

### Custom Configuration

Mount custom config file:

```yaml
services:
  streamrev:
    volumes:
      - ./config.json:/opt/streamrev/config.json:ro
```

### Environment Variables

Override in `docker-compose.yml`:

```yaml
services:
  streamrev:
    environment:
      - DB_HOST=mariadb
      - DB_PORT=3306
      - DB_USER=streamrev
      - DB_PASSWORD=${DB_PASSWORD}
      - REDIS_HOST=redis
      - SECRET_KEY=${SECRET_KEY}
      - LOG_LEVEL=INFO
```

### Build Custom Image

Modify `Dockerfile` and rebuild:

```bash
docker-compose build streamrev
docker-compose up -d streamrev
```

## Database Management

### Initialize Database

Database schema is automatically initialized on first run.

### Backup Database

```bash
docker-compose exec mariadb mysqldump -u streamrev -p streamrev | gzip > backup.sql.gz
```

### Restore Database

```bash
gunzip < backup.sql.gz | docker-compose exec -T mariadb mysql -u streamrev -p streamrev
```

### Access Database

```bash
docker-compose exec mariadb mysql -u streamrev -p streamrev
```

## Logs

### View All Logs

```bash
docker-compose logs -f
```

### Service-Specific Logs

```bash
docker-compose logs -f streamrev
docker-compose logs -f mariadb
docker-compose logs -f redis
```

### Application Logs

```bash
docker-compose exec streamrev tail -f /var/log/streamrev/app.log
```

## Scaling

### Multiple Workers

Update `docker-compose.yml`:

```yaml
services:
  streamrev:
    deploy:
      replicas: 3
```

### Load Balancer

Add HAProxy or Nginx load balancer:

```yaml
services:
  loadbalancer:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx-lb.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - streamrev
```

## Production Deployment

### Security

1. **Change Default Passwords**
   ```bash
   # Generate strong passwords
   openssl rand -base64 32
   ```

2. **Use SSL/TLS**
   ```yaml
   services:
     nginx:
       ports:
         - "443:443"
       volumes:
         - ./certs:/etc/nginx/certs:ro
   ```

3. **Restrict Network**
   ```yaml
   networks:
     streamrev-network:
       driver: bridge
       ipam:
         config:
           - subnet: 172.25.0.0/16
   ```

### Resource Limits

```yaml
services:
  streamrev:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G
```

### Health Checks

```yaml
services:
  streamrev:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose logs streamrev

# Inspect container
docker-compose ps
docker inspect streamrev-app
```

### Database Connection Failed

```bash
# Check MariaDB is running
docker-compose exec mariadb mysqladmin ping

# Test connection
docker-compose exec streamrev mysql -h mariadb -u streamrev -p
```

### Permission Issues

```bash
# Fix permissions
docker-compose exec streamrev chown -R www-data:www-data /var/streams
```

### Reset Everything

```bash
# Stop and remove all containers, volumes
docker-compose down -v

# Start fresh
docker-compose up -d
```

## Updates

### Update Images

```bash
# Pull latest changes
git pull

# Rebuild and restart
docker-compose build --no-cache
docker-compose up -d
```

### Database Migrations

```bash
docker-compose exec streamrev python scripts/migrate.py migrate
```

## Backup Strategy

### Full Backup

```bash
#!/bin/bash
# Create backup directory
mkdir -p backups/$(date +%Y%m%d)

# Backup database
docker-compose exec mariadb mysqldump -u streamrev -p streamrev | \
    gzip > backups/$(date +%Y%m%d)/database.sql.gz

# Backup volumes
docker run --rm -v streamrev_mariadb-data:/data -v $(pwd)/backups:/backup \
    alpine tar czf /backup/$(date +%Y%m%d)/mariadb-data.tar.gz /data
```

## Monitoring

### Prometheus Metrics

Add Prometheus exporter:

```yaml
services:
  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"
```

### Grafana Dashboard

```yaml
services:
  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
```

## Support

- Documentation: [GitHub Docs](https://github.com/obscuremind/StreamRev/docs)
- Issues: [GitHub Issues](https://github.com/obscuremind/StreamRev/issues)
