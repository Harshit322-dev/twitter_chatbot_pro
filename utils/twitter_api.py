import time
import logging
from typing import List, Optional
import tweepy

from twitter_bot.config import config

logger = logging.getLogger(__name__)

class TwitterAPI:
    def __init__(self):
        # v2 client
        self.client = tweepy.Client(
            bearer_token=config.TWITTER_BEARER_TOKEN,
            consumer_key=config.TWITTER_API_KEY,
            consumer_secret=config.TWITTER_API_SECRET,
            access_token=config.TWITTER_ACCESS_TOKEN,
            access_token_secret=config.TWITTER_ACCESS_TOKEN_SECRET,
            wait_on_rate_limit=True,
        )
        # v1.1 API for media upload and some endpoints
        auth = tweepy.OAuth1UserHandler(
            config.TWITTER_API_KEY,
            config.TWITTER_API_SECRET,
            config.TWITTER_ACCESS_TOKEN,
            config.TWITTER_ACCESS_TOKEN_SECRET,
        )
        self.api_v1 = tweepy.API(auth, wait_on_rate_limit=True)

    def _retry(self, func, *args, retries: int = 3, backoff: float = 2.0, **kwargs):
        for attempt in range(retries):
            try:
                return func(*args, **kwargs)
            except tweepy.TooManyRequests as e:
                sleep_for = int(e.retry_after) if hasattr(e, 'retry_after') and e.retry_after else 900
                logger.warning("Rate limited. Sleeping for %ss", sleep_for)
                time.sleep(sleep_for)
            except Exception as e:
                logger.exception("Twitter API error on attempt %d/%d: %s", attempt + 1, retries, e)
                time.sleep(backoff ** attempt)
        raise RuntimeError("Twitter API failed after retries")

    def upload_media(self, media_path: str) -> Optional[str]:
        try:
            media = self._retry(self.api_v1.media_upload, filename=media_path)
            return media.media_id_string
        except Exception:
            logger.exception("Failed to upload media: %s", media_path)
            return None

    def post_tweet(self, text: str, media_ids: Optional[List[str]] = None) -> Optional[str]:
        try:
            if media_ids:
                resp = self._retry(self.client.create_tweet, text=text, media_ids=media_ids)
            else:
                resp = self._retry(self.client.create_tweet, text=text)
            tweet_id = str(resp.data.get('id')) if resp and resp.data else None
            logger.info("Posted tweet id=%s", tweet_id)
            return tweet_id
        except Exception:
            logger.exception("Failed to post tweet")
            return None

    def reply_to_tweet(self, text: str, in_reply_to_tweet_id: str) -> Optional[str]:
        try:
            resp = self._retry(self.client.create_tweet, text=text, in_reply_to_tweet_id=in_reply_to_tweet_id)
            return str(resp.data.get('id')) if resp and resp.data else None
        except Exception:
            logger.exception("Failed to post reply")
            return None

    def like_tweet(self, tweet_id: str) -> bool:
        try:
            me = self._retry(self.client.get_me)
            self._retry(self.client.like, me.data.id, tweet_id)
            return True
        except Exception:
            logger.exception("Failed to like tweet %s", tweet_id)
            return False

    def retweet(self, tweet_id: str) -> bool:
        try:
            me = self._retry(self.client.get_me)
            self._retry(self.client.retweet, me.data.id, tweet_id)
            return True
        except Exception:
            logger.exception("Failed to retweet %s", tweet_id)
            return False

    def search_recent_tweets(self, query: str, max_results: int = 25):
        try:
            return self._retry(
                self.client.search_recent_tweets,
                query=query,
                tweet_fields=["author_id", "created_at", "public_metrics"],
                user_fields=["username", "public_metrics", "description"],
                expansions=["author_id"],
                max_results=max_results,
            )
        except Exception:
            logger.exception("search_recent_tweets failed for query=%s", query)
            return None

    def get_mentions_since(self, since_id: Optional[str] = None, max_results: int = 50):
        try:
            me = self._retry(self.client.get_me)
            return self._retry(
                self.client.get_users_mentions,
                id=me.data.id,
                since_id=since_id,
                tweet_fields=["author_id", "created_at", "public_metrics", "conversation_id"],
                user_fields=["username"],
                expansions=["author_id"],
                max_results=max_results,
            )
        except Exception:
            logger.exception("get_mentions_since failed")
            return None

    def get_followers_count(self) -> int:
        try:
            me = self._retry(self.client.get_me, user_fields=["public_metrics"])
            return int(me.data.public_metrics.get("followers_count", 0))
        except Exception:
            logger.exception("get_followers_count failed")
            return 0

    def get_tweet_metrics(self, tweet_id: str) -> tuple[int, int, int]:
        try:
            resp = self._retry(self.client.get_tweet, id=tweet_id, tweet_fields=["public_metrics"])
            metrics = resp.data.public_metrics if resp and resp.data else {}
            return (
                int(metrics.get("like_count", 0)),
                int(metrics.get("retweet_count", 0)),
                int(metrics.get("reply_count", 0)),
            )
        except Exception:
            logger.exception("get_tweet_metrics failed for %s", tweet_id)
            return (0, 0, 0)

TW = TwitterAPI()
