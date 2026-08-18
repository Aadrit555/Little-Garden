import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Real Postgres in production. Falls back to a real local SQLite file for
# dev/testing only — still a real database, real rows, real queries.
# No in-memory dict standing in as a "fake DB".
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "sqlite:///./mvp_dev.db",
)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
