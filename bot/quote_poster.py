import json
import os
import random
import logging
from datetime import datetime
from textwrap import wrap
from PIL import Image, ImageDraw, ImageFont

from twitter_bot.config import config
from twitter_bot.utils.twitter_api import TW
from twitter_bot.utils.database import DB

logger = logging.getLogger(__name__)

CATEGORY_HASHTAGS = {
    "Business": ["#Business", "#Entrepreneur", "#Leadership"],
    "Success": ["#Success", "#Growth", "#Mindset"],
    "Motivation": ["#Motivation", "#Inspiration", "#DailyQuote"],
    "Technology": ["#Technology", "#AI", "#WebDev"],
}

FONTS = [
    ImageFont.load_default(),
]


def _load_quotes() -> list[dict]:
    with open(config.QUOTES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _choose_category() -> str:
    # Rotate categories daily
    cats = list(CATEGORY_HASHTAGS.keys())
    day_index = datetime.utcnow().toordinal() % len(cats)
    return cats[day_index]


def _pick_quote(quotes: list[dict], category: str) -> dict:
    filtered = [q for q in quotes if q.get("category") == category]
    random.shuffle(filtered)
    # Avoid recently used by checking in DB last 50 quote tweets
    recent = set(r[0] for r in DB.query("SELECT content FROM tweets WHERE type='quote' ORDER BY posted_at DESC LIMIT 50"))
    for q in filtered:
        text = f"{q['text']} — {q['author']}"
        if text not in recent:
            return q
    return filtered[0] if filtered else random.choice(quotes)


def _generate_image(quote_text: str, author: str) -> str:
    W, H = 1080, 1080
    bg_color = (242, 244, 248)
    text_color = (33, 37, 41)

    img = Image.new("RGB", (W, H), color=bg_color)
    draw = ImageDraw.Draw(img)

    title = "Daily Inspiration"
    font_title = FONTS[0]
    font_quote = FONTS[0]

    draw.text((40, 40), title, font=font_title, fill=(60, 64, 67))

    # Wrap text
    wrapped = wrap(quote_text, width=30)
    y = 180
    for line in wrapped:
        draw.text((80, y), line, font=font_quote, fill=text_color)
        y += 40

    draw.text((80, y + 20), f"— {author}", font=font_quote, fill=(90, 94, 97))

    path = os.path.join(config.MEDIA_DIR, f"quote_{int(datetime.utcnow().timestamp())}.jpg")
    img.save(path, format="JPEG", quality=90)
    return path


def post_daily_quote() -> None:
    try:
        quotes = _load_quotes()
        category = _choose_category()
        q = _pick_quote(quotes, category)
        text = f"{q['text']} — {q['author']}"
        hashtags = " ".join(CATEGORY_HASHTAGS.get(category, []) + ["#Quotes", "#Inspiration"])[:250]
        status_text = f"{text}\n\n{hashtags}"

        media_path = _generate_image(q["text"], q["author"])
        media_id = TW.upload_media(media_path)
        media_ids = [media_id] if media_id else None
        tweet_id = TW.post_tweet(status_text, media_ids=media_ids)
        if tweet_id:
            DB.log_tweet(tweet_id, text, "quote", datetime.utcnow())
            logger.info("Daily quote posted (%s) with id=%s", category, tweet_id)
        else:
            logger.error("Failed to post daily quote")
    except Exception:
        logger.exception("post_daily_quote failed")
