"""Optional: auto-post a teaser tweet for each new article.

Skipped silently if X credentials are not configured.
"""
from __future__ import annotations

from typing import Any

from .config import Config


def maybe_post_to_x(cfg: Config, article: dict[str, Any], post_url: str) -> bool:
    if not all([cfg.x_api_key, cfg.x_api_secret, cfg.x_access_token, cfg.x_access_secret]):
        return False
    try:
        import tweepy  # imported lazily so missing deps don't break headless runs
    except ImportError:
        return False

    title = article.get("title", "新着記事")
    desc = article.get("description", "")
    tags = article.get("tags") or []
    hashtags = " ".join(f"#{t}" for t in tags[:3])

    # X has a 280 char limit; trim to fit URL + hashtags + ellipsis.
    budget = 280 - len(post_url) - len(hashtags) - 6
    body = (desc or title)[:max(40, budget)]
    text = f"{title}\n{body}\n{post_url} {hashtags}".strip()

    try:
        client = tweepy.Client(
            consumer_key=cfg.x_api_key,
            consumer_secret=cfg.x_api_secret,
            access_token=cfg.x_access_token,
            access_token_secret=cfg.x_access_secret,
        )
        client.create_tweet(text=text)
        return True
    except Exception as e:
        print(f"[social] X post failed: {e}")
        return False


def maybe_notify_discord(cfg: Config, article: dict[str, Any], post_url: str) -> bool:
    """POST a simple message to a Discord webhook. Best-effort, never raises."""
    url = (cfg.discord_webhook_url or "").strip()
    if not url:
        return False
    try:
        import requests  # already in requirements.txt
    except ImportError:
        return False

    title = article.get("title", "新着記事")
    desc = article.get("description", "") or ""
    # Discord caps content at 2000 chars; keep well under.
    content = f"**新着記事**: {title}\n{desc[:300]}\n{post_url}"[:1900]
    payload = {"content": content}

    try:
        r = requests.post(url, json=payload, timeout=10)
        if 200 <= r.status_code < 300:
            return True
        print(f"[social] Discord webhook returned {r.status_code}: {r.text[:200]}")
        return False
    except Exception as e:
        print(f"[social] Discord webhook failed: {e}")
        return False
