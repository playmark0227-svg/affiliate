# 完全自動アフィリエイトシステム

AIが自律的に商品レビュー記事を生成→静的ブログとして公開→アフィリエイト収益を発生させる、ほぼ無人運用のシステムです。

> **正直な話**: 「完全に何も触らない」は無理です。最低限のセットアップ(API鍵とアフィリエイト登録)が一度だけ必要です。それ以降は、GitHub Actionsの定時実行が毎日自動で記事を増やし続けます。

---

## 仕組み

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Topic       │ -> │  Generator   │ -> │  Publisher   │ -> │  Site Build  │
│  (Claude)    │    │  (Claude)    │    │  (Markdown)  │    │  (Static)    │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
     ▲                                                              │
     │                                                              ▼
┌──────────────┐                                            ┌──────────────┐
│  Analytics   │ <----------------- (CSV) ------------------│ GitHub Pages │
│  (weights)   │                                            │   公開       │
└──────────────┘                                            └──────────────┘
```

- **GitHub Actions(無料枠で完結)** が毎日 cron で起動
- Claude APIで「今日書く商品レビュー記事のテーマ」を選定し、本文を生成
- アフィリエイトリンク(Amazon / 楽天 / A8.net)を自動挿入
- 静的サイトをビルドして GitHub Pages に公開
- (任意) X(旧Twitter)に告知投稿
- 翌日以降、アナリティクスCSVを置けばカテゴリ重みが自動調整され、売れるジャンルに寄っていく

## クイックスタート(初期セットアップだけはやる)

### 1. このリポジトリを fork して有効化

このプロジェクトをそのまま fork するか、`main` ブランチに merge します。

### 2. アフィリエイトプログラムへの登録

| プログラム | 登録URL | 必要な値 |
|-----------|---------|---------|
| もしもアフィリエイト ⭐推奨 | https://af.moshimo.com | a_id(管理画面の「ID確認」)|
| Amazonアソシエイト | https://affiliate.amazon.co.jp | アソシエイトタグ(例: `yourname-22`) |
| 楽天アフィリエイト | https://affiliate.rakuten.co.jp | アフィリエイトID |
| A8.net (任意) | https://www.a8.net | 任意の案件のアフィリエイトリンク |
| バリューコマース (任意) | https://www.valuecommerce.ne.jp | 案件別のリンクテンプレート |

> **おすすめ:** もしもアフィリエイトが最も審査が緩く、1アカウントで Amazon/楽天/Yahoo!ショッピングの3大ECに対応できます。Amazonアソシエイト本家の審査は厳しい(180日以内に3件売上が必要)ので、もしも経由のAmazonリンクから始めるのが現実的です。

### 3. GitHub の Secrets / Variables を設定

リポジトリの **Settings → Secrets and variables → Actions** で:

#### Secrets(暗号化される値)

| キー | 必須 | 説明 |
|------|------|------|
| `ANTHROPIC_API_KEY` | ✅ | https://console.anthropic.com で取得 |
| `MOSHIMO_ID` | 推奨 | もしもアフィリエイトのa_id |
| `AMAZON_ASSOCIATE_TAG` | 任意 | Amazon アソシエイトタグ(本家) |
| `RAKUTEN_AFFILIATE_ID` | 任意 | 楽天アフィリエイトID |
| `A8_LINK_TEMPLATE` | 任意 | A8.netのアフィリンクURL |
| `VALUECOMMERCE_LINK_TEMPLATE` | 任意 | バリューコマースのリンク |
| `X_API_KEY` 他 | 任意 | XへのAuto投稿用 (4つ) |

#### Variables(平文)

| キー | 説明 | 例 |
|------|------|-----|
| `SITE_BASE_URL` | 公開URL | `https://YOUR-NAME.github.io/affiliate` |
| `SITE_TITLE` | サイト名 | `お得レビューラボ` |
| `SITE_DESCRIPTION` | サブタイトル | `AIが選ぶ商品レビュー` |
| `ARTICLES_PER_RUN` | 1日あたりの生成数 | `2` |
| `MODEL` | 使用モデル | `claude-opus-4-8` |
| `EFFORT` | 思考の深さ(low/medium/high/xhigh/max) | `high` |

