"""Smoke tests that don't require network or API keys."""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from affiliate import affiliate_links, content_generator, publisher, site_builder, state  # noqa: E402
from affiliate.config import CONTENT_DIR, SITE_DIR, Config  # noqa: E402


class SmokeTests(unittest.TestCase):
    def test_affiliate_links_amazon(self):
        aff = affiliate_links.AffiliateContext("mytag-22", "", "")
        url = aff.amazon("ワイヤレスイヤホン")
        assert url is not None
        self.assertIn("tag=mytag-22", url)
        self.assertIn("amazon.co.jp", url)

    def test_affiliate_links_rakuten(self):
        aff = affiliate_links.AffiliateContext("", "abcd1234.5678", "")
        url = aff.rakuten("ヘッドフォン")
        assert url is not None
        self.assertIn("hb.afl.rakuten.co.jp", url)
        self.assertIn("abcd1234.5678", url)

    def test_affiliate_links_skipped_when_unset(self):
        aff = affiliate_links.AffiliateContext("", "", "")
        self.assertEqual(aff.all_for_query("anything"), [])

    def test_render_markdown_minimal(self):
        article = {
            "title": "テスト",
            "summary": "概要",
            "buying_guide": ["A", "B"],
            "products": [
                {
                    "name": "サンプル製品",
                    "search_query": "sample",
                    "for_whom": "対象",
                    "pros": ["良い1"],
                    "cons": ["留意1"],
                }
            ],
            "faq": [{"q": "Q1", "a": "A1"}],
            "closing": "結び",
        }
        aff = affiliate_links.AffiliateContext("tag-22", "", "")
        body = content_generator.render_markdown(article, aff)
        self.assertIn("結論", body)
        self.assertIn("サンプル製品", body)
        self.assertIn("Amazonで見る", body)
        self.assertIn("nofollow sponsored", body)

    def test_publish_and_build(self):
        article = {
            "title": "テスト記事",
            "description": "テスト説明",
            "tags": ["test"],
            "category": "ガジェット",
            "summary": "結論",
        }
        body = "## サンプル\n\n本文です。"
        path = publisher.save_post(article, body)
        self.assertTrue(path.exists())

        os.environ["SITE_BASE_URL"] = "https://example.test"
        os.environ["SITE_TITLE"] = "Test"
        os.environ["SITE_DESCRIPTION"] = "Desc"
        cfg = Config.from_env()
        site_builder.build(cfg)
        self.assertTrue((SITE_DIR / "index.html").exists())
        self.assertTrue((SITE_DIR / "feed.xml").exists())
        self.assertTrue((SITE_DIR / "sitemap.xml").exists())

        # Cleanup so re-runs are deterministic
        for f in CONTENT_DIR.glob("*.md"):
            f.unlink()

    def test_state_roundtrip(self):
        s = state.load()
        s["covered_topics"].append("確認用テーマ")
        state.save(s)
        s2 = state.load()
        self.assertIn("確認用テーマ", s2["covered_topics"])


if __name__ == "__main__":
    unittest.main()
