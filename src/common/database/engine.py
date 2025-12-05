"""
SQLAlchemy database engine and metadata management.
Provides database connectivity and schema reflection.
"""
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine import Engine
import logging

from ..config import config

logger = logging.getLogger(__name__)

# Global instances
_engine = None
_metadata = None


def get_engine(echo: bool = False) -> Engine:
    """Get or create SQLAlchemy engine."""
    global _engine
    if _engine is None:
        database_url = config.database.database_url
        
        # Create engine with appropriate settings
        if database_url.startswith('sqlite'):
            # SQLite-specific settings
            _engine = create_engine(
                database_url,
                echo=echo,
                pool_pre_ping=True,
                connect_args={"check_same_thread": False}
            )
        else:
            # PostgreSQL/MySQL settings
            _engine = create_engine(
                database_url,
                echo=echo,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                pool_recycle=300
            )
        
        logger.debug(f"Created SQLAlchemy engine for {database_url}")
    
    return _engine


def get_metadata() -> MetaData:
    """Get reflected metadata for the current database."""
    global _metadata
    if _metadata is None:
        engine = get_engine()
        _metadata = MetaData()
        # Reflect all existing tables (used only for schema drift validation at startup)
        _metadata.reflect(bind=engine)
        logger.debug(f"Reflected {len(_metadata.tables)} tables from database")
    return _metadata




def cleanup_database_connections():
    """Clean up database connections and dispose of the engine."""
    global _engine, _metadata

    if _engine is not None:
        logger.info("Disposing database engine and closing all connections")
        _engine.dispose()
        _engine = None
        _metadata = None
        logger.info("Database connections cleaned up successfully")


class DatabaseSession:
    """Context manager for database sessions."""

    def __init__(self):
        self.session = None

    def __enter__(self) -> Session:
        engine = get_engine()
        session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        self.session = session_factory()
        return self.session

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.session.rollback()
        else:
            self.session.commit()
        self.session.close()