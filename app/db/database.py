"""
Database connection and session management for the application.
Handles connection to TiDB or other MySQL-compatible databases using SQLModel.
"""
import logging
from typing import Generator
from sqlmodel import create_engine, Session, SQLModel, text
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import DisconnectionError, OperationalError
from sqlalchemy import event

from app.core.config import settings

logger = logging.getLogger(__name__)

"""
Database connection and session management for the application.
Handles connection to TiDB or other MySQL-compatible databases using SQLModel.
"""
import logging
from typing import Generator
from sqlmodel import create_engine, Session, SQLModel, text
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import DisconnectionError, OperationalError
from sqlalchemy import event

from app.core.config import settings

logger = logging.getLogger(__name__)

# Global engine variable - will be initialized lazily
_engine = None

def get_engine():
    """Get or create the SQLAlchemy engine with proper settings."""
    global _engine
    if _engine is None:
        try:
            _engine = create_engine(
                settings.database_url,
                poolclass=QueuePool,
                pool_size=settings.db_pool_size,
                max_overflow=settings.db_max_overflow,
                pool_pre_ping=True,  # Validate connections before use
                pool_recycle=3600,   # Recycle connections every hour
                echo=settings.debug,  # Log SQL queries in debug mode
            )
            logger.info(f"Database engine created successfully with URL: {settings.database_url}")
            
            # Register event listeners after engine creation
            @event.listens_for(_engine, "connect")
            def set_database_session_variables(dbapi_connection, connection_record):
                """Set database-specific session variables for optimal performance."""
                try:
                    with dbapi_connection.cursor() as cursor:
                        cursor.execute("SELECT VERSION()")
                        version_string = cursor.fetchone()[0].lower()
                        
                        if 'tidb' in version_string:
                            logger.info("Connected to TiDB. Applying TiDB-specific session variables.")
                            cursor.execute("SET SESSION tidb_enable_vectorized_expression = ON")
                            cursor.execute("SET SESSION tidb_hash_join_concurrency = 4")
                        elif 'mysql' in version_string:
                            logger.info("Connected to MySQL. Applying MySQL-specific session variables.")
                            cursor.execute("SET SESSION sql_mode = 'STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO'")
                        else:
                            logger.info(f"Connected to an unknown MySQL-compatible database: {version_string}")
                
                except Exception as e:
                    logger.warning(f"Failed to set database session variables: {e}")
            
        except ImportError:
            logger.critical("mysql-connector-python is not installed. Please install it with: pip install mysql-connector-python")
            raise
    return _engine

# Property to maintain backward compatibility
@property
def engine():
    return get_engine()

