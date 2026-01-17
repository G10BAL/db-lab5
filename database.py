import mariadb
import configparser
from typing import Optional, List, Dict, Any, Tuple
from contextlib import contextmanager
import logging
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseConfig:
    def __init__(self, config_file: str = 'config.ini'):
        self.config = configparser.ConfigParser()
        
        possible_paths = [
            config_file
        ]
        
        config_found = False
        for path in possible_paths:
            if os.path.exists(path):
                self.config.read(path)
                config_found = True
                logger.info(f"Config file loaded from: {path}")
                break
        
        if not config_found:
            logger.warning(f"Config file '{config_file}' not found in any of the expected locations")
            logger.warning(f"Tried: {possible_paths}")
            self._set_defaults()
    
    def _set_defaults(self):
        """Standard configuration values"""
        logger.info("Using default configuration values")
        self.config.add_section('database')
        self.config.set('database', 'host', 'localhost')
        self.config.set('database', 'port', '3306')
        self.config.set('database', 'user', 'weapon_admin')
        self.config.set('database', 'password', 'SecurePassword123!')
        self.config.set('database', 'database', 'weapon_inventory')
        
        self.config.add_section('connection_pool')
        self.config.set('connection_pool', 'pool_name', 'weapon_pool')
        self.config.set('connection_pool', 'pool_size', '5')
        self.config.set('connection_pool', 'pool_reset_connection', 'True')
        
    def get_db_config(self) -> Dict[str, Any]:
        """Get params for connection"""
        return {
            'host': self.config.get('database', 'host'),
            'port': self.config.getint('database', 'port'),
            'user': self.config.get('database', 'user'),
            'password': self.config.get('database', 'password'),
            'database': self.config.get('database', 'database')
        }
    
    def get_pool_config(self) -> Dict[str, Any]:
        """Get connection pool parameters"""
        return {
            'pool_name': self.config.get('connection_pool', 'pool_name'),
            'pool_size': self.config.getint('connection_pool', 'pool_size'),
            'pool_reset_connection': self.config.getboolean('connection_pool', 'pool_reset_connection')
        }


class DatabaseConnection:  
    _pool = None
    _config = None
    
    @classmethod
    def initialize_pool(cls, config_file: str = 'config.ini'):
        if cls._pool is not None:
            logger.warning("Connection pool already initialized")
            return
        
        try:
            cls._config = DatabaseConfig(config_file)
            db_config = cls._config.get_db_config()
            pool_config = cls._config.get_pool_config()
            
            cls._pool = mariadb.ConnectionPool(
                **db_config,
                **pool_config
            )
            
            logger.info(f"Connection pool '{pool_config['pool_name']}' initialized successfully")
            
        except mariadb.Error as e:
            logger.error(f"Error initializing connection pool: {e}")
            raise
    
    @classmethod
    @contextmanager
    def get_connection(cls):
        if cls._pool is None:
            cls.initialize_pool()
        
        connection = None
        try:
            connection = cls._pool.get_connection()
            logger.debug("Connection acquired from pool")
            yield connection
        except mariadb.Error as e:
            logger.error(f"Database error: {e}")
            raise
        finally:
            if connection:
                connection.close()
                logger.debug("Connection returned to pool")
    
    @classmethod
    @contextmanager
    def get_cursor(cls, dictionary: bool = False):
        with cls.get_connection() as conn:
            cursor = conn.cursor(dictionary=dictionary)
            try:
                yield conn, cursor
            finally:
                cursor.close()
    
    @classmethod
    def close_pool(cls):
        if cls._pool:
            cls._pool = None
            logger.info("Connection pool closed")


class BaseRepository:
    @staticmethod
    def execute_query(query: str, params: Optional[Tuple] = None, 
                     fetch_one: bool = False, 
                     fetch_all: bool = False,
                     dictionary: bool = True,
                     commit: bool = False) -> Optional[Any]:
        """
        Execute a SQL query
        
        Args:
            query: SQL 
            params: params
            fetch_one: return one 
            fetch_all: return all
            dictionary: return as dicts
            commit: commit transaction
            
        Returns:
            Result/None
        """
        try:
            with DatabaseConnection.get_cursor(dictionary=dictionary) as (conn, cursor):
                logger.debug(f"Executing query: {query}")
                logger.debug(f"Parameters: {params}")
                
                cursor.execute(query, params or ())
                
                if commit:
                    conn.commit()
                    logger.debug("Transaction committed")
                    return cursor.lastrowid if cursor.lastrowid > 0 else None
                
                if fetch_one:
                    result = cursor.fetchone()
                    logger.debug(f"Fetched one row: {result}")
                    return result
                
                if fetch_all:
                    results = cursor.fetchall()
                    logger.debug(f"Fetched {len(results)} rows")
                    return results
                
                return None
                
        except mariadb.Error as e:
            logger.error(f"Query execution error: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Parameters: {params}")
            raise
    
    @staticmethod
    @contextmanager
    def transaction():
        """ Context manager for transactions """
        with DatabaseConnection.get_cursor(dictionary=True) as (conn, cursor):
            try:
                logger.debug("Transaction started")
                yield conn, cursor
                conn.commit()
                logger.info("Transaction committed successfully")
            except Exception as e:
                conn.rollback()
                logger.error(f"Transaction rolled back due to error: {e}")
                raise
    
    @staticmethod
    def execute_many(query: str, params_list: List[Tuple]) -> int:
        """
        Execute multiple queries (batch insert/update)
        
        Args:
            query: SQL query
            params_list: list of params
            
        Returns:
            amount of affected rows
        """
        try:
            with DatabaseConnection.get_cursor() as (conn, cursor):
                logger.debug(f"Executing batch query: {query}")
                logger.debug(f"Batch size: {len(params_list)}")
                
                cursor.executemany(query, params_list)
                conn.commit()
                
                affected = cursor.rowcount
                logger.info(f"Batch operation completed. Rows affected: {affected}")
                return affected
                
        except mariadb.Error as e:
            logger.error(f"Batch execution error: {e}")
            raise


if __name__ == "__main__":
    try:
        DatabaseConnection.initialize_pool()
        
        # Test query
        result = BaseRepository.execute_query(
            "SELECT DATABASE() as current_db",
            fetch_one=True
        )
        
        if result:
            print(f"Connected to database: {result['current_db']}")
        
        # Test counting tables (same as in db_commands.pdf)
        tables = BaseRepository.execute_query(
            "SELECT COUNT(*) as count FROM information_schema.tables WHERE table_schema = ?",
            params=('weapon_inventory',),
            fetch_one=True
        )
        
        if tables:
            print(f"Number of tables: {tables['count']}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        DatabaseConnection.close_pool()