#!/bin/bash
set -e

# Wait for database to be ready
if [ -n "$DB_HOST" ]; then
    echo "Waiting for database..."
    while ! mysqladmin ping -h"$DB_HOST" -P"${DB_PORT:-3306}" --silent; do
        sleep 1
    done
    echo "Database is ready!"
fi

# Wait for Redis to be ready
if [ -n "$REDIS_HOST" ]; then
    echo "Waiting for Redis..."
    while ! redis-cli -h "$REDIS_HOST" -p "${REDIS_PORT:-6379}" ping > /dev/null 2>&1; do
        sleep 1
    done
    echo "Redis is ready!"
fi

# Activate virtual environment
source /opt/streamrev/venv/bin/activate

# Execute the main command
exec "$@"
