"""Génère le dashboard HTML autonome + CSV (sans Notion).

Usage : python -m seo_tracker.report [dossier_de_sortie]
Requiert seulement les accès Google (GOOGLE_CREDENTIALS_JSON, GSC_SITE_URL, GA4_PROPERTY_ID).
"""

from __future__ import annotations

import logging
import sys
from datetime import date, timedelta
from pathlib import Path

from .config import Config, ConfigError
from .dashboard import build_data, write_csv, write_dashboard
from .framer import fetch_inventory_or_empty as _fetch_inventory
from .ga4 import fetch_page_metrics
from .google_auth import build_credentials
from .gsc import fetch_keyword_rows
from .periods import PERIODS
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

    end = config.end_date  # J-3 (données GSC consolidées)
    credentials = build_credentials(config)

    # Inventaire Framer : récupéré une seule fois (identique pour toutes les périodes).
    inventory = _fetch_inventory(config, log)

    payloads = []
    for key, label, days in PERIODS:
        start = end - timedelta(days=days - 1)
        log.info("Période %s (%s -> %s)...", label, start, end)
        keyword_rows = fetch_keyword_rows(credentials, config.gsc_site_url, start, end)
        page_metrics = fetch_page_metrics(credentials, config.ga4_property_id, start, end)
        articles = merge(
            keyword_rows,
            page_metrics,
            url_regex=config.article_url_regex,
            min_impressions=config.min_impressions,
            max_keywords_per_article=config.max_keywords_per_article,
            inventory=inventory,
        )
        n_kw = sum(len(a.keywords) for a in articles)
        log.info("  %d articles, %d mots-clés.", len(articles), n_kw)
        payloads.append((key, label, start, end, articles))

    data = build_data(payloads, date.today())
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
