#!/bin/bash

################################################################################
# StreamRev Update Script
# 
# This script updates StreamRev to the latest version
################################################################################

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

INSTALL_DIR="/opt/streamrev"

echo -e "${GREEN}StreamRev Update Script${NC}"
echo "======================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}This script must be run as root${NC}"
    exit 1
fi

# Backup before update
echo -e "${YELLOW}Creating backup before update...${NC}"
if [ -f "/usr/local/bin/streamrev-backup" ] || [ -f "./scripts/backup.sh" ]; then
    bash ./scripts/backup.sh || echo "Backup script not found, skipping..."
fi

# Stop services
echo "Stopping StreamRev service..."
systemctl stop streamrev

# Pull latest changes
echo "Pulling latest changes..."
cd "$INSTALL_DIR"
git fetch origin
git pull origin main

# Update Python dependencies
echo "Updating Python dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt --upgrade

# Run database migrations if any
echo "Checking for database migrations..."
# TODO: Add migration logic here

# Restart services
echo "Restarting StreamRev service..."
systemctl start streamrev
systemctl status streamrev --no-pager

echo ""
echo -e "${GREEN}✓ Update completed successfully!${NC}"
echo ""
echo "Current version:"
git log -1 --oneline
