"""Shared application state container.

Replaces global variables with a centralized state class that can be
imported by all modules. Uses class-level attributes for singleton behavior.
"""

from typing import Dict, Any, Optional
from lib.vector_store import VectorStore
from lib.database import Database, SessionRepository


class AppState:
    """Shared application state container."""

    vector_store: VectorStore = None
    db: Database = None
    session_repo: SessionRepository = None
    current_session_id: str = None
    detected_activities: Dict[str, Dict[str, Any]] = {}
    config = None

    @classmethod
    def init(cls, config):
        """Initialize state with configuration."""
        cls.config = config

    @classmethod
    def get_vector_store(cls) -> VectorStore:
        """Get or create vector store instance."""
        if cls.vector_store is None:
            cls.vector_store = VectorStore(cls.config.qdrant)
        return cls.vector_store

    @classmethod
    def get_database(cls) -> Database:
        """Get or create database instance."""
        if cls.db is None:
            cls.db = Database(cls.config.postgres)
        return cls.db

    @classmethod
    def get_session_repo(cls) -> SessionRepository:
        """Get or create session repository instance."""
        if cls.session_repo is None:
            cls.session_repo = SessionRepository(cls.get_database())
        return cls.session_repo

    @classmethod
    def get_current_activity_label(cls, session_id: str) -> Optional[str]:
        """
        Get activity label for a session.

        Prioritizes frontend-detected activity over session default.

        Args:
            session_id: Session ID to get activity for

        Returns:
            Activity label string or None
        """
        if session_id in cls.detected_activities:
            return cls.detected_activities[session_id]["activity"]

        repo = cls.get_session_repo()
        session = repo.get(session_id)
        return session.activity_type if session else None
