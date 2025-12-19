#!/bin/bash

################################################################################
# StreamRev Backup Script
# 
# This script backs up the database and configuration files
################################################################################

set -e

# Configuration
BACKUP_DIR="/backup/streamrev"
DB_NAME="${DB_NAME:-streamrev}"
DB_USER="${DB_USER:-streamrev}"
DB_PASSWORD_FILE="/root/.streamrev_db_password"
RETENTION_DAYS=30

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Date stamp
DATE=$(date +%Y%m%d_%H%M%S)

echo -e "${GREEN}Starting StreamRev backup...${NC}"

# Backup database
if [ -f "$DB_PASSWORD_FILE" ]; then
    DB_PASSWORD=$(cat "$DB_PASSWORD_FILE")
    echo "Backing up database..."
    mysqldump -u"$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" | gzip > "$BACKUP_DIR/db_${DATE}.sql.gz"
    echo -e "${GREEN}✓ Database backed up: db_${DATE}.sql.gz${NC}"
else
    echo -e "${RED}✗ Database password file not found${NC}"
fi

# Backup configuration files
echo "Backing up configuration..."
tar -czf "$BACKUP_DIR/config_${DATE}.tar.gz" \
    /opt/streamrev/config.json \
    /etc/nginx/sites-available/streamrev \
    2>/dev/null || true
echo -e "${GREEN}✓ Configuration backed up: config_${DATE}.tar.gz${NC}"

# Clean old backups
echo "Cleaning old backups..."
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +${RETENTION_DAYS} -delete
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +${RETENTION_DAYS} -delete
echo -e "${GREEN}✓ Old backups cleaned (${RETENTION_DAYS} days retention)${NC}"

# List backups
echo ""
echo "Recent backups:"
ls -lh "$BACKUP_DIR" | tail -10

echo -e "${GREEN}Backup completed successfully!${NC}"
