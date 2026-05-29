"""Generate full review/comparison articles with Claude."""
from __future__ import annotations

import datetime as dt
from typing import Any

import anthropic

from . import llm
from .affiliate_links import AffiliateContext
from .config import Config


SYSTEM = """\
あなたは日本語の商品レビュー記事を書くプロのライター兼SEOエディターです。
読者が「買って失敗したくない」と思って検索している前提で書きます。

# トーンと品質
- E-E-A-T(経験/専門性/権威性/信頼性)を意識し、断定しすぎない誠実なトーン
- 具体的な比較軸(価格帯、サイズ、用途、向いている人)を必ず示す
- 一般的なAI生成文にありがちな冗長な前置き・決まり文句を避け、要点から書く
- 文章量はテーマの複雑さに見合わせる(過剰な水増しをしない)

# 事実の扱い(重要)
- 各商品候補は一般名・カテゴリで紹介し、実在しないモデル名や型番は捏造しない
- 価格や仕様は「目安」「執筆時点の参考」と明示し、確定的に断言しない
- 不確実なことは「一般に」「製品により異なる」と幅を持たせる

# 法令順守
- 医薬品的な効能効果の表現(薬機法に抵触する表現)を使わない
- 「最安」「No.1」「必ず効く」など根拠のない最上級・誇大表現(景表法)を避ける
- アフィリエイト広告である旨はフッターで明記される前提で書く

出力は指定スキーマに厳密に従うこと。
"""

# Structured-outputs schema — guarantees the reply parses as valid JSON.
ARTICLE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "description": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "category": {"type": "string"},
        "summary": {"type": "string"},
        "products": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "search_query": {"type": "string"},
                    "for_whom": {"type": "string"},
                    "pros": {"type": "array", "items": {"type": "string"}},
                    "cons": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["name", "search_query", "for_whom", "pros", "cons"],
                "additionalProperties": False,
            },
        },
        "buying_guide": {"type": "array", "items": {"type": "string"}},
        "faq": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"q": {"type": "string"}, "a": {"type": "string"}},
                "required": ["q", "a"],
                "additionalProperties": False,
            },
        },
        "closing": {"type": "string"},
    },
    "required": [
        "title", "description", "tags", "category", "summary",
        "products", "buying_guide", "faq", "closing",
    ],
    "additionalProperties": False,
}

USER_TEMPLATE = """\
今日の日付: {today}

下記テーマで2000〜3000字の日本語記事を書いてください。

テーマ:
- タイトル候補: {title}
- カテゴリ: {category}
- メインキーワード: {primary_keyword}
- 関連キーワード: {secondary_keywords}
- 検索意図: {intent}

含めるセクション:
1. 結論(150字程度の要約)
2. 選び方の3〜5ポイント
3. おすすめ候補3つ(各候補にカテゴリ的な紹介、メリット、こんな人に向く)
4. よくある質問(3つ)
5. まとめ

JSONスキーマ:
{{
  "title": "最終タイトル(40字以内、メインキーワード含む)",
  "description": "メタディスクリプション(120字以内)",
  "tags": ["タグ1", "タグ2", "タグ3"],
  "category": "カテゴリ",
  "summary": "結論(150字)",
  "products": [
    {{
      "name": "一般名(例: 静音マウス)",
      "search_query": "アフィリエイト先で検索する短いクエリ",
      "for_whom": "こんな人におすすめ",
      "pros": ["メリット1", "メリット2", "メリット3"],
      "cons": ["留意点1", "留意点2"]
    }}
  ],
  "buying_guide": ["選び方ポイント1", "選び方ポイント2", "選び方ポイント3"],
  "faq": [
    {{"q": "質問1", "a": "回答1"}},
    {{"q": "質問2", "a": "回答2"}},
    {{"q": "質問3", "a": "回答3"}}
  ],
  "closing": "まとめ200字"
}}
"""


def generate_article(cfg: Config, topic: dict[str, Any]) -> dict[str, Any]:
    client = anthropic.Anthropic(api_key=cfg.require_api_key())
    user = USER_TEMPLATE.format(
        today=dt.date.today().isoformat(),
        title=topic.get("title", ""),
        category=topic.get("category", ""),
        primary_keyword=topic.get("primary_keyword", ""),
        secondary_keywords="、".join(topic.get("secondary_keywords", [])),
        intent=topic.get("intent", ""),
    )

    # Long output + adaptive thinking → stream to avoid HTTP timeouts.
    article = llm.generate_json(
        client,
        model=cfg.model,
        system=SYSTEM,
        user=user,
        schema=ARTICLE_SCHEMA,
        effort=cfg.effort,
        max_tokens=16000,
        stream=True,
    )
    article["topic"] = topic
    return article


def render_markdown(article: dict[str, Any], aff: AffiliateContext) -> str:
    """Turn the structured article into a Jekyll-friendly markdown post."""
    lines: list[str] = []
    lines.append(f"## 結論")
    lines.append("")
    lines.append(article.get("summary", "").strip())
    lines.append("")

    # Buying guide
    guide = article.get("buying_guide") or []
    if guide:
        lines.append("## 失敗しない選び方")
        lines.append("")
        for i, point in enumerate(guide, 1):
            lines.append(f"{i}. {point}")
        lines.append("")

    # Products
    products = article.get("products") or []
    if products:
        lines.append("## おすすめ候補")
        lines.append("")
        for p in products:
            name = p.get("name", "").strip()
            lines.append(f"### {name}")
            lines.append("")
            for_whom = p.get("for_whom", "").strip()
            if for_whom:
                lines.append(f"**こんな人におすすめ:** {for_whom}")
                lines.append("")
            pros = p.get("pros") or []
            if pros:
                lines.append("**良い点**")
                lines.append("")
                for x in pros:
                    lines.append(f"- {x}")
                lines.append("")
            cons = p.get("cons") or []
            if cons:
                lines.append("**留意点**")
                lines.append("")
                for x in cons:
                    lines.append(f"- {x}")
                lines.append("")

            # Affiliate links
            query = p.get("search_query") or name
            links = aff.all_for_query(query)
            if links:
                lines.append('<div class="aff-buttons">')
                for label, url in links:
                    lines.append(
                        f'  <a class="aff-btn" href="{url}" target="_blank" '
                        f'rel="nofollow sponsored noopener">{label}</a>'
                    )
                lines.append("</div>")
                lines.append("")

    # FAQ
    faq = article.get("faq") or []
    if faq:
        lines.append("## よくある質問")
        lines.append("")
        for item in faq:
            q = item.get("q", "").strip()
            a = item.get("a", "").strip()
            if not q:
                continue
            lines.append(f"### Q. {q}")
            lines.append("")
            lines.append(a)
            lines.append("")

    # Closing
    closing = article.get("closing", "").strip()
    if closing:
        lines.append("## まとめ")
        lines.append("")
        lines.append(closing)
        lines.append("")

    # Disclosure
    lines.append("---")
    lines.append("")
    lines.append(
        "*本記事はアフィリエイトプログラムによる収益を得ています。"
        "価格・仕様は執筆時点の情報です。最新情報はリンク先でご確認ください。*"
    )
    lines.append("")
    return "\n".join(lines)
