import os
from dataclasses import dataclass
from dotenv import load_dotenv
import pytz

load_dotenv()

IST = pytz.timezone("Asia/Kolkata")

@dataclass
class Config:
    # Times and Scheduling
    POST_TIME: str = os.getenv("POST_TIME", "09:00")  # HH:MM 24h IST
    MAX_REPLIES_PER_HOUR: int = int(os.getenv("MAX_REPLIES_PER_HOUR", "30"))
    HASHTAGS_TO_MONITOR: list[str] = os.getenv(
        "HASHTAGS_TO_MONITOR", "freelancing,webdevelopment,AItools"
    ).split(",")
    REPLY_KEYWORDS: list[str] = os.getenv(
        "REPLY_KEYWORDS", "pricing,cost,hire,available"
    ).split(",")
    SENTIMENT_ALERT_THRESHOLD: float = float(os.getenv("SENTIMENT_ALERT_THRESHOLD", "-0.5"))

    # Models
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # Paths
    BASE_DIR: str = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR: str = os.path.join(BASE_DIR, "data")
    DB_PATH: str = os.path.join(DATA_DIR, "bot.db")
    REPORTS_DIR: str = os.path.join(DATA_DIR, "reports")
    QUOTES_PATH: str = os.path.join(DATA_DIR, "quotes.json")
    MEDIA_DIR: str = os.path.join(DATA_DIR, "media")

    # API Keys
    TWITTER_API_KEY: str = os.getenv("TWITTER_API_KEY", "")
    TWITTER_API_SECRET: str = os.getenv("TWITTER_API_SECRET", "")
    TWITTER_ACCESS_TOKEN: str = os.getenv("TWITTER_ACCESS_TOKEN", "")
    TWITTER_ACCESS_TOKEN_SECRET: str = os.getenv("TWITTER_ACCESS_TOKEN_SECRET", "")
    TWITTER_BEARER_TOKEN: str = os.getenv("TWITTER_BEARER_TOKEN", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")


config = Config()

# Ensure data directories exist
os.makedirs(config.DATA_DIR, exist_ok=True)
os.makedirs(config.REPORTS_DIR, exist_ok=True)
os.makedirs(config.MEDIA_DIR, exist_ok=True)
