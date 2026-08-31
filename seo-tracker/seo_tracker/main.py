"""Point d'entrée : collecte GSC + GA4, fusion, puis synchro Notion."""

from __future__ import annotations

import logging
import sys

from .config import Config, ConfigError
from .framer import fetch_inventory_or_empty as _fetch_inventory
from .ga4 import fetch_page_metrics
from .google_auth import build_credentials
from .gsc import fetch_keyword_rows
from .notion_sync import NotionSync
from .transform import merge

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("seo-tracker")


def run() -> int:
    try:
        config = Config.from_env()
    except ConfigError as exc:
        log.error("Configuration invalide : %s", exc)
        return 2

    start, end = config.start_date, config.end_date
    log.info("Fenêtre d'analyse : %s -> %s", start, end)

    credentials = build_credentials(config)

    log.info("Search Console : récupération des mots-clés (%s)...", config.gsc_site_url)
    keyword_rows = fetch_keyword_rows(credentials, config.gsc_site_url, start, end)
    log.info("  %d couples (page, mot-clé) récupérés.", len(keyword_rows))

    log.info("GA4 : récupération de l'audience par page (propriété %s)...", config.ga4_property_id)
    page_metrics = fetch_page_metrics(credentials, config.ga4_property_id, start, end)
    log.info("  %d pages avec audience récupérées.", len(page_metrics))

    inventory = _fetch_inventory(config, log)

    articles = merge(
        keyword_rows,
        page_metrics,
        url_regex=config.article_url_regex,
        exclude_regex=config.article_url_exclude,
        min_impressions=config.min_impressions,
        max_keywords_per_article=config.max_keywords_per_article,
        inventory=inventory,
    )
    total_keywords = sum(len(a.keywords) for a in articles)
    log.info("Fusion : %d articles, %d mots-clés au total.", len(articles), total_keywords)

    if not articles:
        log.warning(
            "Aucun article à synchroniser. Vérifie GSC_SITE_URL, la fenêtre de dates "
            "et ARTICLE_URL_REGEX."
        )
        return 0

    sync = NotionSync(
        config.notion_token, config.notion_db_articles, config.notion_db_keywords
    )

    log.info("Notion : synchronisation des articles...")
    url_to_page = sync.sync_articles(articles, end, config.prune_stale)

    log.info("Notion : synchronisation des mots-clés...")
    sync.sync_keywords(articles, url_to_page, end, config.prune_stale)

    log.info("Terminé ✅  %d articles / %d mots-clés synchronisés.", len(articles), total_keywords)
    return 0


if __name__ == "__main__":
    sys.exit(run())
