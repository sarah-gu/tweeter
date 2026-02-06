"""SQLite-backed tweet store for deduplication and archiving."""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path

from finxnews.models import TweetItem

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS tweets (
    tweet_id   TEXT PRIMARY KEY,
    text       TEXT NOT NULL,
    author     TEXT NOT NULL DEFAULT '',
    created_at TEXT,
    metrics    TEXT NOT NULL DEFAULT '{}',
    query_group TEXT NOT NULL DEFAULT '',
    score      REAL NOT NULL DEFAULT 0.0,
    inserted_at TEXT NOT NULL
);
"""


class TweetStore:
    """Append-only tweet archive backed by SQLite."""

    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db_path = db_path
        self._init_db()

    # ── public ──────────────────────────────────────────────────────────

    def seen_ids(self) -> set[str]:
        """Return the set of tweet IDs already stored."""
        con = self._connect()
        cur = con.execute("SELECT tweet_id FROM tweets")
        ids = {row[0] for row in cur.fetchall()}
        con.close()
        return ids

    def insert(self, item: TweetItem) -> bool:
        """Insert a tweet; return True if it was new (not a duplicate)."""
        con = self._connect()
        try:
            con.execute(
                """
                INSERT OR IGNORE INTO tweets
                    (tweet_id, text, author, created_at, metrics, query_group, score, inserted_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.tweet_id,
                    item.text,
                    item.author_username,
                    item.created_at.isoformat() if item.created_at else None,
                    json.dumps(item.metrics.model_dump()),
                    item.query_group,
                    item.score,
                    datetime.utcnow().isoformat(),
                ),
            )
            con.commit()
            return con.total_changes > 0
        finally:
            con.close()

    def insert_many(self, items: list[TweetItem]) -> int:
        """Insert multiple tweets; return count of newly inserted rows."""
        con = self._connect()
        now = datetime.utcnow().isoformat()
        rows = [
            (
                item.tweet_id,
                item.text,
                item.author_username,
                item.created_at.isoformat() if item.created_at else None,
                json.dumps(item.metrics.model_dump()),
                item.query_group,
                item.score,
                now,
            )
            for item in items
        ]
        before = self._count(con)
        con.executemany(
            """
            INSERT OR IGNORE INTO tweets
                (tweet_id, text, author, created_at, metrics, query_group, score, inserted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        con.commit()
        after = self._count(con)
        con.close()
        return after - before

    # ── private ─────────────────────────────────────────────────────────

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self._db_path))

    def _init_db(self) -> None:
        con = self._connect()
        con.executescript(_SCHEMA)
        con.close()

    @staticmethod
    def _count(con: sqlite3.Connection) -> int:
        cur = con.execute("SELECT COUNT(*) FROM tweets")
        return cur.fetchone()[0]  # type: ignore[no-any-return]
