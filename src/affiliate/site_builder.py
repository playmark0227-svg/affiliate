"""Render the markdown posts into a static HTML site."""
from __future__ import annotations

import datetime as dt
import re
import shutil
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
        posts.append(meta)
    return posts


def build(cfg: Config) -> None:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
    )

    if SITE_DIR.exists():
        shutil.rmtree(SITE_DIR)
    SITE_DIR.mkdir(parents=True)
    (SITE_DIR / "posts").mkdir(parents=True)

    # Copy static assets if present
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

    # Index
    index_tpl = env.get_template("index.html")
    (SITE_DIR / "index.html").write_text(
        index_tpl.render(site=site_ctx, posts=posts), encoding="utf-8"
    )

    # Posts
    post_tpl = env.get_template("post.html")
    for p in posts:
        out_path = SITE_DIR / p["url_path"]
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            post_tpl.render(site=site_ctx, post=p), encoding="utf-8"
        )

    # Sitemap & RSS
    _write_sitemap(posts, cfg)
    _write_rss(posts, cfg)

    # Don't let GitHub Pages run Jekyll on us.
    (SITE_DIR / ".nojekyll").write_text("")


def _write_sitemap(posts: list[dict[str, Any]], cfg: Config) -> None:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    lines.append(
        f"<url><loc>{cfg.site_base_url}/</loc><changefreq>daily</changefreq></url>"
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
