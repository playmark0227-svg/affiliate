"""Render the markdown posts into a static HTML site."""
from __future__ import annotations

import datetime as dt
import json
import re
import shutil
import urllib.parse
import urllib.request
from html import escape
from pathlib import Path
from typing import Any

import frontmatter
import markdown as md
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .config import CONTENT_DIR, SITE_DIR, TEMPLATES_DIR, Config


def _md_to_html(text: str) -> str:
    return md.markdown(text, extensions=["extra", "toc", "sane_lists"])


def _excerpt(html: str, n: int = 120) -> str:
    text = re.sub(r"<[^>]+>", "", html)
    text = text.strip().replace("\n", " ")
    return (text[:n] + "…") if len(text) > n else text


def _extract_faq_jsonld(html: str) -> str | None:
    """Look for ## よくある質問 sections rendered as h3 Q. ... + following p."""
    # Find h3 questions
    pattern = re.compile(
        r'<h3[^>]*>(?:Q\.\s*)?(.+?)</h3>\s*<p>(.+?)</p>',
        re.DOTALL,
    )
    qa: list[tuple[str, str]] = []
    for m in pattern.finditer(html):
        q = re.sub(r"<[^>]+>", "", m.group(1)).strip()
        a = re.sub(r"<[^>]+>", "", m.group(2)).strip()
        if "?" in q or "?" in q:
            qa.append((q, a))
    if not qa:
        return None
    data = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": q,
                "acceptedAnswer": {"@type": "Answer", "text": a},
            }
            for q, a in qa
        ],
    }
    return json.dumps(data, ensure_ascii=False)


def _read_posts() -> list[dict[str, Any]]:
    posts: list[dict[str, Any]] = []
    if not CONTENT_DIR.exists():
        return posts
    for path in sorted(CONTENT_DIR.glob("*.md"), reverse=True):
        post = frontmatter.load(path)
        meta = dict(post.metadata)
        meta["body_html"] = _md_to_html(post.content)
        meta["excerpt"] = _excerpt(meta["body_html"])
        meta["url_path"] = f"posts/{path.stem}.html"
        meta["faq_jsonld"] = _extract_faq_jsonld(meta["body_html"])
        posts.append(meta)
    _attach_related(posts)
    return posts


def _attach_related(posts: list[dict[str, Any]]) -> None:
    """For each post, find up to 3 other posts in the same category."""
    by_cat: dict[str, list[dict[str, Any]]] = {}
    for p in posts:
        by_cat.setdefault(p.get("category", ""), []).append(p)
    for p in posts:
        cat = p.get("category", "")
        candidates = [q for q in by_cat.get(cat, []) if q is not p]
        if len(candidates) < 3:
            # Pad with newest from other categories
            others = [q for q in posts if q is not p and q.get("category") != cat]
            candidates = candidates + others
        p["related"] = candidates[:3]


def build(cfg: Config) -> None:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
    )

    if SITE_DIR.exists():
        shutil.rmtree(SITE_DIR)
    SITE_DIR.mkdir(parents=True)
    (SITE_DIR / "posts").mkdir(parents=True)

    static_src = TEMPLATES_DIR / "static"
    if static_src.exists():
        shutil.copytree(static_src, SITE_DIR / "static")

    posts = _read_posts()

    site_ctx = {
        "title": cfg.site_title,
        "description": cfg.site_description,
        "base_url": cfg.site_base_url,
        "year": dt.date.today().year,
    }

    index_tpl = env.get_template("index.html")
    (SITE_DIR / "index.html").write_text(
        index_tpl.render(site=site_ctx, posts=posts), encoding="utf-8"
    )

    post_tpl = env.get_template("post.html")
    for p in posts:
        out_path = SITE_DIR / p["url_path"]
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            post_tpl.render(site=site_ctx, post=p), encoding="utf-8"
        )

    # Policy/info pages
    _write_policy_pages(env, site_ctx)

    _write_sitemap(posts, cfg)
    _write_rss(posts, cfg)
    _write_robots(cfg)

    (SITE_DIR / ".nojekyll").write_text("")


def _write_policy_pages(env: Environment, site_ctx: dict[str, Any]) -> None:
    pages = [
        ("about.html", "運営者情報", _ABOUT_BODY),
        ("privacy.html", "プライバシーポリシー", _PRIVACY_BODY),
        ("contact.html", "お問い合わせ", _CONTACT_BODY),
    ]
    tpl = env.get_template("page.html")
    for filename, title, body in pages:
        out = SITE_DIR / filename
        out.write_text(
            tpl.render(site=site_ctx, page={"title": title, "body": body}),
            encoding="utf-8",
        )


def _write_sitemap(posts: list[dict[str, Any]], cfg: Config) -> None:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    today = dt.date.today().isoformat()
    for url in ["", "about.html", "privacy.html", "contact.html"]:
        loc = f"{cfg.site_base_url}/{url}"
        lines.append(
            f"<url><loc>{escape(loc)}</loc><lastmod>{today}</lastmod></url>"
        )
    for p in posts:
        loc = f"{cfg.site_base_url}/{p['url_path']}"
        lines.append(
            f"<url><loc>{escape(loc)}</loc><lastmod>{p.get('date','')}</lastmod></url>"
        )
    lines.append("</urlset>")
    (SITE_DIR / "sitemap.xml").write_text("\n".join(lines), encoding="utf-8")


