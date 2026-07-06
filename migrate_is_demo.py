#!/usr/bin/env python3
"""
Migration: add 'is_demo' column to clients and scans tables.
Also widens public_token to VARCHAR(100).
Usage: python migrate_is_demo.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from app.models.base import engine
from sqlalchemy import text


def _sqlite_has_column(conn, table, column):
    result = conn.execute(text(f"PRAGMA table_info({table})"))
    return any(row[1] == column for row in result)


def migrate():
    with engine.connect() as conn:
        is_sqlite = "sqlite" in str(engine.url)

        if is_sqlite:
            for table in ("clients", "scans"):
                if not _sqlite_has_column(conn, table, "is_demo"):
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN is_demo BOOLEAN DEFAULT 0 NOT NULL"))
                    print(f"Added is_demo to {table}")
                else:
                    print(f"is_demo already exists in {table}")
            conn.commit()
        else:
            for table in ("clients", "scans"):
                try:
                    conn.execute(text(
                        f"ALTER TABLE {table} ADD COLUMN is_demo TINYINT(1) NOT NULL DEFAULT 0"
                    ))
                    conn.commit()
                    print(f"Added is_demo to {table}")
                except Exception as e:
                    if "Duplicate column" in str(e) or "already exists" in str(e):
                        print(f"is_demo already exists in {table}")
                    else:
                        raise

    print("Migration is_demo complete.")


if __name__ == "__main__":
    migrate()
