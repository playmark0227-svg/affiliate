"""Pre-flight check: validates configuration and points out gaps.

Run with: python -m affiliate.check
"""
from __future__ import annotations

import os
import sys

from .config import Config


GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
RESET = "\033[0m"


def _ok(msg: str) -> None:
    print(f"{GREEN}✓{RESET} {msg}")


def _warn(msg: str) -> None:
    print(f"{YELLOW}⚠{RESET} {msg}")


def _bad(msg: str) -> None:
    print(f"{RED}✗{RESET} {msg}")


def main() -> int:
    cfg = Config.from_env()
    fatal = 0
    warnings = 0

    print("=== Required ===")
    if cfg.anthropic_api_key:
        _ok("ANTHROPIC_API_KEY is set")
    else:
        _bad("ANTHROPIC_API_KEY missing - articles cannot be generated")
        fatal += 1

    print("\n=== Affiliate networks (need at least 1) ===")
    affiliates = 0
    if cfg.amazon_tag:
        _ok(f"Amazon: tag={cfg.amazon_tag}")
        affiliates += 1
    else:
        _warn("Amazon associate tag not set")
    if cfg.rakuten_id:
        _ok(f"Rakuten: id={cfg.rakuten_id}")
        affiliates += 1
    else:
        _warn("Rakuten affiliate id not set")
    if cfg.moshimo_id:
        _ok(f"Moshimo: a_id={cfg.moshimo_id}")
        affiliates += 1
    else:
        _warn("Moshimo a_id not set (easiest ASP to get approved into)")
    if cfg.a8_template:
        _ok("A8.net link template set")
        affiliates += 1
    if cfg.valuecommerce_template:
        _ok("ValueCommerce link template set")
        affiliates += 1
    if affiliates == 0:
        _bad("No affiliate network configured - posts will have no monetized links")
        fatal += 1
    elif affiliates < 2:
        _warn("Only one affiliate network. Adding 2-3 increases conversion options.")
        warnings += 1

    print("\n=== Site identity ===")
    if cfg.site_base_url == "https://example.github.io/affiliate":
        _warn(f"SITE_BASE_URL is the default placeholder ({cfg.site_base_url})")
        warnings += 1
    else:
        _ok(f"SITE_BASE_URL = {cfg.site_base_url}")
    _ok(f"SITE_TITLE = {cfg.site_title}")
    _ok(f"SITE_DESCRIPTION = {cfg.site_description}")

    print("\n=== Optional integrations ===")
    if all([cfg.x_api_key, cfg.x_api_secret, cfg.x_access_token, cfg.x_access_secret]):
        _ok("X (Twitter) auto-posting enabled")
    else:
        _warn("X auto-posting disabled (set 4 X_* env vars to enable)")

    if cfg.discord_webhook_url:
        _ok("Discord webhook set (new posts will be announced)")
    else:
        _warn("Discord webhook not set (optional)")

    print("\n=== Analytics & Search Console ===")
    if cfg.ga_id:
        _ok(f"Google Analytics 4 ID = {cfg.ga_id}")
    else:
        _warn("GA_MEASUREMENT_ID not set (no analytics tag will be emitted)")
    if cfg.google_site_verification:
        _ok("Google Search Console verification meta set")
    else:
        _warn("GOOGLE_SITE_VERIFICATION not set (you can verify via DNS instead)")
    if cfg.bing_site_verification:
        _ok("Bing Webmaster verification meta set")
    else:
        _warn("BING_SITE_VERIFICATION not set (optional)")

    print("\n=== Custom domain ===")
    if cfg.site_custom_domain:
        _ok(f"SITE_CUSTOM_DOMAIN = {cfg.site_custom_domain} (CNAME will be emitted)")
    else:
        _warn("SITE_CUSTOM_DOMAIN not set (using default github.io URL)")

    print("\n=== Tuning ===")
    _ok(f"ARTICLES_PER_RUN = {cfg.articles_per_run}")
    _ok(f"MODEL = {cfg.model}")

    print()
    if fatal:
        print(f"{RED}FAIL{RESET}: {fatal} fatal issue(s), {warnings} warning(s)")
        return 1
    if warnings:
        print(f"{YELLOW}OK with warnings{RESET}: {warnings} warning(s)")
        return 0
    print(f"{GREEN}All good. Ready to run.{RESET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
