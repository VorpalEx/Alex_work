"""Fusion des données GSC (mots-clés) et GA4 (audience) par article."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from urllib.parse import urlparse

from .ga4 import PageMetrics
from .gsc import KeywordRow


@dataclass
class KeywordEntry:
    query: str
    url: str
    clicks: int
    impressions: int
    ctr: float
    position: float


@dataclass
class ArticleSummary:
    url: str
    path: str
    # GSC
    clicks: int = 0
    impressions: int = 0
    ctr: float = 0.0
    avg_position: float = 0.0
    keyword_count: int = 0
    best_keyword: str = ""
    # GA4
    views: int = 0
    avg_time_on_page: float = 0.0
    conversions: float = 0.0
    keywords: list[KeywordEntry] = field(default_factory=list)


def normalize_path(url_or_path: str) -> str:
    """Réduit une URL/chemin à un chemin canonique comparable entre GSC et GA4."""
    path = urlparse(url_or_path).path or url_or_path
    if len(path) > 1:
        path = path.rstrip("/")
    return path or "/"


def merge(
    keyword_rows: list[KeywordRow],
    page_metrics: dict[str, PageMetrics],
    *,
    url_regex: re.Pattern | None = None,
    min_impressions: int = 1,
    max_keywords_per_article: int = 0,
) -> list[ArticleSummary]:
    """Construit une liste d'ArticleSummary (avec leurs mots-clés) triée par clics."""
    # GA4 indexé par chemin normalisé.
    ga4_by_path: dict[str, PageMetrics] = {
        normalize_path(p): m for p, m in page_metrics.items()
    }

    grouped: dict[str, list[KeywordRow]] = defaultdict(list)
    for row in keyword_rows:
        if row.impressions < min_impressions:
            continue
        if url_regex and not url_regex.search(row.page):
            continue
        grouped[row.page].append(row)

    articles: list[ArticleSummary] = []
    for page_url, rows in grouped.items():
        rows.sort(key=lambda r: (r.clicks, r.impressions), reverse=True)
        if max_keywords_per_article > 0:
            rows = rows[:max_keywords_per_article]

        total_clicks = sum(r.clicks for r in rows)
        total_impr = sum(r.impressions for r in rows)
        # Position moyenne pondérée par les impressions (plus juste qu'une moyenne simple).
        weighted_pos = (
            sum(r.position * r.impressions for r in rows) / total_impr
            if total_impr
            else 0.0
        )
        best = max(rows, key=lambda r: (r.clicks, r.impressions))

        path = normalize_path(page_url)
        ga4 = ga4_by_path.get(path)

        summary = ArticleSummary(
            url=page_url,
            path=path,
            clicks=total_clicks,
            impressions=total_impr,
            ctr=(total_clicks / total_impr) if total_impr else 0.0,
            avg_position=round(weighted_pos, 1),
            keyword_count=len(rows),
            best_keyword=best.query,
            views=ga4.views if ga4 else 0,
            avg_time_on_page=ga4.avg_time_on_page if ga4 else 0.0,
            conversions=ga4.conversions if ga4 else 0.0,
            keywords=[
                KeywordEntry(
                    query=r.query,
                    url=page_url,
                    clicks=r.clicks,
                    impressions=r.impressions,
                    ctr=r.ctr,
                    position=round(r.position, 1),
                )
                for r in rows
            ],
        )
        articles.append(summary)

    articles.sort(key=lambda a: a.clicks, reverse=True)
    return articles