### 4. GitHub Pages を有効化

**Settings → Pages → Source = "GitHub Actions"** を選択。

### 5. 動作確認

- **Actions** タブから `Deploy site` ワークフローを **Run workflow** で手動実行
- 数分後に GitHub Pages にサイトが公開される(**初期記事8本がすでに用意されています**)
- その後 `Auto-generate posts` も手動実行できる
- 毎日 06:00 UTC (日本時間 15:00) に勝手に新記事が増え続ける

> **重要:** `Deploy site` は **`ANTHROPIC_API_KEY` 無しでも動きます**(seed記事8本だけでサイトが立ち上がる)。
> なので「とりあえず公開だけ確認したい」なら、まず GitHub Pages 有効化 → `Deploy site` 実行で公開URLが出ます。
> APIキーやアフィリエイトIDは後から Secrets に追加すれば、翌日の cron から自動生成が走り始めます。

これで設定完了です。

### 6. (任意)アクセス解析・検索コンソール

設定すれば自動でメタタグが入ります。すべて GitHub の **Variables** に追加するだけ。

| キー | 用途 | 取得元 |
|------|------|--------|
| `GA_MEASUREMENT_ID` | Google Analytics 4 | https://analytics.google.com で プロパティ作成 → 測定ID `G-XXXXXXXXXX` |
| `GOOGLE_SITE_VERIFICATION` | Search Console | https://search.google.com/search-console → 「HTMLタグ」で `content="..."` の中身 |
| `BING_SITE_VERIFICATION` | Bing Webmaster | https://www.bing.com/webmasters → メタタグ方式の `content="..."` |
| `SITE_CUSTOM_DOMAIN` | 独自ドメイン | 例: `example.com` または `blog.example.com`(設定時は `site/CNAME` 自動生成) |

Discord通知が欲しい場合は、Discord チャンネルの「連携サービス → Webhook」で URL を取得し、**Secrets** に `DISCORD_WEBHOOK_URL` として保存。

---

## 含まれているもの

- ✅ **初期記事8本**(私が書いた、APIコール不要のコンテンツ)— ガジェット/在宅ワーク/キッチン/美容健康/学習/アウトドア
- ✅ **About/プライバシーポリシー/お問い合わせ**ページ自動生成
- ✅ **JSON-LD構造化データ**(Article / FAQ / BreadcrumbList)
- ✅ **OGP / Twitter Card メタタグ**
- ✅ **canonical / robots.txt / sitemap.xml / RSS feed**
- ✅ **Google・Bingへのサイトマップ自動ping**(新記事公開時)
- ✅ **記事間の関連記事自動リンク**(同カテゴリ優先)
- ✅ **Amazon・楽天・Yahoo(もしも経由)・A8・バリューコマース**の5ASP対応
- ✅ **GitHub Actions cron**で毎日自動投稿
- ✅ **`python -m affiliate.cli check`** で設定漏れを検出

---

## AI生成エンジン(Claude Opus 4.8 最適化)

記事生成・テーマ選定は最新の **Claude Opus 4.8** を使い、以下を有効化しています(`src/affiliate/llm.py`):

- **アダプティブ思考**(`thinking: adaptive`)— モデルが必要に応じて推論を深め、比較や選び方の質が上がる
- **エフォート制御**(`EFFORT`、既定 `high`)— 品質とコスト/速度のトレードオフを1変数で調整。記事は `high`、テーマ選定は `medium`
- **構造化出力**(JSON Schema)— 返答が必ず有効なJSONになり、パース失敗で記事が落ちる事故をなくす
- **ストリーミング**— 長文記事生成でのタイムアウトを回避
- **プロンプトキャッシュ**— システムプロンプトにキャッシュ断点を設置(プレフィックスが十分長い場合に課金を節約)
- **多重フォールバック**— もしSDK/モデルが新パラメータを拒否しても、自動で素朴な呼び出しに切り替えて止まらない

