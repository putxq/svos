import os
import logging
from datetime import datetime

logger = logging.getLogger("svos.tools.social")


class SocialPostTool:
    """Post content to social media platforms."""

    name = "social_post"
    description = "Create and publish social media posts"
    allowed_roles = ["CMO", "CEO"]

    def __init__(self):
        self.twitter_api_key = os.getenv("TWITTER_API_KEY", "")
        self.twitter_api_secret = os.getenv("TWITTER_API_SECRET", "")
        self.twitter_access_token = os.getenv("TWITTER_ACCESS_TOKEN", "")
        self.twitter_access_secret = os.getenv("TWITTER_ACCESS_SECRET", "")
        self.configured = bool(
            self.twitter_api_key and self.twitter_api_secret and self.twitter_access_token and self.twitter_access_secret
        )
        self.post_log = []

        if self.configured:
            logger.info("SocialPostTool initialized with Twitter/X credentials")
        else:
            logger.warning("SocialPostTool: Missing credentials - dry-run mode")

    def post_twitter(self, content: str) -> dict:
        timestamp = datetime.utcnow().isoformat()

        if not self.configured:
            entry = {
                "status": "dry-run",
                "platform": "twitter",
                "content_preview": content[:100],
                "timestamp": timestamp,
                "message": "Set TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET.",
            }
            self.post_log.append(entry)
            logger.info(f"[DRY-RUN] Twitter post: {content[:80]}...")
            return entry

        try:
            import tweepy

            client = tweepy.Client(
                consumer_key=self.twitter_api_key,
                consumer_secret=self.twitter_api_secret,
                access_token=self.twitter_access_token,
                access_token_secret=self.twitter_access_secret,
            )
            response = client.create_tweet(text=content[:280])
            entry = {
                "status": "posted",
                "platform": "twitter",
                "tweet_id": str(response.data["id"]),
                "content_preview": content[:100],
                "timestamp": timestamp,
            }
            self.post_log.append(entry)
            logger.info(f"Twitter posted | ID: {response.data['id']}")
            return entry
        except Exception as e:
            logger.error(f"Twitter post failed: {e}")
            return {"status": "error", "platform": "twitter", "error": str(e)}

    def post(self, content: str, platform: str = "twitter") -> dict:
        if platform == "twitter":
            return self.post_twitter(content)
        return {"status": "error", "message": f"Platform '{platform}' not yet supported"}

    def get_post_log(self) -> list:
        return self.post_log
