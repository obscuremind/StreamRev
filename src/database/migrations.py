"""
Database migration utilities for StreamRev
"""

import os
import logging
from typing import List, Dict, Any
from .connection import Database

logger = logging.getLogger(__name__)


class MigrationManager:
    """Manage database migrations"""
    
    def __init__(self, db: Database):
        """
        Initialize migration manager
        
        Args:
            db: Database instance
        """
        self.db = db
        self._ensure_migration_table()
    
    def _ensure_migration_table(self):
        """Create migrations tracking table if it doesn't exist"""
        query = """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id INT UNSIGNED NOT NULL AUTO_INCREMENT,
                version VARCHAR(255) NOT NULL UNIQUE,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
        self.db.execute(query)
    
    def get_applied_migrations(self) -> List[str]:
        """
        Get list of applied migrations
        
        Returns:
            List of migration versions
        """
        query = "SELECT version FROM schema_migrations ORDER BY id"
        results = self.db.fetch_all(query)
        return [r['version'] for r in results]
    
    def record_migration(self, version: str) -> bool:
        """
        Record a migration as applied
        
        Args:
            version: Migration version
            
        Returns:
            bool: True if successful
        """
        query = "INSERT INTO schema_migrations (version) VALUES (%s)"
        return self.db.execute(query, (version,))
    
    def rollback_migration(self, version: str) -> bool:
        """
        Remove a migration record
        
        Args:
            version: Migration version
            
        Returns:
            bool: True if successful
        """
        query = "DELETE FROM schema_migrations WHERE version = %s"
        return self.db.execute(query, (version,))
    
    def apply_migration(self, version: str, sql: str) -> bool:
        """
        Apply a migration
        
        Args:
            version: Migration version
            sql: SQL to execute
            
        Returns:
            bool: True if successful
        """
        try:
            # Execute migration SQL
            for statement in sql.split(';'):
                statement = statement.strip()
                if statement:
                    self.db.execute(statement)
            
            # Record migration
            self.record_migration(version)
            logger.info(f"Applied migration: {version}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply migration {version}: {str(e)}")
            return False
    
    def get_pending_migrations(self, migrations_dir: str) -> List[Dict[str, Any]]:
        """
        Get list of pending migrations
        
        Args:
            migrations_dir: Directory containing migration files
            
        Returns:
            List of pending migration info
        """
        applied = set(self.get_applied_migrations())
        pending = []
        
        if not os.path.exists(migrations_dir):
            return pending
        
        for filename in sorted(os.listdir(migrations_dir)):
            if filename.endswith('.sql'):
                version = filename[:-4]  # Remove .sql extension
                if version not in applied:
                    filepath = os.path.join(migrations_dir, filename)
                    pending.append({
                        'version': version,
                        'filepath': filepath
                    })
        
        return pending
    
    def run_pending_migrations(self, migrations_dir: str) -> int:
        """
        Run all pending migrations
        
        Args:
            migrations_dir: Directory containing migration files
            
        Returns:
            Number of migrations applied
        """
        pending = self.get_pending_migrations(migrations_dir)
        count = 0
        
        for migration in pending:
            logger.info(f"Applying migration: {migration['version']}")
            
            with open(migration['filepath'], 'r') as f:
                sql = f.read()
            
            if self.apply_migration(migration['version'], sql):
                count += 1
            else:
                logger.error(f"Failed to apply migration: {migration['version']}")
                break
        
        return count


def create_migration(name: str, migrations_dir: str = 'src/database/migrations') -> str:
    """
    Create a new migration file
    
    Args:
        name: Migration name
        migrations_dir: Directory for migrations
        
    Returns:
        Path to created migration file
    """
    import datetime
    
    # Create migrations directory if it doesn't exist
    os.makedirs(migrations_dir, exist_ok=True)
    
    # Generate version (timestamp + name)
    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    version = f"{timestamp}_{name}"
    filepath = os.path.join(migrations_dir, f"{version}.sql")
    
    # Create migration template
    template = f"""-- Migration: {name}
-- Created: {datetime.datetime.now().isoformat()}

-- Add your migration SQL here

-- Example:
-- ALTER TABLE users ADD COLUMN new_field VARCHAR(255);

-- Rollback instructions (comments only):
-- ALTER TABLE users DROP COLUMN new_field;
"""
    
    with open(filepath, 'w') as f:
        f.write(template)
    
    logger.info(f"Created migration: {filepath}")
    return filepath
