"""
Generic SQLAlchemy models that work with any database schema automatically.
Uses reflection to understand the database structure at runtime.
"""
from .base import (
    Base, 
    get_engine, 
    get_session, 
    get_metadata,
    refresh_metadata,
    DatabaseSession,
    with_session
)

__all__ = [
    'Base',
    'get_engine',
    'get_session', 
    'get_metadata',
    'refresh_metadata',
    'DatabaseSession',
    'with_session'
]