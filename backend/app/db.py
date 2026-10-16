import os
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


_development_database = Path(__file__).resolve().parents[2] / "data" / "cathedra.db"
_data_directory = os.environ.get("CATHEDRA_DATA_DIR")
DB_PATH = (
    Path(_data_directory).expanduser().resolve() / "cathedra.db"
    if _data_directory
    else _development_database
)
DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,
    hide_parameters=True,
)


@event.listens_for(Engine, "connect")
def enforce_foreign_keys(connection, _) -> None:
    from app.current_grant import name_prefix_matches
    from app.record_text import unicode_contains

    connection.create_function("name_prefix_matches", 2, name_prefix_matches, deterministic=True)
    connection.create_function("unicode_contains", 2, unicode_contains, deterministic=True)
    connection.create_function(
        "name_sort_key", 1, lambda value: (value or "").strip().casefold(), deterministic=True
    )
    cursor = connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
    finally:
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
