from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import json

from src.config import settings
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)

class DatabaseManager:
    def __init__(self):
        # Handle SecretStr if DB_URL is a secret
        if isinstance(settings.DB_URL, str):
            self.db_url = settings.DB_URL
        else:
            self.db_url = settings.DB_URL.get_secret_value()

        if not self.db_url:
            logger.critical("DB_URL is missing in settings!")
            raise ValueError("No db_url is specified")

        # 1. Industrial Tuning: Connection Pooling
        # 'pool_pre_ping=True': The engine checks if the DB is alive before using a connection.
        connect_args = {}
        # SQLite specific check removed or kept conditional just in case
        if "sqlite" in self.db_url:
             connect_args['check_same_thread'] = False

        self.engine = create_engine(
            self.db_url,
            pool_pre_ping=True,
            connect_args=connect_args,
            json_serializer=lambda obj: json.dumps(obj, ensure_ascii=False),
            # Postgres Pooling Tuning
            pool_size=10, 
            max_overflow=20
        )

        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )

    def get_db(self):
        """
        Dependency generator.
        Guarantees the session is closed even if your code crashes.
        """
        session = self.SessionLocal()
        try:
            yield session
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()

db_manager = DatabaseManager()

# Export engine and SessionLocal for usage in other modules (e.g. repository)
engine = db_manager.engine
SessionLocal = db_manager.SessionLocal

# This is often used as a FastAPI dependency
def get_db():
    return db_manager.get_db()

