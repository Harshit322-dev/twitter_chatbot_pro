import logging
from datetime import datetime, timedelta

from twitter_bot.utils.twitter_api import TW
from twitter_bot.utils.database import DB
from twitter_bot.utils.openai_helper import generate_reply
from twitter_bot.bot.sentiment_analyzer import analyze_sentiment

from twitter_bot.config import config

logger = logging.getLogger(__name__)

_last_mention_id_key = "last_mention_id"


def _within_last_two_minutes(created_at) -> bool:
    try:
        # created_at is ISO8601; tweepy returns datetime
        return (datetime.utcnow() - created_at.replace(tzinfo=None)) <= timedelta(minutes=2)
    except Exception:
        return True


def handle_mention(mention, users_map):
    user_id = mention.author_id
    username = users_map.get(user_id).username if users_map and user_id in users_map else "user"

    text = mention.text
    intent_hint = None
    for kw in config.REPLY_KEYWORDS:
        if kw in text.lower():
            intent_hint = kw
            break

    profile = ""
    try:
        profile = users_map.get(user_id).description or ""
    except Exception:
        pass

    reply = generate_reply({
        "text": text,
        "username": username,
        "profile": profile,
        "intent_hint": intent_hint or "",
    })

    # Basic content validation
    reply = reply[:275]

    label, score = analyze_sentiment(text)

    reply_id = TW.reply_to_tweet(reply, str(mention.id))
    if reply_id:
        DB.log_interaction(str(user_id), username, str(mention.id), "mention", reply, score)
        logger.info("Replied to @%s mention %s with %s", username, mention.id, reply_id)
    else:
        logger.error("Failed to reply to mention %s", mention.id)


def poll_and_reply_mentions():
    try:
        since_id = DB.get_meta(_last_mention_id_key)
        resp = TW.get_mentions_since(since_id)
        if not resp or not resp.data:
            return

        # Build user map
        users_map = {u.id: u for u in (resp.includes.get("users", []) if resp.includes else [])}

        for m in sorted(resp.data, key=lambda x: x.id):
            if _within_last_two_minutes(m.created_at):
                handle_mention(m, users_map)
            DB.upsert_meta(_last_mention_id_key, str(m.id))
    except Exception:
        logger.exception("poll_and_reply_mentions failed")
