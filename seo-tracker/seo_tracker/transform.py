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
    title: str = ""
    # GSC
    clicks: int = 0
    impressions: int = 0
    ctr: float = 0.0
    avg_position: float = 0.0
    keyword_count: int = 0
    best_keyword: str = ""
    # GA4
    views: int = 0
    users: int = 0
    avg_time_on_page: float = 0.0
    conversions: float = 0.0
    keywords: list[KeywordEntry] = field(default_factory=list)
    # Comparaison avec la période précédente (variation ; None/False si non calculée).
    d_clicks: int = 0
    d_impressions: int = 0
    d_views: int = 0
    d_position: float | None = None  # positif = progression (position qui remonte)
    is_new: bool = False             # absent de la période précédente
    sources: list = field(default_factory=list)  # [(canal, sessions)] GA4, cet article


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
    exclude_regex: re.Pattern | None = None,
    min_impressions: int = 1,
    max_keywords_per_article: int = 0,
    inventory: list | None = None,
    page_sources: dict | None = None,
) -> list[ArticleSummary]:
    """Construit une liste d'ArticleSummary (avec leurs mots-clés) triée par clics.

    `inventory` (optionnel) : liste d'objets ayant .path/.url/.title (ex. FramerArticle).
    Chaque article de l'inventaire apparaît dans le résultat, même sans trafic
    (métriques à 0). Fournit aussi le vrai titre des pages.
    `page_sources` (optionnel) : {chemin -> [(canal, sessions)]} pour les sources par article.
    """
    # GA4 indexé par chemin normalisé.
    ga4_by_path: dict[str, PageMetrics] = {
        normalize_path(p): m for p, m in page_metrics.items()
    }
    sources_by_path: dict[str, list] = {
        normalize_path(p): v for p, v in (page_sources or {}).items()
    }
    # Inventaire indexé par chemin normalisé — y compris les alias (slugs FR/EN),
    # pour que la jointure GSC/GA4 fonctionne quel que soit le slug live.
    inv_by_path: dict[str, object] = {}
    for a in inventory or []:
        for p in [a.path, *getattr(a, "alt_paths", [])]:
            if p:
                inv_by_path.setdefault(normalize_path(p), a)

    grouped: dict[str, list[KeywordRow]] = defaultdict(list)
    for row in keyword_rows:
        if row.impressions < min_impressions:
            continue
        # L'exclusion l'emporte sur l'inclusion (ex. bannir /fr/news, /fr/use-case…).
        if exclude_regex and exclude_regex.search(row.page):
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
        inv = inv_by_path.get(path)

        summary = ArticleSummary(
            url=page_url,
            path=path,
            title=getattr(inv, "title", "") if inv else "",
            clicks=total_clicks,
            impressions=total_impr,
            ctr=(total_clicks / total_impr) if total_impr else 0.0,
            avg_position=round(weighted_pos, 1),
            keyword_count=len(rows),
            best_keyword=best.query,
            views=ga4.views if ga4 else 0,
            users=ga4.users if ga4 else 0,
            avg_time_on_page=ga4.avg_time_on_page if ga4 else 0.0,
            conversions=ga4.conversions if ga4 else 0.0,
            sources=list(sources_by_path.get(path, [])),
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

    # Ajoute les articles de l'inventaire sans trafic de recherche (métriques à 0).
    # Dédup par identité d'article : on saute si l'un de ses chemins candidats a
    # déjà été produit via GSC.
    seen = {a.path for a in articles}
    for inv in inventory or []:
        candidates = [normalize_path(p) for p in [inv.path, *getattr(inv, "alt_paths", [])] if p]
        if any(c in seen for c in candidates):
            continue
        path = normalize_path(inv.path)
        seen.add(path)
        ga4 = next((ga4_by_path[c] for c in candidates if c in ga4_by_path), None)
        src = next((sources_by_path[c] for c in candidates if c in sources_by_path), [])
        articles.append(
            ArticleSummary(
                url=getattr(inv, "url", ""),
                path=path,
                title=getattr(inv, "title", ""),
                clicks=0,
                impressions=0,
                ctr=0.0,
                avg_position=0.0,
                keyword_count=0,
                best_keyword="",
                views=ga4.views if ga4 else 0,
                users=ga4.users if ga4 else 0,
                avg_time_on_page=ga4.avg_time_on_page if ga4 else 0.0,
                conversions=ga4.conversions if ga4 else 0.0,
                sources=list(src),
                keywords=[],
            )
        )

    articles.sort(key=lambda a: a.clicks, reverse=True)
    return articles


def attach_deltas(
    current: list[ArticleSummary],
    previous: list[ArticleSummary],
) -> None:
    """Attache à chaque article courant sa variation vs la période précédente.

    Comparaison par chemin canonique. Pour la position, un delta positif = une
    progression (la page remonte dans les résultats). `is_new` = article absent
    de la période précédente.
    """
    prev_by_path = {a.path: a for a in previous}
    for a in current:
        p = prev_by_path.get(a.path)
        if p is None:
            a.is_new = True
            a.d_clicks = a.clicks
            a.d_impressions = a.impressions
            a.d_views = a.views
            a.d_position = None
            continue
        a.d_clicks = a.clicks - p.clicks
        a.d_impressions = a.impressions - p.impressions
        a.d_views = a.views - p.views
        # Position : plus petit = mieux, donc progression = position précédente - actuelle.
        if a.avg_position > 0 and p.avg_position > 0:
            a.d_position = round(p.avg_position - a.avg_position, 1)
        else:
            a.d_position = None
