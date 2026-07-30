"""SQLAlchemy engine and session factory construction for local SQLite persistence."""

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import sessionmaker


def build_database(database_url: str) -> tuple[Engine, sessionmaker]:
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite:") else {}
    engine = create_engine(database_url, connect_args=connect_args)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    return engine, session_factory
