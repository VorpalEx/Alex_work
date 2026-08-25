"""Synchronisation (upsert) des articles et mots-clés vers les bases Notion."""

from __future__ import annotations

import time
from datetime import date

from notion_client import Client
from notion_client.errors import APIResponseError

from .transform import ArticleSummary, KeywordEntry

_MAX_RETRIES = 5


def _retry(fn, *args, **kwargs):
    """Réessaie sur rate-limit (429) avec backoff exponentiel."""
    delay = 1.0
    for attempt in range(_MAX_RETRIES):
        try:
            return fn(*args, **kwargs)
        except APIResponseError as exc:
            if getattr(exc, "status", None) == 429 and attempt < _MAX_RETRIES - 1:
                time.sleep(delay)
                delay *= 2
                continue
            raise


def _title(text: str) -> dict:
    return {"title": [{"text": {"content": (text or "")[:2000]}}]}


def _rich(text: str) -> dict:
    return {"rich_text": [{"text": {"content": (text or "")[:2000]}}]}


def _num(value: float | int | None) -> dict:
    return {"number": None if value is None else round(float(value), 4)}


def _plain(prop: dict) -> str:
    """Extrait le texte brut d'une propriété title/rich_text/url."""
    if not prop:
        return ""
    if prop.get("type") == "title":
        return "".join(t.get("plain_text", "") for t in prop.get("title", []))
    if prop.get("type") == "rich_text":
        return "".join(t.get("plain_text", "") for t in prop.get("rich_text", []))
    if prop.get("type") == "url":
        return prop.get("url") or ""
    return ""


class NotionSync:
    def __init__(self, token: str, db_articles: str, db_keywords: str):
        self.client = Client(auth=token)
        self.db_articles = db_articles
        self.db_keywords = db_keywords

    # -- lecture d'index ----------------------------------------------------
    def _index(self, database_id: str, key_fn) -> dict:
        """Parcourt toutes les pages d'une base et renvoie {clé: page_id}."""
        index: dict = {}
        cursor = None
        while True:
            resp = _retry(
                self.client.databases.query,
                database_id=database_id,
                start_cursor=cursor,
                page_size=100,
            )
            for page in resp["results"]:
                key = key_fn(page["properties"])
                if key is not None:
                    index[key] = page["id"]
            if not resp.get("has_more"):
                break
            cursor = resp.get("next_cursor")
        return index

    # -- articles -----------------------------------------------------------
    def sync_articles(
        self, articles: list[ArticleSummary], today: date, prune: bool
    ) -> dict[str, str]:
        """Upsert des articles. Retourne {url: page_id} pour lier les mots-clés."""
        index = self._index(
            self.db_articles,
            lambda props: _plain(props.get("URL de l'article", {})) or None,
        )
        seen: set[str] = set()
        url_to_page: dict[str, str] = {}

        for art in articles:
            props = {
                "Article": _title(art.best_keyword or art.path),
                "URL de l'article": {"url": art.url},
                "Vues": _num(art.views),
                "Temps moyen (s)": _num(art.avg_time_on_page),
                "Conversions": _num(art.conversions),
                "Clics": _num(art.clicks),
                "Impressions": _num(art.impressions),
                "CTR": _num(art.ctr),
                "Position moyenne": _num(art.avg_position),
                "Nb mots-clés": _num(art.keyword_count),
                "Meilleur mot-clé": _rich(art.best_keyword),
                "Dernière MAJ": {"date": {"start": today.isoformat()}},
            }
            page_id = index.get(art.url)
            if page_id:
                _retry(self.client.pages.update, page_id=page_id, properties=props)
            else:
                created = _retry(
                    self.client.pages.create,
                    parent={"database_id": self.db_articles},
                    properties=props,
                )
                page_id = created["id"]
            url_to_page[art.url] = page_id
            seen.add(art.url)

        if prune:
            self._prune(self.db_articles, index, seen)
        return url_to_page

    # -- mots-clés ----------------------------------------------------------
    def sync_keywords(
        self,
        articles: list[ArticleSummary],
        url_to_page: dict[str, str],
        today: date,
        prune: bool,
    ) -> None:
        def key_fn(props):
            q = _plain(props.get("Mot-clé", {}))
            u = _plain(props.get("URL de l'article", {}))
            return (q, u) if q else None

        index = self._index(self.db_keywords, key_fn)
        seen: set[tuple[str, str]] = set()

        keywords: list[KeywordEntry] = [kw for art in articles for kw in art.keywords]
        for kw in keywords:
            props = {
                "Mot-clé": _title(kw.query),
                "URL de l'article": {"url": kw.url},
                "Clics": _num(kw.clicks),
                "Impressions": _num(kw.impressions),
                "CTR": _num(kw.ctr),
                "Position": _num(kw.position),
                "Dernière MAJ": {"date": {"start": today.isoformat()}},
            }
            article_page = url_to_page.get(kw.url)
            if article_page:
                props["Article"] = {"relation": [{"id": article_page}]}

            composite = (kw.query, kw.url)
            page_id = index.get(composite)
            if page_id:
                _retry(self.client.pages.update, page_id=page_id, properties=props)
            else:
                _retry(
                    self.client.pages.create,
                    parent={"database_id": self.db_keywords},
                    properties=props,
                )
            seen.add(composite)

        if prune:
            self._prune(self.db_keywords, index, seen)

    # -- pruning ------------------------------------------------------------
    def _prune(self, database_id: str, index: dict, seen: set) -> None:
        for key, page_id in index.items():
            if key not in seen:
                _retry(self.client.pages.update, page_id=page_id, archived=True)
