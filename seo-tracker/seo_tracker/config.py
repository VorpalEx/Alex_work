"""Chargement et validation de la configuration (variables d'environnement)."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import date, timedelta

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # dotenv est optionnel en production (CI)
    pass


class ConfigError(RuntimeError):
    """Configuration manquante ou invalide."""


def _get(name: str, default: str | None = None, required: bool = False) -> str | None:
    value = os.environ.get(name, default)
    if required and not value:
        raise ConfigError(
            f"Variable d'environnement manquante : {name}. "
            "Voir .env.example pour la liste complète."
        )
    return value


@dataclass
class Config:
    # Google
    google_credentials_path: str | None
    google_credentials_json: str | None
    gsc_site_url: str
    ga4_property_id: str

    # Notion (optionnel : non requis pour le dashboard autonome)
    notion_token: str | None
    notion_db_articles: str | None
    notion_db_keywords: str | None

    # Rapport
    lookback_days: int
    article_url_regex: re.Pattern | None
    max_keywords_per_article: int
    min_impressions: int
    prune_stale: bool

    @property
    def start_date(self) -> date:
        # GSC a ~2-3 jours de latence : on décale la fenêtre de 3 jours.
        return self.end_date - timedelta(days=self.lookback_days - 1)

    @property
    def end_date(self) -> date:
        return date.today() - timedelta(days=3)

    @classmethod
    def from_env(cls, require_notion: bool = True) -> "Config":
        cred_json = _get("GOOGLE_CREDENTIALS_JSON")
        cred_path = _get("GOOGLE_APPLICATION_CREDENTIALS")
        if not cred_json and not cred_path:
            raise ConfigError(
                "Fournir GOOGLE_CREDENTIALS_JSON (contenu) ou "
                "GOOGLE_APPLICATION_CREDENTIALS (chemin du fichier JSON)."
            )

        regex_raw = _get("ARTICLE_URL_REGEX", "") or ""
        regex = re.compile(regex_raw, re.IGNORECASE) if regex_raw.strip() else None

        return cls(
            google_credentials_path=cred_path,
            google_credentials_json=cred_json,
            gsc_site_url=_get("GSC_SITE_URL", required=True),
            ga4_property_id=str(_get("GA4_PROPERTY_ID", required=True)).replace(
                "properties/", ""
            ),
            notion_token=_get("NOTION_TOKEN", required=require_notion),
            notion_db_articles=_get("NOTION_DB_ARTICLES", required=require_notion),
            notion_db_keywords=_get("NOTION_DB_KEYWORDS", required=require_notion),
            lookback_days=int(_get("LOOKBACK_DAYS", "28")),
            article_url_regex=regex,
            max_keywords_per_article=int(_get("MAX_KEYWORDS_PER_ARTICLE", "0")),
            min_impressions=int(_get("MIN_IMPRESSIONS", "1")),
            prune_stale=(_get("PRUNE_STALE", "false") or "").lower() == "true",
        )
