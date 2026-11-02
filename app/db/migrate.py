"""Tiny forward-only migrations for the SQLite development database.

The project has no Alembic setup yet; ``create_all`` creates new tables but does
not add columns to existing ones. This keeps an existing ``autoreporter.db``
usable after the report-item schema grew ``done``, ``confidence`` and
``position`` columns. Other databases must be migrated by hand.
"""

from __future__ import annotations

from typing import Dict, List

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

_ADDITIONS: Dict[str, Dict[str, str]] = {
    "report_items": {
        "done": "BOOLEAN NOT NULL DEFAULT 0",
        "confidence": "FLOAT",
        "position": "INTEGER NOT NULL DEFAULT 0",
    },
}


def ensure_schema(engine: Engine) -> List[str]:
    """Add missing columns, returning what was applied. Safe to call on every start."""
    if engine.dialect.name != "sqlite":
        return []

    applied: List[str] = []
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    with engine.begin() as connection:
        for table, columns in _ADDITIONS.items():
            if table not in tables:
                continue
            existing = {column["name"] for column in inspector.get_columns(table)}
            for name, ddl in columns.items():
                if name in existing:
                    continue
                connection.execute(text(f'ALTER TABLE "{table}" ADD COLUMN "{name}" {ddl}'))
                applied.append(f"{table}.{name}")
    return applied
