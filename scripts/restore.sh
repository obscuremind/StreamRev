#!/bin/bash

################################################################################
# StreamRev Restore Script
# 
# This script restores the database from a backup
################################################################################

set -e

# Configuration
BACKUP_DIR="/backup/streamrev"
DB_NAME="${DB_NAME:-streamrev}"
DB_USER="${DB_USER:-streamrev}"
DB_PASSWORD_FILE="/root/.streamrev_db_password"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

if [ -z "$1" ]; then
    echo -e "${RED}Usage: $0 <backup_file.sql.gz>${NC}"
    echo ""
    echo "Available backups:"
    ls -lh "$BACKUP_DIR"/*.sql.gz 2>/dev/null || echo "No backups found"
    exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "$BACKUP_FILE" ]; then
    echo -e "${RED}Error: Backup file not found: $BACKUP_FILE${NC}"
    exit 1
fi

# Confirm restore
echo -e "${YELLOW}WARNING: This will replace the current database!${NC}"
echo "Backup file: $BACKUP_FILE"
read -p "Are you sure you want to restore? (yes/no): " -r
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "Restore cancelled"
    exit 0
fi

# Get database password
if [ -f "$DB_PASSWORD_FILE" ]; then
    DB_PASSWORD=$(cat "$DB_PASSWORD_FILE")
else
    read -s -p "Enter database password: " DB_PASSWORD
    echo
fi

echo -e "${GREEN}Starting restore...${NC}"

# Drop and recreate database
echo "Dropping existing database..."
mysql -u"$DB_USER" -p"$DB_PASSWORD" -e "DROP DATABASE IF EXISTS ${DB_NAME};"
mysql -u"$DB_USER" -p"$DB_PASSWORD" -e "CREATE DATABASE ${DB_NAME};"

# Restore from backup
echo "Restoring database..."
gunzip < "$BACKUP_FILE" | mysql -u"$DB_USER" -p"$DB_PASSWORD" "$DB_NAME"

echo -e "${GREEN}✓ Database restored successfully!${NC}"

# Restart services
echo "Restarting StreamRev service..."
systemctl restart streamrev

echo -e "${GREEN}Restore completed!${NC}"