> コスト感: 記事1本あたり数円〜十数円程度(`EFFORT` と文字数次第)。`ARTICLES_PER_RUN=2` なら1日数十円。`EFFORT=medium` でさらに下げられます。

---

## ローカルでの開発

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# .env を作って値を埋める
cp .env.example .env
# vim .env

export $(cat .env | xargs)
export PYTHONPATH=src

# セットアップを検証
python -m affiliate.cli check

# 1回だけ実行(記事1〜2本生成)
python -m affiliate.cli run

# サイトのHTMLをビルドのみ
python -m affiliate.cli build

# 検索エンジンにサイトマップを通知
python -m affiliate.cli ping

# テスト
python -m unittest tests.test_smoke -v
```

## カスタマイズ

### 生成数を変える

GitHub Variables の `ARTICLES_PER_RUN` を `5` などに変更。

### 走らせる時刻を変える

`.github/workflows/generate.yml` の cron を編集。
- 例: `"0 0 * * *"` = 毎日 09:00 JST

### カテゴリを増やす/変える

`src/affiliate/state.py` の `_default_state()` の `category_weights` を編集。

### 売上データをフィードバック

Amazonアソシエイト等のレポートをダウンロードして、以下の形式の CSV を `data/performance.csv` として commit してください。次回実行時にカテゴリ重みが更新されます。

```csv
category,clicks,conversions
ガジェット,120,4
キッチン用品,40,1
在宅ワーク,200,9
```

### 別のテーマ/プロンプトに変える

- `src/affiliate/topic_research.py` の `SYSTEM` / `USER_TEMPLATE`
- `src/affiliate/content_generator.py` の `SYSTEM` / `USER_TEMPLATE`

を直接編集。日本語以外でも英語でも自由に書き換え可能。

---

## ファイル構成

```
.
├── .github/workflows/
│   ├── generate.yml      # 毎日cron → 記事生成 → commit
│   └── deploy.yml        # contentが更新されたらPagesに公開
├── src/affiliate/
│   ├── config.py         # 環境変数のロード
│   ├── state.py          # 永続状態 (data/state.json)
│   ├── affiliate_links.py# Amazon/楽天/A8 のリンク生成
│   ├── topic_research.py # 次に書くテーマをClaudeに選ばせる
│   ├── content_generator.py # 本文生成 + Markdown化
│   ├── publisher.py      # Markdownをcontent/posts/に保存
│   ├── site_builder.py   # 静的サイト(HTML/RSS/sitemap)生成
│   ├── analytics.py      # 売上CSVから重みを更新
│   ├── social.py         # 任意のX投稿
│   ├── orchestrator.py   # パイプライン全体
│   └── cli.py            # python -m affiliate.cli {run,build}
├── templates/            # サイトテンプレート + CSS
├── content/posts/        # 自動生成されたMarkdown記事
├── data/                 # state.json, performance.csv
├── tests/test_smoke.py   # API無しで通るスモークテスト
└── requirements.txt
```

## 法的・倫理的注意

- **広告であることを明示**: 全記事フッターに自動でアフィリエイト表記が入ります(景品表示法のステマ規制対応)
- **薬機法**: プロンプトで医薬品的な効能効果表現を禁止しています
- **誇大広告**: AIが情報を捏造する可能性があるため、**価格・スペック等は「目安」と必ず明記**するよう指示済み
- **ChatGPT検出**: Google等の検索エンジンが「AI生成だけ」のサイトを評価しなくなる場合があります。長期運用する場合は人間による校正やE-E-A-Tの強化を検討してください

## 期待値の正直な話

- ✅ システムは確実に毎日記事を増やし、リンクをクリックすれば収益化される構造になっている
- ❌ ただしSEOで検索1ページ目に入るのは別の戦い(被リンク・サイト年数・コンテンツ品質)
- ❌ 「設置直後から月100万」は無理。インデックス→ランクインまで早くて1〜3ヶ月、稼げるかは運用次第
- 💡 だからこそ「**1日2本×365日 = 730本**」を低コストで自動生成し続けるこの仕組みに意味がある

## ライセンス

MIT