def _write_rss(posts: list[dict[str, Any]], cfg: Config) -> None:
    items = []
    for p in posts[:30]:
        link = f"{cfg.site_base_url}/{p['url_path']}"
        items.append(
            "<item>"
            f"<title>{escape(p.get('title',''))}</title>"
            f"<link>{escape(link)}</link>"
            f"<description>{escape(p.get('description','') or p.get('excerpt',''))}</description>"
            f"<pubDate>{p.get('date','')}</pubDate>"
            "</item>"
        )
    rss = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<rss version="2.0"><channel>'
        f"<title>{escape(cfg.site_title)}</title>"
        f"<link>{escape(cfg.site_base_url)}</link>"
        f"<description>{escape(cfg.site_description)}</description>"
        + "".join(items)
        + "</channel></rss>"
    )
    (SITE_DIR / "feed.xml").write_text(rss, encoding="utf-8")


def _write_robots(cfg: Config) -> None:
    content = (
        "User-agent: *\n"
        "Allow: /\n"
        f"Sitemap: {cfg.site_base_url}/sitemap.xml\n"
    )
    (SITE_DIR / "robots.txt").write_text(content, encoding="utf-8")


def ping_sitemap(cfg: Config) -> None:
    """Notify Google and Bing about the sitemap. Best-effort, never fatal."""
    sitemap = f"{cfg.site_base_url}/sitemap.xml"
    targets = [
        f"https://www.google.com/ping?sitemap={urllib.parse.quote(sitemap)}",
        f"https://www.bing.com/ping?sitemap={urllib.parse.quote(sitemap)}",
    ]
    for url in targets:
        try:
            with urllib.request.urlopen(url, timeout=10) as r:
                print(f"[sitemap-ping] {url} -> {r.status}")
        except Exception as e:
            print(f"[sitemap-ping] {url} failed: {e}")


_ABOUT_BODY = """\
<h2>サイト概要</h2>
<p>本サイトは、編集チームが厳選した商品レビューを発信するメディアです。AIによるリサーチと人手の監修を組み合わせ、購入の判断材料となる客観的な情報をお届けします。</p>

<h2>運営方針</h2>
<ul>
  <li>誇大広告・医薬品的効能効果の表現は使用しません</li>
  <li>価格・仕様は執筆時点の情報であることを明記します</li>
  <li>アフィリエイトリンクであることをすべて明示します</li>
</ul>

<h2>コンテンツについて</h2>
<p>記事は最新情報に基づいて作成していますが、製品仕様・価格は変動します。最終的な購入判断は、リンク先の販売ページで最新情報をご確認の上、自己責任でお願いいたします。</p>

<h2>免責事項</h2>
<p>本サイトの情報を利用したことにより生じた損害について、運営者は一切の責任を負いかねます。</p>
"""

_PRIVACY_BODY = """\
<h2>個人情報の取扱い</h2>
<p>本サイトでは、お問い合わせフォーム等を通じてお預かりした個人情報を、お問い合わせへの回答以外の目的で利用することはありません。</p>

<h2>アクセス解析ツールについて</h2>
<p>本サイトでは、アクセス状況の把握のためにGoogle Analytics等のアクセス解析ツールを利用する場合があります。これらはトラフィックデータの収集のためにCookieを使用しており、データは匿名で収集され、個人を特定するものではありません。</p>

<h2>アフィリエイトプログラムについて</h2>
<p>本サイトは、Amazon.co.jpを宣伝しリンクすることによってサイトが紹介料を獲得できる手段を提供することを目的に設定されたアフィリエイトプログラムである、Amazonアソシエイト・プログラムの参加者です。また、楽天アフィリエイトプログラム、A8.netその他のASPに参加しています。</p>

<h2>Cookieについて</h2>
<p>アフィリエイトリンクをクリックされた場合、リンク先のサービス提供者によりCookieが設定される場合があります。これは購入のトラッキングのために用いられます。設定を無効にしたい場合はブラウザの設定からCookieを無効にしてください。</p>

<h2>免責事項</h2>
<p>本サイトに掲載された情報を利用して生じた損害等について、運営者は一切の責任を負いません。</p>

<h2>著作権</h2>
<p>本サイトに掲載されているテキスト・画像等の著作権は、当サイト運営者または各権利者に帰属します。</p>

<h2>プライバシーポリシーの変更</h2>
<p>本ポリシーの内容は、利用者に通知することなく変更することができるものとします。</p>
"""

_CONTACT_BODY = """\
<p>本サイトへのお問い合わせ・記事修正のご依頼・広告掲載のご相談などは、リポジトリの Issues よりご連絡ください。</p>

<p>掲載情報の誤りに気づかれた場合、訂正の根拠資料(公式サイトのリンクなど)をご提示いただけると、迅速に対応できます。</p>

<p>取材・寄稿のご相談も受け付けております。</p>
"""
