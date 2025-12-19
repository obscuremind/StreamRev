#!/bin/bash

################################################################################
# StreamRev Monitoring Script
# 
# This script checks the health of StreamRev services
################################################################################

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

check_service() {
    SERVICE=$1
    if systemctl is-active --quiet "$SERVICE"; then
        echo -e "${GREEN}✓${NC} $SERVICE is running"
        return 0
    else
        echo -e "${RED}✗${NC} $SERVICE is not running"
        return 1
    fi
}

check_port() {
    PORT=$1
    NAME=$2
    if nc -z localhost "$PORT" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} $NAME (port $PORT) is accessible"
        return 0
    else
        echo -e "${RED}✗${NC} $NAME (port $PORT) is not accessible"
        return 1
    fi
}

check_disk() {
    USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
    if [ "$USAGE" -lt 80 ]; then
        echo -e "${GREEN}✓${NC} Disk usage: ${USAGE}%"
    elif [ "$USAGE" -lt 90 ]; then
        echo -e "${YELLOW}⚠${NC} Disk usage: ${USAGE}%"
    else
        echo -e "${RED}✗${NC} Disk usage: ${USAGE}% (critical)"
    fi
}

check_memory() {
    USAGE=$(free | awk 'NR==2 {printf "%.0f", $3/$2*100}')
    if [ "$USAGE" -lt 80 ]; then
        echo -e "${GREEN}✓${NC} Memory usage: ${USAGE}%"
    elif [ "$USAGE" -lt 90 ]; then
        echo -e "${YELLOW}⚠${NC} Memory usage: ${USAGE}%"
    else
        echo -e "${RED}✗${NC} Memory usage: ${USAGE}% (critical)"
    fi
}

echo "StreamRev System Monitor"
echo "======================="
echo ""

echo "Services:"
check_service mariadb
check_service redis-server
check_service nginx
check_service streamrev
echo ""

echo "Network:"
check_port 3306 "MariaDB"
check_port 6379 "Redis"
check_port 80 "Nginx"
check_port 5000 "StreamRev API"
echo ""

echo "System Resources:"
check_disk
check_memory
echo ""

echo "API Health:"
if curl -f http://localhost:5000/health -s > /dev/null; then
    echo -e "${GREEN}✓${NC} API health check passed"
else
    echo -e "${RED}✗${NC} API health check failed"
fi
echo ""

# Log recent errors
echo "Recent Errors (last 10):"
journalctl -u streamrev --no-pager -n 10 --priority=err || echo "No recent errors"
