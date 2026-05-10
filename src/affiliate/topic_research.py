"""Choose what to write about next.

Strategy:
1. Skip topics already covered.
2. Bias toward categories that scored well in past runs.
3. Ask Claude to propose fresh, search-intent-driven topics seeded with
   trend signals (e.g. seasonal). The model gets a list of "do not repeat"
   topics and category weights as hints.
"""
from __future__ import annotations

import datetime as dt
import json
import random
from typing import Any

import anthropic

from .config import Config


SYSTEM = """\
あなたは日本のアフィリエイトSEOマーケターです。
購入意欲が高いロングテールキーワードを狙う商品レビュー記事のテーマを提案します。

要件:
- タイトルは検索意図が明確で、具体的な商品ジャンルや比較軸を含む
- 「おすすめ」「比較」「レビュー」「選び方」のいずれかを含めることが多い
- 既出テーマと重複しない
- 季節性や時事を反映する(現在の日付を考慮)
- カテゴリ重みが高いものを優先するが、多様性も保つ
- 1テーマあたり最低3件の主要キーワードを抽出する
- 必ず JSON で出力する
"""


USER_TEMPLATE = """\
今日の日付: {today}
既出テーマ(避ける): {covered}
カテゴリ別重み(高いほど優先): {weights}
生成数: {n}

以下のJSONスキーマで返してください。説明文は不要です。

{{
  "topics": [
    {{
      "title": "記事タイトル(40字以内)",
      "category": "カテゴリ名",
      "search_query": "Amazonや楽天で検索する商品クエリ(短く具体的に)",
      "primary_keyword": "メインキーワード",
      "secondary_keywords": ["関連キーワード1", "関連キーワード2", "関連キーワード3"],
      "intent": "検索意図の1行説明",
      "rationale": "なぜ売れそうか1行"
    }}
  ]
}}
"""


def propose_topics(cfg: Config, state: dict[str, Any], n: int) -> list[dict[str, Any]]:
    client = anthropic.Anthropic(api_key=cfg.require_api_key())

    covered = state.get("covered_topics", [])[-50:]  # only show recent ones
    weights = state.get("category_weights", {})

    user = USER_TEMPLATE.format(
        today=dt.date.today().isoformat(),
        covered=json.dumps(covered, ensure_ascii=False),
        weights=json.dumps(weights, ensure_ascii=False),
        n=n,
    )

    msg = client.messages.create(
        model=cfg.model,
        max_tokens=2048,
        system=SYSTEM,
        messages=[{"role": "user", "content": user}],
    )

    text = "".join(b.text for b in msg.content if b.type == "text").strip()
    # Be tolerant: strip code fences if the model wrapped the JSON.
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip("` \n")

    try:
        data = json.loads(text)
        topics = data.get("topics", [])
    except json.JSONDecodeError:
        topics = []

    if not topics:
        # Defensive fallback so a one-off model glitch doesn't kill the run.
        topics = _fallback_topics(n)

    random.shuffle(topics)
    return topics[:n]


def _fallback_topics(n: int) -> list[dict[str, Any]]:
    pool = [
        {
            "title": "在宅ワークが捗るおすすめ昇降デスク3選",
            "category": "在宅ワーク",
            "search_query": "電動昇降デスク",
            "primary_keyword": "昇降デスク おすすめ",
            "secondary_keywords": ["電動昇降デスク", "スタンディングデスク", "在宅ワーク 机"],
            "intent": "在宅ワーク用のデスクを探している人",
            "rationale": "高単価で需要が安定",
        },
        {
            "title": "コスパ最強のワイヤレスイヤホン比較",
            "category": "ガジェット",
            "search_query": "ワイヤレスイヤホン コスパ",
            "primary_keyword": "ワイヤレスイヤホン おすすめ",
            "secondary_keywords": ["bluetoothイヤホン", "完全ワイヤレス", "ノイズキャンセリング"],
            "intent": "1万円前後のイヤホンを比較したい人",
            "rationale": "回遊性が高く比較記事が刺さる",
        },
    ]
    random.shuffle(pool)
    return pool[:n]
