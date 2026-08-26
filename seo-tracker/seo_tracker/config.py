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


def _get_int(name: str, default: int) -> int:
    """Comme _get mais tolère une valeur vide (fréquent avec les variables GitHub
    non définies passées en chaîne vide) -> retombe sur le défaut."""
    raw = (os.environ.get(name) or "").strip()
    return int(raw) if raw else default


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

    # Framer (optionnel : source d'inventaire des articles)
    # La récupération se fait côté Node (framer/fetch_inventory.mjs) ; Python lit
    # seulement le JSON produit.
    framer_inventory_file: str | None
    framer_token: str | None
    framer_project_url: str | None
    site_base_url: str
    framer_collections: dict[str, str]  # {nom_collection: prefixe_url}

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

        # Pages d'articles Dillygence = /news/, /blog/, /use-case(s)/.
        # - non défini ou vide  -> filtre par défaut ci-dessous
        # - "all" / "*"         -> tout inclure (aucun filtre)
        # - toute autre valeur  -> regex personnalisée
        default_regex = r"/(news|blog|use-cases?)(/|$)"
        regex_raw = (_get("ARTICLE_URL_REGEX") or "").strip() or default_regex
        if regex_raw.lower() in ("all", "*", ".*"):
            regex = None
        else:
            regex = re.compile(regex_raw, re.IGNORECASE)

        # Framer : FRAMER_COLLECTIONS="collId1=/news,collId2=/blog,collId3=/use-case"
        collections: dict[str, str] = {}
        for pair in (_get("FRAMER_COLLECTIONS") or "").split(","):
            pair = pair.strip()
            if "=" in pair:
                cid, prefix = pair.split("=", 1)
                collections[cid.strip()] = "/" + prefix.strip().strip("/")

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
            framer_inventory_file=_get("FRAMER_INVENTORY_FILE") or "framer_inventory.json",
            framer_token=_get("FRAMER_API_TOKEN"),
            framer_project_url=_get("FRAMER_PROJECT_URL"),
            site_base_url=(_get("SITE_BASE_URL") or "https://dillygence.com").rstrip("/"),
            framer_collections=collections,
            lookback_days=_get_int("LOOKBACK_DAYS", 28),
            article_url_regex=regex,
            max_keywords_per_article=_get_int("MAX_KEYWORDS_PER_ARTICLE", 0),
            min_impressions=_get_int("MIN_IMPRESSIONS", 1),
            prune_stale=(_get("PRUNE_STALE", "false") or "").lower() == "true",
        )
