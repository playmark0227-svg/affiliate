"""Build affiliate URLs for supported networks.

Amazon Associates JP: append ?tag=YOUR-TAG to a product URL.
Rakuten: use Rakuten's affiliate URL builder (https://hb.afl.rakuten.co.jp).
A8.net: any link is a redirect URL containing your media id, so we just
substitute {url} into a user-provided template.
"""
from __future__ import annotations

import urllib.parse
from dataclasses import dataclass


@dataclass
class AffiliateContext:
    amazon_tag: str
    rakuten_id: str
    a8_template: str

    def amazon(self, search_query: str) -> str | None:
        """Return an Amazon JP search URL with the affiliate tag.

        Using a search URL is safer than a hallucinated ASIN - even if the
        AI cannot pick a real product, the link still leads somewhere useful
        and still pays affiliate commission on whatever the user buys.
        """
        if not self.amazon_tag:
            return None
        q = urllib.parse.quote_plus(search_query)
        return f"https://www.amazon.co.jp/s?k={q}&tag={self.amazon_tag}"

    def rakuten(self, search_query: str) -> str | None:
        if not self.rakuten_id:
            return None
        # Rakuten's "afl.rakuten.co.jp" universal link wraps any rakuten URL.
        # We point at their search endpoint with the user's affiliate id.
        q = urllib.parse.quote(search_query, safe="")
        target = f"https://search.rakuten.co.jp/search/mall/{q}/"
        wrapped = (
            "https://hb.afl.rakuten.co.jp/hgc/"
            f"{self.rakuten_id}/?pc={urllib.parse.quote(target, safe='')}"
            f"&m={urllib.parse.quote(target, safe='')}"
        )
        return wrapped

    def a8(self) -> str | None:
        if not self.a8_template:
            return None
        return self.a8_template

    def all_for_query(self, query: str) -> list[tuple[str, str]]:
        """Return a list of (label, url) pairs for all configured networks."""
        out: list[tuple[str, str]] = []
        a = self.amazon(query)
        if a:
            out.append(("Amazonで見る", a))
        r = self.rakuten(query)
        if r:
            out.append(("楽天市場で見る", r))
        a8 = self.a8()
        if a8:
            out.append(("公式サイトで見る", a8))
        return out
