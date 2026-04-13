"""
Database setup using SQLite via the standard library.
SQLite is chosen for:
  - Zero-config, file-based persistence (survives restarts)
  - Built into Python standard library (no extra deps)
  - ACID compliant — safe for concurrent reads/writes at this scale
  - Easy to migrate to Postgres later via SQLAlchemy dialect swap

Money is stored as INTEGER (paise/cents) to avoid floating-point errors.
All arithmetic is done in integer paise; only the API layer converts to/from Decimal strings.
"""

import sqlite3
import os

# DB_PATH = os.environ.get("/app/expenses.db", "expenses.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect('C:\\Users\\dapatil\\Downloads\\files\\backend\\example.db')
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")   # Better concurrent read perf
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id           TEXT PRIMARY KEY,
                idempotency_key TEXT UNIQUE,          -- client-supplied key for safe retries
                amount_paise INTEGER NOT NULL CHECK(amount_paise > 0),
                category     TEXT NOT NULL,
                description  TEXT NOT NULL DEFAULT '',
                date         TEXT NOT NULL,            -- ISO 8601 date string YYYY-MM-DD
                created_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(category)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(date DESC)
        """)
        conn.commit()
