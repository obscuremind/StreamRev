"""
Database connection handler
"""

import pymysql
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class Database:
    """Database connection and query handler"""
    
    def __init__(self, host: str, user: str, password: str, database: str, port: int = 3306):
        """
        Initialize database connection
        
        Args:
            host: Database host
            user: Database user
            password: Database password
            database: Database name
            port: Database port (default: 3306)
        """
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.port = port
        self.connection = None
        
    def connect(self) -> bool:
        """
        Establish database connection
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.connection = pymysql.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                port=self.port,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=False
            )
            logger.info(f"Connected to database: {self.database}")
            return True
        except Exception as e:
            logger.error(f"Database connection failed: {str(e)}")
            return False
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")
    
    def execute(self, query: str, params: Optional[tuple] = None) -> bool:
        """
        Execute a query (INSERT, UPDATE, DELETE)
        
        Args:
            query: SQL query
            params: Query parameters
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, params or ())
                self.connection.commit()
                return True
        except Exception as e:
            logger.error(f"Query execution failed: {str(e)}")
            self.connection.rollback()
            return False
    
    def fetch_one(self, query: str, params: Optional[tuple] = None) -> Optional[Dict[str, Any]]:
        """
        Fetch single row
        
        Args:
            query: SQL query
            params: Query parameters
            
        Returns:
            Dictionary with row data or None
        """
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, params or ())
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"Fetch one failed: {str(e)}")
            return None
    
    def fetch_all(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """
        Fetch all rows
        
        Args:
            query: SQL query
            params: Query parameters
            
        Returns:
            List of dictionaries with row data
        """
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, params or ())
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Fetch all failed: {str(e)}")
            return []
    
    def last_insert_id(self) -> int:
        """
        Get last insert ID
        
        Returns:
            Last insert ID
        """
        return self.connection.insert_id()
