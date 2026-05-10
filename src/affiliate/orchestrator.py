"""End-to-end pipeline: research -> generate -> publish -> build site -> social."""
from __future__ import annotations

import datetime as dt
import sys
import traceback
from typing import Any

from . import analytics, content_generator, publisher, site_builder, social, state, topic_research
from .affiliate_links import AffiliateContext
from .config import Config


def run_once() -> int:
    cfg = Config.from_env()
    cfg.require_api_key()

    aff = AffiliateContext(
        amazon_tag=cfg.amazon_tag,
        rakuten_id=cfg.rakuten_id,
        a8_template=cfg.a8_template,
        moshimo_id=cfg.moshimo_id,
        valuecommerce_template=cfg.valuecommerce_template,
    )

    s = state.load()

    # 1. Update weights from any new performance data
    s = analytics.update_weights(s)

    # 2. Get fresh topics
    n = max(1, cfg.articles_per_run)
    topics = topic_research.propose_topics(cfg, s, n)
    print(f"[orchestrator] proposed {len(topics)} topics")

    # 3. Generate + publish each article
    new_paths: list[tuple[dict[str, Any], str]] = []
    for topic in topics:
        try:
            article = content_generator.generate_article(cfg, topic)
        except Exception as e:
            print(f"[orchestrator] generation failed: {e}")
            traceback.print_exc()
            continue

        body = content_generator.render_markdown(article, aff)
        path = publisher.save_post(article, body)
        print(f"[orchestrator] wrote {path}")

        s["covered_topics"].append(topic.get("title", ""))
        s["post_count"] = s.get("post_count", 0) + 1

        post_url = f"{cfg.site_base_url}/posts/{path.stem}.html"
        new_paths.append((article, post_url))

    # Trim memory of covered topics to keep the prompt bounded
    s["covered_topics"] = s["covered_topics"][-200:]
    s["last_run"] = dt.datetime.utcnow().isoformat() + "Z"

    state.save(s)

    # 4. Rebuild static site from full corpus
    site_builder.build(cfg)
    print("[orchestrator] site built")

    # 5. Optional: announce on X / Discord
    for article, url in new_paths:
        if social.maybe_post_to_x(cfg, article, url):
            print(f"[orchestrator] posted to X: {url}")
        if social.maybe_notify_discord(cfg, article, url):
            print(f"[orchestrator] notified Discord: {url}")

    # 6. Ping search engines so the new posts get indexed faster
    if new_paths:
        site_builder.ping_sitemap(cfg)

    return len(new_paths)


def main() -> int:
    try:
        n = run_once()
        print(f"[orchestrator] done, {n} new posts")
        return 0
    except SystemExit:
        raise
    except Exception as e:
        print(f"[orchestrator] FAILED: {e}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