def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency to get a database session using SQLModel.
    Ensures the session is properly closed and rolled back on error.
    """
    with Session(get_engine()) as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session error: {e}", exc_info=True)
            session.rollback()
            raise


def create_database_if_not_exists():
    """
    Creates the database specified in the settings if it doesn't already exist.
    This is useful for initial setup in development and testing environments.
    """
    try:
        # Connect to the MySQL server without specifying a database
        if settings.database_url_env:
            # Parse the DATABASE_URL to get server connection (without database)
            from urllib.parse import urlparse
            parsed = urlparse(settings.database_url_env)
            server_url = f"mysql+mysqlconnector://{parsed.username}:{parsed.password}@{parsed.hostname}:{parsed.port or 4000}"
            # Extract database name from URL path
            db_name = parsed.path.lstrip('/') if parsed.path else 'test'
        else:
            # Fallback to individual settings
            server_url = f"mysql+mysqlconnector://{settings.tidb_user}:{settings.tidb_password}@{settings.tidb_host}:{settings.tidb_port}"
            db_name = settings.tidb_database
        
        temp_engine = create_engine(server_url, echo=settings.debug)
        
        with temp_engine.connect() as connection:
            connection.execute(text(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
            connection.commit()
        
        temp_engine.dispose()
        logger.info(f"Database '{db_name}' created or already exists.")
    except Exception as e:
        logger.error(f"Failed to create database '{db_name}': {e}")
        raise


def create_db_and_tables():
    """
    Create the database if it doesn't exist and then create all tables using SQLModel.
    This function is designed to be idempotent and safe to run on startup.
    """
    logger.info("Attempting to create database and tables...")
    try:
        # Step 1: Create the database if it does not exist.
        # This requires connecting to the MySQL server without a specific database.
        if settings.database_url_env:
            # Parse the DATABASE_URL to get server connection (without database)
            from urllib.parse import urlparse
            parsed = urlparse(settings.database_url_env)
            server_url = f"mysql+mysqlconnector://{parsed.username}:{parsed.password}@{parsed.hostname}:{parsed.port or 4000}"
            # Extract database name from URL path
            db_name = parsed.path.lstrip('/') if parsed.path else 'test'
        else:
            # Fallback to individual settings
            server_url = f"mysql+mysqlconnector://{settings.tidb_user}:{settings.tidb_password}@{settings.tidb_host}:{settings.tidb_port}"
            db_name = settings.tidb_database
        
        # Use a temporary engine with autocommit enabled for the CREATE DATABASE command.
        # This command cannot be run inside a transaction.
        temp_engine = create_engine(server_url, connect_args={"autocommit": True})
        
        with temp_engine.connect() as connection:
            connection.execute(text(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
            logger.info(f"Database '{db_name}' created or already exists.")
        
        # Dispose of the temporary engine to close its connections.
        temp_engine.dispose()

        # Step 2: Create the tables within the newly ensured database using SQLModel.
        # Use the main application engine, which is configured with a connection pool
        # and connects to the specific database.
        logger.info("Creating database tables with SQLModel...")
        
        # Import all models to ensure they are registered with SQLModel.metadata
        from app.models.user import User
        from app.models.service import Service
        from app.models.chat import ChatMessage
        
        # The `engine.begin()` context manager provides a connection and a transaction.
        # `create_all` will use this transaction to execute all DDL statements.
        with get_engine().begin() as conn:
            SQLModel.metadata.create_all(conn)
            
        logger.info("Database tables created successfully with SQLModel.")

    except Exception as e:
        logger.error(f"An error occurred during database and table creation: {e}", exc_info=True)
        raise



def check_database_connection() -> bool:
    """
    Checks if a connection to the database can be established.
    
    Returns:
        bool: True if connection is successful, False otherwise.
    """
    try:
        with get_engine().connect() as connection:
            connection.scalar(text("SELECT 1"))
        logger.info("Database connection check successful.")
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False


class DatabaseManager:
    """A manager for handling database operations and health checks using SQLModel."""
    
    def __init__(self, db_engine):
        self.engine = db_engine
    
    def get_session(self) -> Session:
        """Provides a new SQLModel database session."""
        return Session(self.engine)
    
    def close_all_connections(self):
        """Close all database connections."""
        try:
            get_engine().dispose()
            logger.info("All database connections closed.")
        except Exception as e:
            logger.error(f"Error closing database connections: {e}")
    
    def health_check(self) -> dict:
        """
        Performs a comprehensive health check of the database connection.
        
        Returns:
            dict: A dictionary with the health status and details.
        """
        status = {"database": "unhealthy", "details": {}}
        try:
            if check_database_connection():
                status["database"] = "healthy"
                pool = get_engine().pool
                status["details"] = {
                    "pool_size": pool.size(),
                    "checked_in_connections": pool.checkedin(),
                    "checked_out_connections": pool.checkedout(),
                    "overflow_connections": pool.overflow(),
                }
            else:
                status["details"]["error"] = "Failed to establish a basic connection."
        except Exception as e:
            status["details"]["error"] = str(e)
        
        return status

# Global database manager instance
db_manager = DatabaseManager(get_engine())