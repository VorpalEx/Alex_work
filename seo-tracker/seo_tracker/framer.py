"""Inventaire des articles depuis Framer.

⚠️ La Server API de Framer est un SDK Node (`framer-api`), pas une API REST.
La récupération se fait donc via le script Node `framer/fetch_inventory.mjs`,
qui écrit un fichier JSON. Ce module Python se contente de LIRE ce JSON.

Format attendu du JSON (liste d'objets) :
    [{"title": "...", "slug": "...", "path": "/news/...", "url": "https://...",
      "collection": "News"}, ...]
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .config import Config


@dataclass
class FramerArticle:
    title: str
    slug: str
    url: str
    path: str
    collection: str = ""
    alt_paths: list[str] = field(default_factory=list)


def load_inventory(path: str | Path) -> list[FramerArticle]:
    """Charge l'inventaire depuis le JSON produit par framer/fetch_inventory.mjs."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    articles: list[FramerArticle] = []
    for row in data:
        if not row.get("path"):
            continue
        articles.append(
            FramerArticle(
                title=row.get("title", "") or row.get("slug", ""),
                slug=row.get("slug", ""),
                url=row.get("url", ""),
                path=row["path"],
                collection=row.get("collection", ""),
                alt_paths=list(row.get("alt_paths", []) or []),
            )
        )
    return articles


def fetch_inventory_or_empty(config: Config, log=None) -> list[FramerArticle]:
    """Renvoie l'inventaire si le fichier JSON Framer existe, sinon [] (mode GSC)."""
    path = config.framer_inventory_file
    if not path or not Path(path).exists():
        if log:
            log.info("Framer : pas d'inventaire (%s absent) — mode piloté par GSC.", path or "—")
        return []
    inv = load_inventory(path)
    if log:
        log.info("Framer : %d articles chargés depuis %s.", len(inv), path)
    return inv
