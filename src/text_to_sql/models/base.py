"""
Generic SQLAlchemy base configuration for any database schema.
Works automatically with any existing database through reflection.
"""
import os
from pathlib import Path
from sqlalchemy import create_engine, MetaData, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine import Engine
import logging

from ..config import config

logger = logging.getLogger(__name__)

# Create declarative base (not used for reflection, but available for custom models)
Base = declarative_base()

# Global engine and session factory
_engine = None
_SessionLocal = None
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
        
        logger.info(f"Created SQLAlchemy engine for {database_url}")
    
    return _engine


def get_metadata() -> MetaData:
    """Get reflected metadata for the current database."""
    global _metadata
    if _metadata is None:
        engine = get_engine()
        _metadata = MetaData()
        # Reflect all existing tables automatically
        _metadata.reflect(bind=engine)
        logger.info(f"Reflected {len(_metadata.tables)} tables from database")
    return _metadata


def get_session_factory():
    """Get session factory."""
    global _SessionLocal
    if _SessionLocal is None:
        engine = get_engine()
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _SessionLocal


def get_session() -> Session:
    """Get database session."""
    SessionLocal = get_session_factory()
    return SessionLocal()


def refresh_metadata():
    """Refresh metadata to pick up schema changes."""
    global _metadata
    _metadata = None
    get_metadata()  # This will recreate and reflect


class DatabaseSession:
    """Context manager for database sessions."""
    
    def __init__(self):
        self.session = None
    
    def __enter__(self) -> Session:
        self.session = get_session()
        return self.session
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.session.rollback()
        else:
            self.session.commit()
        self.session.close()


# Convenience function for database operations
def with_session(func):
    """Decorator to provide database session to function."""
    def wrapper(*args, **kwargs):
        with DatabaseSession() as session:
            return func(session, *args, **kwargs)
    return wrapper