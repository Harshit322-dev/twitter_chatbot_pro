import sqlite3
import threading
from contextlib import contextmanager
from typing import Any, Iterable, Optional
import os
import logging
from datetime import datetime

from twitter_bot.config import config

logger = logging.getLogger(__name__)

class Database:
    _lock = threading.Lock()

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = db_path or config.DB_PATH
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with self.get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS tweets (
                    id INTEGER PRIMARY KEY,
                    tweet_id TEXT UNIQUE,
                    content TEXT,
                    type TEXT,
                    likes INTEGER DEFAULT 0,
                    retweets INTEGER DEFAULT 0,
                    replies INTEGER DEFAULT 0,
                    posted_at TIMESTAMP
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY,
                    user_id TEXT,
                    username TEXT,
                    tweet_id TEXT,
                    interaction_type TEXT,
                    our_response TEXT,
                    sentiment REAL,
                    created_at TIMESTAMP
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS analytics (
                    id INTEGER PRIMARY KEY,
                    date DATE UNIQUE,
                    followers_count INTEGER,
                    mentions_count INTEGER,
                    replies_sent INTEGER,
                    avg_sentiment REAL,
                    engagement_rate REAL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
                """
            )
            conn.commit()
            logger.debug("Database initialized at %s", self.db_path)

    @contextmanager
    def get_conn(self):
        with Database._lock:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            try:
                yield conn
            finally:
                conn.close()

    def execute(self, sql: str, params: Iterable[Any] = ()) -> None:
        with self.get_conn() as conn:
            cur = conn.cursor()
            cur.execute(sql, params)
            conn.commit()

    def query(self, sql: str, params: Iterable[Any] = ()) -> list[tuple]:
        with self.get_conn() as conn:
            cur = conn.cursor()
            cur.execute(sql, params)
            return cur.fetchall()

    def upsert_meta(self, key: str, value: str) -> None:
        self.execute(
            "INSERT INTO meta(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )

    def get_meta(self, key: str, default: Optional[str] = None) -> Optional[str]:
        rows = self.query("SELECT value FROM meta WHERE key=?", (key,))
        return rows[0][0] if rows else default

    def log_tweet(self, tweet_id: str, content: str, ttype: str, posted_at: Optional[datetime] = None) -> None:
        posted_at = posted_at or datetime.utcnow()
        self.execute(
            "INSERT OR IGNORE INTO tweets(tweet_id, content, type, posted_at) VALUES(?, ?, ?, ?)",
            (tweet_id, content, ttype, posted_at),
        )

    def log_interaction(self, user_id: str, username: str, tweet_id: str, interaction_type: str, our_response: str, sentiment: float) -> None:
        self.execute(
            "INSERT INTO interactions(user_id, username, tweet_id, interaction_type, our_response, sentiment, created_at) VALUES(?, ?, ?, ?, ?, ?, ?)",
            (user_id, username, tweet_id, interaction_type, our_response, sentiment, datetime.utcnow()),
        )

    def update_tweet_metrics(self, tweet_id: str, likes: int, retweets: int, replies: int) -> None:
        self.execute(
            "UPDATE tweets SET likes=?, retweets=?, replies=? WHERE tweet_id=?",
            (likes, retweets, replies, tweet_id),
        )

    def upsert_daily_analytics(self, date: str, followers_count: int, mentions_count: int, replies_sent: int, avg_sentiment: float, engagement_rate: float) -> None:
        self.execute(
            """
            INSERT INTO analytics(date, followers_count, mentions_count, replies_sent, avg_sentiment, engagement_rate)
            VALUES(?, ?, ?, ?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
                followers_count=excluded.followers_count,
                mentions_count=excluded.mentions_count,
                replies_sent=excluded.replies_sent,
                avg_sentiment=excluded.avg_sentiment,
                engagement_rate=excluded.engagement_rate
            """,
            (date, followers_count, mentions_count, replies_sent, avg_sentiment, engagement_rate),
        )

DB = Database()
