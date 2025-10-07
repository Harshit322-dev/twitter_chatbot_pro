import csv
import os
import logging
from datetime import datetime, timedelta

from twitter_bot.utils.database import DB
from twitter_bot.utils.twitter_api import TW
from twitter_bot.config import config, IST

logger = logging.getLogger(__name__)


def _calc_engagement_rate() -> float:
    rows = DB.query(
        "SELECT likes, retweets, replies FROM tweets WHERE posted_at >= ?",
        (datetime.utcnow() - timedelta(days=1),),
    )
    if not rows:
        return 0.0
    likes = sum(r[0] or 0 for r in rows)
    rts = sum(r[1] or 0 for r in rows)
    reps = sum(r[2] or 0 for r in rows)
    total = likes + rts + reps
    return round(total / max(1, len(rows)), 4)


def _avg_sentiment_today() -> float:
    rows = DB.query(
        "SELECT AVG(sentiment) FROM interactions WHERE created_at >= ?",
        (datetime.utcnow() - timedelta(days=1),),
    )
    return float(rows[0][0] or 0.0)


def generate_daily_report():
    try:
        today = datetime.now(IST).date()
        followers = TW.get_followers_count()
        mentions_count = len(
            DB.query(
                "SELECT id FROM interactions WHERE interaction_type='mention' AND created_at >= ?",
                (datetime.utcnow() - timedelta(days=1),),
            )
        )
        replies_sent = len(
            DB.query(
                "SELECT id FROM interactions WHERE created_at >= ?",
                (datetime.utcnow() - timedelta(days=1),),
            )
        )
        avg_sentiment = _avg_sentiment_today()
        engagement_rate = _calc_engagement_rate()

        DB.upsert_daily_analytics(
            str(today), followers, mentions_count, replies_sent, avg_sentiment, engagement_rate
        )

        # Alert on negative sentiment spike
        yesterday = str(today - timedelta(days=1))
        rows = DB.query("SELECT avg_sentiment FROM analytics WHERE date=?", (yesterday,))
        y_avg = float(rows[0][0]) if rows else 0.0
        if (avg_sentiment - y_avg) <= config.SENTIMENT_ALERT_THRESHOLD:
            logger.warning(
                "Negative sentiment spike detected: today=%.3f, yesterday=%.3f",
                avg_sentiment,
                y_avg,
            )

        # Export CSV
        csv_path = os.path.join(config.REPORTS_DIR, f"report_{today.strftime('%Y%m%d')}.csv")
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "date",
                    "followers_count",
                    "mentions_count",
                    "replies_sent",
                    "avg_sentiment",
                    "engagement_rate",
                ]
            )
            writer.writerow(
                [
                    str(today),
                    followers,
                    mentions_count,
                    replies_sent,
                    f"{avg_sentiment:.4f}",
                    f"{engagement_rate:.4f}",
                ]
            )
        logger.info("Daily report exported: %s", csv_path)
    except Exception:
        logger.exception("generate_daily_report failed")
