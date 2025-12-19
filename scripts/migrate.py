#!/usr/bin/env python3
"""
Database migration CLI tool for StreamRev
"""

import sys
import os
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.connection import Database
from src.database.migrations import MigrationManager, create_migration
from src.utils.config import load_config


def main():
    """Main migration CLI"""
    parser = argparse.ArgumentParser(description='StreamRev Database Migrations')
    parser.add_argument('command', choices=['status', 'migrate', 'create'],
                       help='Migration command')
    parser.add_argument('name', nargs='?', help='Migration name (for create)')
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config()
    
    # Connect to database
    db = Database(
        host=config['db_host'],
        user=config['db_user'],
        password=config['db_password'],
        database=config['db_name'],
        port=config['db_port']
    )
    
    if not db.connect():
        print("Failed to connect to database")
        sys.exit(1)
    
    # Create migration manager
    manager = MigrationManager(db)
    migrations_dir = 'src/database/migrations'
    
    if args.command == 'status':
        # Show migration status
        applied = manager.get_applied_migrations()
        pending = manager.get_pending_migrations(migrations_dir)
        
        print("Applied migrations:")
        for version in applied:
            print(f"  ✓ {version}")
        
        print(f"\nPending migrations: {len(pending)}")
        for migration in pending:
            print(f"  - {migration['version']}")
    
    elif args.command == 'migrate':
        # Run pending migrations
        count = manager.run_pending_migrations(migrations_dir)
        print(f"Applied {count} migration(s)")
    
    elif args.command == 'create':
        # Create new migration
        if not args.name:
            print("Error: Migration name required")
            sys.exit(1)
        
        filepath = create_migration(args.name, migrations_dir)
        print(f"Created migration: {filepath}")
    
    db.close()


if __name__ == '__main__':
    main()
