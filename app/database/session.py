"""Shared SQLAlchemy session dependency for FastAPI routes.

This compatibility module centralizes the get_db dependency used by v13
public routes and guarantees that every SessionLocal instance is closed.
"""
from collections.abc import Generator

from sqlalchemy.orm import Session

from app.database.database import SessionLocal


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
