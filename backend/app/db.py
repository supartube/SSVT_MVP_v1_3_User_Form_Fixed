import sqlite3
from contextlib import contextmanager
from .config import settings

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS users (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 email TEXT NOT NULL UNIQUE COLLATE NOCASE,
 username TEXT NOT NULL UNIQUE COLLATE NOCASE,
 password_hash TEXT NOT NULL,
 display_name TEXT NOT NULL,
 role TEXT NOT NULL DEFAULT 'creator',
 date_of_birth TEXT NOT NULL DEFAULT '',
 terms_accepted INTEGER NOT NULL DEFAULT 0,
 account_status TEXT NOT NULL DEFAULT 'active',
 account_note TEXT NOT NULL DEFAULT '',
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS videos (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 title TEXT NOT NULL,
 description TEXT NOT NULL DEFAULT '',
 original_filename TEXT NOT NULL,
 stored_filename TEXT NOT NULL,
 file_size INTEGER NOT NULL,
 content_type TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'pending_review',
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS moderation_actions (
 id INTEGER PRIMARY KEY AUTOINCREMENT, actor TEXT NOT NULL, target_user_id INTEGER, target_video_id INTEGER, action TEXT NOT NULL, note TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_videos_status_created ON videos(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_videos_owner_created ON videos(owner_id, created_at DESC);
"""

def connect():
    conn = sqlite3.connect(settings.database_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    with connect() as conn:
        conn.executescript(SCHEMA)
        # Lightweight migrations for existing prototype databases.
        cols = {r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()}
        for name, definition in {
            "date_of_birth": "TEXT NOT NULL DEFAULT ''",
            "terms_accepted": "INTEGER NOT NULL DEFAULT 0",
            "account_status": "TEXT NOT NULL DEFAULT 'active'",
            "account_note": "TEXT NOT NULL DEFAULT ''",
        }.items():
            if name not in cols:
                conn.execute(f"ALTER TABLE users ADD COLUMN {name} {definition}")

@contextmanager
def db_session():
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
