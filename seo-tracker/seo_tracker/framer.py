"""Client Framer CMS (Server API) — source d'inventaire des articles.

Récupère la liste complète des articles publiés (même sans trafic) pour que
TOUS les articles apparaissent dans le dashboard, pas seulement ceux qui rankent.

⚠️ La forme exacte des items CMS dépend de ta collection Framer. Le module est
donc défensif et configurable (FRAMER_SLUG_FIELD / FRAMER_TITLE_FIELD). Lance
`python -m seo_tracker.framer` pour afficher la structure réelle et ajuster.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass

from .config import Config, ConfigError


@dataclass
class FramerArticle:
    title: str
    slug: str
    url: str
    path: str
    collection: str


class FramerError(RuntimeError):
    pass


def _request(base_url: str, token: str, path: str) -> dict:
    url = f"{base_url}{path}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "User-Agent": "seo-tracker/0.1",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:500]
        raise FramerError(f"HTTP {exc.code} sur {url} — {body}") from exc
    except urllib.error.URLError as exc:
        raise FramerError(f"Connexion Framer impossible ({url}) : {exc}") from exc


def _as_list(payload: dict, *keys: str) -> list:
    """Renvoie la première liste trouvée dans le payload (formes d'API variables)."""
    if isinstance(payload, list):
        return payload
    for k in keys:
        v = payload.get(k)
        if isinstance(v, list):
            return v
    for v in payload.values():
        if isinstance(v, list):
            return v
    return []


def _field(item: dict, name: str) -> str:
    """Extrait un champ, en gérant les items plats et {fieldData:{...}}."""
    for container in (item, item.get("fieldData", {}), item.get("fields", {}), item.get("data", {})):
        if isinstance(container, dict) and container.get(name) not in (None, ""):
            val = container[name]
            return val.get("value", "") if isinstance(val, dict) else str(val)
    return ""


def list_collections(config: Config) -> list[dict]:
    payload = _request(config.framer_base_url, config.framer_token, "/collections")
    return _as_list(payload, "collections", "data", "items")


def list_items(config: Config, collection_id: str) -> list[dict]:
    """Liste tous les items d'une collection (avec pagination best-effort)."""
    items: list[dict] = []
    offset, limit = 0, 100
    while True:
        payload = _request(
            config.framer_base_url,
            config.framer_token,
            f"/collections/{collection_id}/items?limit={limit}&offset={offset}",
        )
        batch = _as_list(payload, "items", "data", "results")
        items.extend(batch)
        if len(batch) < limit:
            break
        offset += limit
    return items


def fetch_inventory(config: Config) -> list[FramerArticle]:
    """Construit l'inventaire complet des articles depuis les collections configurées."""
    if not config.framer_token:
        raise ConfigError("FRAMER_API_TOKEN manquant.")
    if not config.framer_collections:
        raise ConfigError(
            "FRAMER_COLLECTIONS manquant "
            "(ex: 'collId1=/news,collId2=/blog,collId3=/use-case')."
        )

    articles: list[FramerArticle] = []
    for coll_id, prefix in config.framer_collections.items():
        for item in list_items(config, coll_id):
            slug = _field(item, config.framer_slug_field) or _field(item, "slug")
            if not slug:
                continue
            title = _field(item, config.framer_title_field) or slug
            path = f"{prefix}/{slug.strip('/')}"
            articles.append(
                FramerArticle(
                    title=title,
                    slug=slug,
                    url=f"{config.site_base_url}{path}",
                    path=path,
                    collection=coll_id,
                )
            )
    return articles


def fetch_inventory_or_empty(config: Config, log=None) -> list[FramerArticle]:
    """Comme fetch_inventory mais renvoie [] (avec avertissement) si Framer n'est
    pas configuré ou en cas d'erreur — pour ne pas casser le run principal."""
    if not config.framer_token or not config.framer_collections:
        if log:
            log.info("Framer non configuré : inventaire ignoré (piloté par GSC).")
        return []
    try:
        inv = fetch_inventory(config)
        if log:
            log.info("Framer : %d articles dans l'inventaire.", len(inv))
        return inv
    except (FramerError, ConfigError) as exc:
        if log:
            log.warning("Framer : inventaire ignoré (%s).", exc)
        return []


def probe() -> int:
    """Affiche les collections et un échantillon d'items pour découvrir la structure."""
    import sys

    try:
        config = Config.from_env(require_notion=False)
    except ConfigError as exc:
        print(f"Config invalide : {exc}", file=sys.stderr)
        return 2
    if not config.framer_token:
        print("FRAMER_API_TOKEN manquant.", file=sys.stderr)
        return 2

    print("== Collections ==")
    colls = list_collections(config)
    print(json.dumps(colls, ensure_ascii=False, indent=2)[:4000])

    if config.framer_collections:
        first = next(iter(config.framer_collections))
        print(f"\n== Échantillon d'items (collection {first}) ==")
        items = list_items(config, first)
        print(f"{len(items)} items")
        print(json.dumps(items[:2], ensure_ascii=False, indent=2)[:4000])
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(probe())
