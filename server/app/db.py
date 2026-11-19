import json
import os
import sqlite3
import threading
import time
from datetime import datetime, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    name TEXT PRIMARY KEY,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    from_user TEXT NOT NULL,
    origin TEXT NOT NULL,
    lamport INTEGER NOT NULL,
    sent_at TEXT NOT NULL,
    body TEXT NOT NULL,
    received_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_order ON messages (lamport, origin);

CREATE TABLE IF NOT EXISTS pending (
    id TEXT PRIMARY KEY,
    payload TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    next_attempt_at REAL NOT NULL DEFAULT 0,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Database:
    def __init__(self, path: str) -> None:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.executescript(SCHEMA)
            self._conn.commit()

    def create_user(self, name: str) -> bool:
        with self._lock:
            try:
                self._conn.execute(
                    "INSERT INTO users (name, created_at) VALUES (?, ?)",
                    (name, utc_now()),
                )
                self._conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def list_users(self) -> list[str]:
        with self._lock:
            rows = self._conn.execute("SELECT name FROM users ORDER BY name").fetchall()
        return [r["name"] for r in rows]

    def has_message(self, message_id: str) -> bool:
        with self._lock:
            row = self._conn.execute(
                "SELECT 1 FROM messages WHERE id = ?", (message_id,)
            ).fetchone()
        return row is not None

    def insert_message(
        self, message_id: str, from_user: str, origin: str, lamport: int, sent_at: str, body: str
    ) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR IGNORE INTO messages (id, from_user, origin, lamport, sent_at, body, received_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (message_id, from_user, origin, lamport, sent_at, body, utc_now()),
            )
            self._conn.commit()

    def list_messages(self) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, from_user, origin, lamport, sent_at, body "
                "FROM messages ORDER BY lamport, origin"
            ).fetchall()
        return [dict(r) for r in rows]

    def max_lamport(self) -> int:
        with self._lock:
            row = self._conn.execute("SELECT COALESCE(MAX(lamport), 0) AS m FROM messages").fetchone()
        return row["m"]

    def enqueue_pending(self, message_id: str, payload: dict) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO pending (id, payload, attempts, next_attempt_at, created_at) "
                "VALUES (?, ?, 0, 0, ?)",
                (message_id, json.dumps(payload), time.time()),
            )
            self._conn.commit()

    def next_pending(self) -> dict | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT id, payload, attempts, next_attempt_at FROM pending "
                "WHERE next_attempt_at <= ? ORDER BY created_at LIMIT 1",
                (time.time(),),
            ).fetchone()
        if row is None:
            return None
        return {
            "id": row["id"],
            "payload": json.loads(row["payload"]),
            "attempts": row["attempts"],
        }

    def mark_pending_attempt(self, message_id: str, attempts: int, next_attempt_at: float) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE pending SET attempts = ?, next_attempt_at = ? WHERE id = ?",
                (attempts, next_attempt_at, message_id),
            )
            self._conn.commit()

    def remove_pending(self, message_id: str) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM pending WHERE id = ?", (message_id,))
            self._conn.commit()

    def pending_count(self) -> int:
        with self._lock:
            row = self._conn.execute("SELECT COUNT(*) AS c FROM pending").fetchone()
        return row["c"]
