"""Build affiliate URLs for supported networks.

Amazon Associates JP: append ?tag=YOUR-TAG to a product URL.
Rakuten: use Rakuten's affiliate URL builder (https://hb.afl.rakuten.co.jp).
A8.net / ValueCommerce: any link is a redirect URL containing your media id,
    so we just substitute {url} into a user-provided template.
Moshimo (かんたんリンク): URL-prefix based; supports Amazon/Rakuten/Yahoo
    in one approval and is the easiest ASP to get accepted into.
"""
from __future__ import annotations

import urllib.parse
from dataclasses import dataclass


@dataclass
class AffiliateContext:
    amazon_tag: str = ""
    rakuten_id: str = ""
    a8_template: str = ""
    moshimo_id: str = ""
    valuecommerce_template: str = ""

    def amazon(self, search_query: str) -> str | None:
        if not self.amazon_tag:
            return None
        q = urllib.parse.quote_plus(search_query)
        return f"https://www.amazon.co.jp/s?k={q}&tag={self.amazon_tag}"

    def rakuten(self, search_query: str) -> str | None:
        if not self.rakuten_id:
            return None
        q = urllib.parse.quote(search_query, safe="")
        target = f"https://search.rakuten.co.jp/search/mall/{q}/"
        return (
            "https://hb.afl.rakuten.co.jp/hgc/"
            f"{self.rakuten_id}/?pc={urllib.parse.quote(target, safe='')}"
            f"&m={urllib.parse.quote(target, safe='')}"
        )

    def yahoo_via_moshimo(self, search_query: str) -> str | None:
        """もしもアフィリエイト経由でYahoo!ショッピングへ。

        Moshimo's "かんたんリンク" actually wraps a target URL. The user
        gets one moshimo_id (a_id) and we wrap any deep URL.
        """
        if not self.moshimo_id:
            return None
        q = urllib.parse.quote(search_query, safe="")
        target = f"https://shopping.yahoo.co.jp/search?p={q}"
        # https://af.moshimo.com/af/c/click?a_id=XXXXX&p_id=...&pl_id=...&url=ENCODED
        return (
            "https://af.moshimo.com/af/c/click?"
            f"a_id={self.moshimo_id}"
            f"&url={urllib.parse.quote(target, safe='')}"
        )

    def a8(self) -> str | None:
        if not self.a8_template:
            return None
        return self.a8_template

    def valuecommerce(self) -> str | None:
        if not self.valuecommerce_template:
            return None
        return self.valuecommerce_template

    def all_for_query(self, query: str) -> list[tuple[str, str]]:
        out: list[tuple[str, str]] = []
        for label, url in (
            ("Amazonで見る", self.amazon(query)),
            ("楽天市場で見る", self.rakuten(query)),
            ("Yahoo!ショッピングで見る", self.yahoo_via_moshimo(query)),
            ("公式サイトで見る", self.a8()),
            ("提携ストアで見る", self.valuecommerce()),
        ):
            if url:
                out.append((label, url))
        return out
