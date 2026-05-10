"""Save generated articles to the content/posts directory as Markdown."""
from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

import frontmatter
from slugify import slugify

from .config import CONTENT_DIR


def save_post(article: dict[str, Any], body: str) -> Path:
    today = dt.date.today()
    title = article.get("title", "untitled")
    # slugify falls back to a transliterated form for Japanese; if that yields
    # an empty string we use a date+sequence fallback.
    slug = slugify(title) or f"post-{today.isoformat()}"
    filename = f"{today.isoformat()}-{slug}.md"

    CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    path = CONTENT_DIR / filename

    post = frontmatter.Post(
        body,
        title=title,
        date=today.isoformat(),
        description=article.get("description", ""),
        tags=article.get("tags", []),
        category=article.get("category", ""),
        slug=slug,
    )
    with path.open("wb") as f:
        frontmatter.dump(post, f)
    return path
