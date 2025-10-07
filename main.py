import logging
import os
from datetime import time

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from twitter_bot.config import config, IST
from twitter_bot.bot.quote_poster import post_daily_quote
from twitter_bot.bot.reply_handler import poll_and_reply_mentions
from twitter_bot.bot.hashtag_monitor import monitor_hashtags
from twitter_bot.bot.analytics import generate_daily_report
from twitter_bot.utils.twitter_api import TW
from twitter_bot.utils.database import DB


def configure_logging():
    os.makedirs(os.path.join(config.DATA_DIR, "logs"), exist_ok=True)
    log_path = os.path.join(config.DATA_DIR, "logs", "bot.log")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.FileHandler(log_path, encoding="utf-8"), logging.StreamHandler()],
    )


def update_recent_tweet_metrics():
    try:
        rows = DB.query("SELECT tweet_id FROM tweets WHERE posted_at >= datetime('now','-2 days')")
        for (tid,) in rows:
            likes, rts, reps = TW.get_tweet_metrics(tid)
            DB.update_tweet_metrics(tid, likes, rts, reps)
    except Exception:
        logging.getLogger(__name__).exception("update_recent_tweet_metrics failed")


def schedule_jobs():
    scheduler = BackgroundScheduler(timezone=IST)

    # Daily quote at POST_TIME IST
    hh, mm = map(int, config.POST_TIME.split(":"))
    scheduler.add_job(post_daily_quote, CronTrigger(hour=hh, minute=mm))

    # Mentions poll every minute
    scheduler.add_job(poll_and_reply_mentions, IntervalTrigger(minutes=1))

    # Hashtag monitor every 10 minutes
    scheduler.add_job(monitor_hashtags, IntervalTrigger(minutes=10))

    # Update tweet metrics every 30 minutes
    scheduler.add_job(update_recent_tweet_metrics, IntervalTrigger(minutes=30))

    # Daily report at 23:59 IST
    scheduler.add_job(generate_daily_report, CronTrigger(hour=23, minute=59))

    scheduler.start()
    return scheduler


def main():
    configure_logging()
    logging.getLogger(__name__).info("Starting Twitter bot")
    schedule_jobs()

    # Keep the script alive
    try:
        import time as _t
        while True:
            _t.sleep(5)
    except KeyboardInterrupt:
        logging.getLogger(__name__).info("Shutting down...")


if __name__ == "__main__":
    main()
