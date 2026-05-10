"""Runtime configuration loaded from environment."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
CONTENT_DIR = ROOT / "content" / "posts"
SITE_DIR = ROOT / "site"
PROMPTS_DIR = ROOT / "prompts"
TEMPLATES_DIR = ROOT / "templates"


@dataclass
class Config:
    anthropic_api_key: str
    amazon_tag: str
    rakuten_id: str
    a8_template: str
    moshimo_id: str
    valuecommerce_template: str

    x_api_key: str
    x_api_secret: str
    x_access_token: str
    x_access_secret: str

    site_base_url: str
    site_title: str
    site_description: str
    site_custom_domain: str

    ga_id: str
    google_site_verification: str
    bing_site_verification: str

    discord_webhook_url: str

    articles_per_run: int
    model: str

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
            amazon_tag=os.environ.get("AMAZON_ASSOCIATE_TAG", ""),
            rakuten_id=os.environ.get("RAKUTEN_AFFILIATE_ID", ""),
            a8_template=os.environ.get("A8_LINK_TEMPLATE", ""),
            moshimo_id=os.environ.get("MOSHIMO_ID", ""),
            valuecommerce_template=os.environ.get("VALUECOMMERCE_LINK_TEMPLATE", ""),
            x_api_key=os.environ.get("X_API_KEY", ""),
            x_api_secret=os.environ.get("X_API_SECRET", ""),
            x_access_token=os.environ.get("X_ACCESS_TOKEN", ""),
            x_access_secret=os.environ.get("X_ACCESS_SECRET", ""),
            site_base_url=os.environ.get("SITE_BASE_URL", "https://example.github.io/affiliate").rstrip("/"),
            site_title=os.environ.get("SITE_TITLE", "AI Review Lab"),
            site_description=os.environ.get("SITE_DESCRIPTION", "AI-curated product reviews"),
            site_custom_domain=os.environ.get("SITE_CUSTOM_DOMAIN", "").strip(),
            ga_id=os.environ.get("GA_MEASUREMENT_ID", "").strip(),
            google_site_verification=os.environ.get("GOOGLE_SITE_VERIFICATION", "").strip(),
            bing_site_verification=os.environ.get("BING_SITE_VERIFICATION", "").strip(),
            discord_webhook_url=os.environ.get("DISCORD_WEBHOOK_URL", "").strip(),
            articles_per_run=int(os.environ.get("ARTICLES_PER_RUN", "2")),
            model=os.environ.get("MODEL", "claude-opus-4-7"),
        )

    def require_api_key(self) -> str:
        if not self.anthropic_api_key:
            raise SystemExit(
                "ANTHROPIC_API_KEY is required. Set it as a GitHub Actions secret."
            )
        return self.anthropic_api_key
