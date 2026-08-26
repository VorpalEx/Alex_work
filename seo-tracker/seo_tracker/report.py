"""Génère le dashboard HTML autonome + CSV (sans Notion).

Usage : python -m seo_tracker.report [dossier_de_sortie]
Requiert seulement les accès Google (GOOGLE_CREDENTIALS_JSON, GSC_SITE_URL, GA4_PROPERTY_ID).
"""

from __future__ import annotations

import logging
import sys
from datetime import date
from pathlib import Path

from .config import Config, ConfigError
from .dashboard import build_data, write_csv, write_dashboard
from .framer import fetch_inventory_or_empty as _fetch_inventory
from .ga4 import fetch_page_metrics
from .google_auth import build_credentials
from .gsc import fetch_keyword_rows
from .transform import merge

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("seo-report")


def run(out_dir: Path) -> int:
    try:
        config = Config.from_env(require_notion=False)
    except ConfigError as exc:
        log.error("Configuration invalide : %s", exc)
        return 2

    start, end = config.start_date, config.end_date
    log.info("Fenêtre d'analyse : %s -> %s", start, end)

    credentials = build_credentials(config)

    log.info("Search Console : récupération des mots-clés...")
    keyword_rows = fetch_keyword_rows(credentials, config.gsc_site_url, start, end)
    log.info("  %d couples (page, mot-clé) récupérés.", len(keyword_rows))

    log.info("GA4 : récupération de l'audience par page...")
    page_metrics = fetch_page_metrics(credentials, config.ga4_property_id, start, end)
    log.info("  %d pages récupérées.", len(page_metrics))

    inventory = _fetch_inventory(config, log)

    articles = merge(
        keyword_rows,
        page_metrics,
        url_regex=config.article_url_regex,
        min_impressions=config.min_impressions,
        max_keywords_per_article=config.max_keywords_per_article,
        inventory=inventory,
    )
    total_keywords = sum(len(a.keywords) for a in articles)
    log.info("Fusion : %d articles, %d mots-clés.", len(articles), total_keywords)

    data = build_data(articles, start, end, date.today())
    html_path = out_dir / "dashboard.html"
    write_dashboard(data, html_path)
    write_csv(data, out_dir)

    log.info("Dashboard écrit : %s", html_path)
    log.info("Exports CSV : %s/articles.csv, %s/keywords.csv", out_dir, out_dir)
    log.info("Terminé ✅")
    return 0


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("out")
    sys.exit(run(target))
