import sqlite3
import os
from app.config import settings

def get_db():
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS sync_state (
                source_item_id TEXT PRIMARY KEY,
                source_etag TEXT,
                source_path TEXT,
                destination_path TEXT,
                last_status TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS system_state (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        conn.commit()

def get_delta_token() -> str:
    with get_db() as conn:
        cur = conn.execute("SELECT value FROM system_state WHERE key = 'delta_token'")
        row = cur.fetchone()
        return row['value'] if row else None

def set_delta_token(token: str):
    with get_db() as conn:
        conn.execute("REPLACE INTO system_state (key, value) VALUES ('delta_token', ?)", (token,))
        conn.commit()

def record_sync(source_id: str, etag: str, src_path: str, dest_path: str, status: str):
    with get_db() as conn:
        conn.execute('''
            REPLACE INTO sync_state (source_item_id, source_etag, source_path, destination_path, last_status, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (source_id, etag, src_path, dest_path, status))
        conn.commit()

def get_sync_record(source_id: str):
    with get_db() as conn:
        cur = conn.execute("SELECT * FROM sync_state WHERE source_item_id = ?", (source_id,))
        return cur.fetchone()

init_db()
