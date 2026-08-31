"""Génère un dashboard HTML autonome + exports CSV depuis les données fusionnées.

Ne dépend PAS de Notion : sert de mode "aperçu / SaaS léger".
Le dashboard embarque plusieurs périodes (7j/28j/3m/6m/12m), sélectionnables
côté navigateur.
"""

from __future__ import annotations

import csv
import json
import re
from datetime import date
from pathlib import Path

from .periods import DEFAULT_PERIOD
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


def _rows(articles: list[ArticleSummary]) -> dict:
    """Transforme une liste d'ArticleSummary en dict {articles, keywords}."""
    art_rows = [
        {
            "title": a.title or a.best_keyword or a.path,
            "path": a.path,
            "url": a.url,
            "clicks": a.clicks,
            "impressions": a.impressions,
            "ctr": round(a.ctr, 4),
            "position": round(a.avg_position, 1),
            "views": a.views,
            "avg_time": round(a.avg_time_on_page, 1),
            "keyword_count": a.keyword_count,
            # Variation vs période précédente.
            "d_clicks": a.d_clicks,
            "d_impressions": a.d_impressions,
            "d_views": a.d_views,
            "d_position": a.d_position,
            "is_new": a.is_new,
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
    return {"articles": art_rows, "keywords": kw_rows}


def build_data(
    period_payloads: list[tuple],
    updated: date,
    *,
    default: str = DEFAULT_PERIOD,
) -> dict:
    """Construit le dict JSON multi-périodes attendu par le template.

    period_payloads : liste de (clé, libellé, start, end, prev_start, prev_end, articles).
    """
    periods = [
        {
            "key": key,
            "label": label,
            "period": f"{_fr_date(start)} – {_fr_date(end)}",
            "prev_period": f"{_fr_date(prev_start)} – {_fr_date(prev_end)}",
            **_rows(articles),
        }
        for key, label, start, end, prev_start, prev_end, articles in period_payloads
    ]
    keys = {p["key"] for p in periods}
    return {
        "meta": {
            "site": "dillygence.com",
            "updated": _fr_date(updated),
            "generated": f"{_fr_date(updated)} · données réelles",
            "demo": False,
        },
        "periods": periods,
        "default": default if default in keys else (periods[0]["key"] if periods else ""),
    }


def _default_rows(data: dict) -> dict:
    for p in data.get("periods", []):
        if p["key"] == data.get("default"):
            return p
    return data.get("periods", [{}])[0] if data.get("periods") else {"articles": [], "keywords": []}


def write_dashboard(data: dict, out_html: Path) -> None:
    """Injecte les données dans le template et écrit le fichier HTML."""
    template = _TEMPLATE.read_text(encoding="utf-8")
    payload = json.dumps(data, ensure_ascii=False, indent=2).replace("</", "<\\/")

    def _sub(m: re.Match) -> str:
        return f"{m.group(1)}\n{payload}\n{m.group(3)}"

    html, n = _DATA_BLOCK.subn(_sub, template)
    if n != 1:
        raise RuntimeError('Bloc de données introuvable dans template.html (<script id="seo-data">).')
    out_html.parent.mkdir(parents=True, exist_ok=True)
    out_html.write_text(html, encoding="utf-8")


def write_csv(data: dict, out_dir: Path) -> None:
    """Écrit articles.csv et keywords.csv de la période par défaut (';', UTF-8 BOM)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = _default_rows(data)

    art_fields = [
        "title", "url", "path", "clicks", "impressions", "ctr",
        "position", "views", "avg_time", "keyword_count",
    ]
    with (out_dir / "articles.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=art_fields, delimiter=";")
        w.writeheader()
        w.writerows(rows.get("articles", []))

    kw_fields = ["kw", "path", "clicks", "impressions", "ctr", "position"]
    with (out_dir / "keywords.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=kw_fields, delimiter=";")
        w.writeheader()
        w.writerows(rows.get("keywords", []))
