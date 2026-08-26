"""Client Google Search Console : récupère les mots-clés (requêtes) par page."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

_ROW_LIMIT = 25000  # maximum autorisé par l'API par page de résultats


@dataclass
class KeywordRow:
    page: str          # URL complète de la page
    query: str         # le mot-clé / requête
    clicks: int
    impressions: int
    ctr: float         # ratio (0.05 = 5 %)
    position: float    # position moyenne


def fetch_keyword_rows(
    credentials: Credentials,
    site_url: str,
    start: date,
    end: date,
) -> list[KeywordRow]:
    """Interroge searchanalytics avec les dimensions (page, query) et pagine
    jusqu'à épuisement des résultats."""
    service = build("searchconsole", "v1", credentials=credentials, cache_discovery=False)

    rows: list[KeywordRow] = []
    start_row = 0
    while True:
        request = {
            "startDate": start.isoformat(),
            "endDate": end.isoformat(),
            "dimensions": ["page", "query"],
            "rowLimit": _ROW_LIMIT,
            "startRow": start_row,
            "dataState": "final",
        }
        response = (
            service.searchanalytics()
            .query(siteUrl=site_url, body=request)
            .execute()
        )
        batch = response.get("rows", [])
        for r in batch:
            page, query = r["keys"]
            rows.append(
                KeywordRow(
                    page=page,
                    query=query,
                    clicks=int(r.get("clicks", 0)),
                    impressions=int(r.get("impressions", 0)),
                    ctr=float(r.get("ctr", 0.0)),
                    position=float(r.get("position", 0.0)),
                )
            )
        if len(batch) < _ROW_LIMIT:
            break
        start_row += _ROW_LIMIT

    return rows
