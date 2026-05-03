"""
Database connection management.
Migrated from services/bbdd_conection.py with improvements.
"""

from dotenv import load_dotenv
import os
import mysql.connector
from mysql.connector import Error
from typing import Optional

load_dotenv()


class DatabaseConnection:
    """Singleton database connection manager."""
    
    _instance: Optional['DatabaseConnection'] = None
    _connection: Optional[mysql.connector.MySQLConnection] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_connection(self) -> mysql.connector.MySQLConnection:
        """
        Get or create database connection.
        
        Returns:
            mysql.connector.MySQLConnection: Active database connection
            
        Raises:
            RuntimeError: If connection fails
        """
        if self._connection is None or not self._connection.is_connected():
            try:
                self._connection = mysql.connector.connect(
                    host=os.getenv("DB_HOST"),
                    user=os.getenv("DB_USER"),
                    password=os.getenv("DB_PASS"),
                    database=os.getenv("DB_NAME"),
                    port=int(os.getenv("DB_PORT", "3306")),
                    autocommit=True,
                )
                self._connection.ping(reconnect=True, attempts=3, delay=2)
                print("✅ Database connection established.")
            except Error as e:
                raise RuntimeError(f"❌ MySQL connection error: {e}")
        
        return self._connection
    
    def close_connection(self):
        """Close the database connection if it exists."""
        if self._connection and self._connection.is_connected():
            self._connection.close()
            print("🔌 Database connection closed.")
            self._connection = None


# Singleton instance
_db = DatabaseConnection()


def get_connection() -> mysql.connector.MySQLConnection:
    """
    Get database connection (backward compatible with old code).
    
    Returns:
        mysql.connector.MySQLConnection: Active database connection
    """
    return _db.get_connection()


def close_connection():
    """Close database connection (backward compatible with old code)."""
    _db.close_connection()
