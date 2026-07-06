#!/usr/bin/env python3
"""
Migration: add 'sector' column to clients table.
Run once after updating the model.
Usage: python migrate_sector.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from app.models.base import engine
from sqlalchemy import text

def migrate():
    with engine.connect() as conn:
        # Check if column already exists
        if "sqlite" in str(engine.url):
            result = conn.execute(text("PRAGMA table_info(clients)"))
            columns = [row[1] for row in result]
            if "sector" in columns:
                print("Column 'sector' already exists — nothing to do.")
                return
            conn.execute(text("ALTER TABLE clients ADD COLUMN sector VARCHAR(100) DEFAULT ''"))
            conn.commit()
            print("Migration complete: added 'sector' column to clients.")
        else:
            # MySQL
            try:
                conn.execute(text(
                    "ALTER TABLE clients ADD COLUMN sector VARCHAR(100) DEFAULT '' NOT NULL"
                ))
                conn.commit()
                print("Migration complete: added 'sector' column to clients.")
            except Exception as e:
                if "Duplicate column" in str(e) or "already exists" in str(e):
                    print("Column 'sector' already exists — nothing to do.")
                else:
                    raise

if __name__ == "__main__":
    migrate()
