import logging
from datetime import datetime, timedelta

from twitter_bot.utils.twitter_api import TW
from twitter_bot.utils.database import DB
from twitter_bot.utils.openai_helper import generate_reply
from twitter_bot.bot.sentiment_analyzer import analyze_sentiment
from twitter_bot.config import config

logger = logging.getLogger(__name__)


def _score_tweet(tweet, users_map) -> int:
    # Score by follower count, engagement, and bio keywords
    user = users_map.get(tweet.author_id)
    followers = 0
    bio = ""
    if user and hasattr(user, "public_metrics"):
        followers = user.public_metrics.get("followers_count", 0)
        bio = (user.description or "").lower()

    metrics = tweet.public_metrics or {}
    engagement = metrics.get("like_count", 0) + 2 * metrics.get("retweet_count", 0)

    bonus = 0
    for kw in ["startup", "founder", "hiring", "freelance", "website", "ai", "automation", "lead"]:
        if kw in bio:
            bonus += 5

    score = min(100, int(followers / 100) + engagement + bonus)
    return score


def monitor_hashtags(hashtags: list[str] | None = None):
    hashtags = hashtags or config.HASHTAGS_TO_MONITOR
    try:
        query = " OR ".join([f"#{h}" for h in hashtags]) + " -is:retweet -is:reply lang:en"
        resp = TW.search_recent_tweets(query=query, max_results=50)
        if not resp or not resp.data:
            return
        users_map = {u.id: u for u in (resp.includes.get("users", []) if resp.includes else [])}

        interactions_this_hour = int(DB.get_meta("interactions_this_hour", "0"))
        reset_at = DB.get_meta("interactions_reset_at")
        if not reset_at or datetime.utcnow() > datetime.fromisoformat(reset_at):
            interactions_this_hour = 0
            DB.upsert_meta("interactions_this_hour", "0")
            DB.upsert_meta("interactions_reset_at", (datetime.utcnow() + timedelta(hours=1)).isoformat())

        for t in resp.data:
            if interactions_this_hour >= 50:  # hard cap to avoid spam
                break
            score = _score_tweet(t, users_map)
            if score < 20:
                continue

            # Like and optionally retweet
            TW.like_tweet(str(t.id))
            if score >= 60:
                TW.retweet(str(t.id))

            # Personalized reply for high-score
            if score >= 70 and interactions_this_hour < config.MAX_REPLIES_PER_HOUR:
                reply = generate_reply({
                    "text": t.text,
                    "username": users_map.get(t.author_id).username if t.author_id in users_map else "there",
                    "profile": users_map.get(t.author_id).description if t.author_id in users_map else "",
                    "intent_hint": "lead_generation",
                })
                reply = reply[:275]
                label, sent = analyze_sentiment(t.text)
                reply_id = TW.reply_to_tweet(reply, str(t.id))
                if reply_id:
                    DB.log_interaction(str(t.author_id), users_map.get(t.author_id).username if t.author_id in users_map else "", str(t.id), "hashtag", reply, sent)
                    interactions_this_hour += 1
                    DB.upsert_meta("interactions_this_hour", str(interactions_this_hour))

    except Exception:
        logger.exception("monitor_hashtags failed")
