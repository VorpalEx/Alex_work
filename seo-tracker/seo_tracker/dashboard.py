"""Génère un dashboard HTML autonome + exports CSV depuis les données fusionnées.

Ne dépend PAS de Notion : sert de mode "aperçu / SaaS léger".
"""

from __future__ import annotations

import csv
import json
import re
from datetime import date
from pathlib import Path

from .transform import ArticleSummary, normalize_path

_TEMPLATE = Path(__file__).resolve().parent.parent / "dashboard" / "template.html"
_DATA_BLOCK = re.compile(
    r'(<script id="seo-data" type="application/json">)(.*?)(</script>)',
    re.DOTALL,
)

_MONTHS_FR = [
    "janv.", "févr.", "mars", "avr.", "mai", "juin",
    "juil.", "août", "sept.", "oct.", "nov.", "déc.",
]


def _fr_date(d: date) -> str:
    return f"{d.day} {_MONTHS_FR[d.month - 1]} {d.year}"


def build_data(
    articles: list[ArticleSummary], start: date, end: date, updated: date
) -> dict:
    """Construit le dict JSON attendu par le template."""
    art_rows = [
        {
            "title": a.best_keyword or a.path,
            "path": a.path,
            "url": a.url,
            "clicks": a.clicks,
            "impressions": a.impressions,
            "ctr": round(a.ctr, 4),
            "position": round(a.avg_position, 1),
            "views": a.views,
            "avg_time": round(a.avg_time_on_page, 1),
            "keyword_count": a.keyword_count,
        }
        for a in articles
    ]
    kw_rows = [
        {
            "kw": kw.query,
            "path": normalize_path(kw.url),
            "clicks": kw.clicks,
            "impressions": kw.impressions,
            "ctr": round(kw.ctr, 4),
            "position": round(kw.position, 1),
        }
        for a in articles
        for kw in a.keywords
    ]
    return {
        "meta": {
            "site": "dillygence.com",
            "period": f"{_fr_date(start)} – {_fr_date(end)}",
            "updated": _fr_date(updated),
            "generated": f"{_fr_date(updated)} · données réelles",
            "demo": False,
        },
        "articles": art_rows,
        "keywords": kw_rows,
    }


def write_dashboard(data: dict, out_html: Path) -> None:
    """Injecte les données dans le template et écrit le fichier HTML."""
    template = _TEMPLATE.read_text(encoding="utf-8")
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    # Échappe </script> et <!-- pour ne pas casser le bloc script.
    payload = payload.replace("</", "<\\/")

    def _sub(m: re.Match) -> str:
        return f"{m.group(1)}\n{payload}\n{m.group(3)}"

    html, n = _DATA_BLOCK.subn(_sub, template)
    if n != 1:
        raise RuntimeError(
            "Bloc de données introuvable dans template.html "
            "(<script id=\"seo-data\">)."
        )
    out_html.parent.mkdir(parents=True, exist_ok=True)
    out_html.write_text(html, encoding="utf-8")


def write_csv(data: dict, out_dir: Path) -> None:
    """Écrit articles.csv et keywords.csv (séparateur ';', UTF-8 BOM pour Excel FR)."""
    out_dir.mkdir(parents=True, exist_ok=True)

    art_fields = [
        "title", "url", "path", "clicks", "impressions", "ctr",
        "position", "views", "avg_time", "keyword_count",
    ]
    with (out_dir / "articles.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=art_fields, delimiter=";")
        w.writeheader()
        w.writerows(data["articles"])

    kw_fields = ["kw", "path", "clicks", "impressions", "ctr", "position"]
    with (out_dir / "keywords.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=kw_fields, delimiter=";")
        w.writeheader()
        w.writerows(data["keywords"])
