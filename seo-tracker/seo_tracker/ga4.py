"""Client GA4 Data API : vues, temps d'engagement et conversions par page."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    RunReportRequest,
)
from google.api_core.exceptions import InvalidArgument
from google.oauth2.service_account import Credentials


@dataclass
class PageMetrics:
    path: str          # chemin de la page (ex: /blog/mon-article)
    views: int
    avg_time_on_page: float  # secondes (engagement / vues)
    conversions: float
    users: int = 0     # utilisateurs (totalUsers) de la page


@dataclass
class Audience:
    """Données d'audience GA4 pour tout le site, sur une période."""
    total_users: int = 0
    new_users: int = 0
    sessions: int = 0
    views: int = 0
    engagement_rate: float = 0.0        # ratio 0..1
    avg_session_duration: float = 0.0   # secondes
    by_device: list = None              # [(appareil, utilisateurs)]
    by_country: list = None             # [(pays, utilisateurs)]
    by_channel: list = None             # [(canal, sessions)]

    def __post_init__(self):
        self.by_device = self.by_device or []
        self.by_country = self.by_country or []
        self.by_channel = self.by_channel or []


# Métriques demandées. 'conversions' peut ne pas exister selon la config GA4
# (remplacé par 'keyEvents') : on retente sans si l'API la refuse.
_BASE_METRICS = ["screenPageViews", "userEngagementDuration", "totalUsers"]
_CONVERSION_METRICS = ["conversions", "keyEvents"]


def _run(
    client: BetaAnalyticsDataClient,
    property_id: str,
    start: date,
    end: date,
    metrics: list[str],
) -> "object":
    request = RunReportRequest(
        property=f"properties/{property_id}",
        date_ranges=[DateRange(start_date=start.isoformat(), end_date=end.isoformat())],
        dimensions=[Dimension(name="pagePath")],
        metrics=[Metric(name=m) for m in metrics],
        limit=250000,
    )
    return client.run_report(request)


def fetch_page_metrics(
    credentials: Credentials,
    property_id: str,
    start: date,
    end: date,
) -> dict[str, PageMetrics]:
    """Retourne un dict chemin_de_page -> PageMetrics."""
    client = BetaAnalyticsDataClient(credentials=credentials)

    conversion_metric = None
    metrics = list(_BASE_METRICS)
    for candidate in _CONVERSION_METRICS:
        try:
            response = _run(client, property_id, start, end, metrics + [candidate])
            conversion_metric = candidate
            break
        except InvalidArgument:
            continue
    else:
        # Aucune métrique de conversion disponible : on continue sans.
        response = _run(client, property_id, start, end, metrics)

    result: dict[str, PageMetrics] = {}
    for row in response.rows:
        path = row.dimension_values[0].value
        values = [mv.value for mv in row.metric_values]
        views = int(float(values[0] or 0))
        engagement = float(values[1] or 0.0)
        users = int(float(values[2] or 0))
        conversions = float(values[3]) if conversion_metric and len(values) > 3 else 0.0
        avg_time = (engagement / views) if views else 0.0
        result[path] = PageMetrics(
            path=path,
            views=views,
            avg_time_on_page=round(avg_time, 1),
            conversions=conversions,
            users=users,
        )
    return result


def fetch_page_sources(
    credentials: Credentials,
    property_id: str,
    start: date,
    end: date,
) -> dict[str, list[tuple[str, int]]]:
    """Sources de trafic par page : {chemin -> [(canal, sessions), ...]} trié décroissant."""
    client = BetaAnalyticsDataClient(credentials=credentials)
    request = RunReportRequest(
        property=f"properties/{property_id}",
        date_ranges=[DateRange(start_date=start.isoformat(), end_date=end.isoformat())],
        dimensions=[Dimension(name="pagePath"), Dimension(name="sessionDefaultChannelGroup")],
        metrics=[Metric(name="sessions")],
        limit=250000,
    )
    resp = client.run_report(request)
    by_path: dict[str, list[tuple[str, int]]] = {}
    for r in resp.rows:
        path = r.dimension_values[0].value
        channel = r.dimension_values[1].value or "(non défini)"
        sessions = int(float(r.metric_values[0].value or 0))
        if sessions <= 0:
            continue
        by_path.setdefault(path, []).append((channel, sessions))
    for path in by_path:
        by_path[path].sort(key=lambda x: x[1], reverse=True)
    return by_path


def _breakdown(
    client: BetaAnalyticsDataClient,
    property_id: str,
    start: date,
    end: date,
    dimension: str,
    metric: str,
    limit: int = 25,
) -> list[tuple[str, int]]:
    """Retourne [(valeur_dimension, valeur_métrique)] trié décroissant."""
    request = RunReportRequest(
        property=f"properties/{property_id}",
        date_ranges=[DateRange(start_date=start.isoformat(), end_date=end.isoformat())],
        dimensions=[Dimension(name=dimension)],
        metrics=[Metric(name=metric)],
        limit=limit,
    )
    resp = client.run_report(request)
    rows = [
        (r.dimension_values[0].value or "(non défini)", int(float(r.metric_values[0].value or 0)))
        for r in resp.rows
    ]
    rows.sort(key=lambda x: x[1], reverse=True)
    return rows


def fetch_audience(
    credentials: Credentials,
    property_id: str,
    start: date,
    end: date,
    *,
    totals_only: bool = False,
) -> Audience:
    """Audience GA4 de tout le site : totaux + répartitions appareil/pays/canal.

    `totals_only` : ne récupère que les totaux (utile pour la période de
    comparaison, où seuls les deltas globaux sont nécessaires).
    """
    client = BetaAnalyticsDataClient(credentials=credentials)

    # Totaux (sans dimension).
    totals_req = RunReportRequest(
        property=f"properties/{property_id}",
        date_ranges=[DateRange(start_date=start.isoformat(), end_date=end.isoformat())],
        metrics=[
            Metric(name="totalUsers"),
            Metric(name="newUsers"),
            Metric(name="sessions"),
            Metric(name="screenPageViews"),
            Metric(name="engagementRate"),
            Metric(name="averageSessionDuration"),
        ],
    )
    tr = client.run_report(totals_req)
    aud = Audience()
    if tr.rows:
        v = [mv.value for mv in tr.rows[0].metric_values]
        aud.total_users = int(float(v[0] or 0))
        aud.new_users = int(float(v[1] or 0))
        aud.sessions = int(float(v[2] or 0))
        aud.views = int(float(v[3] or 0))
        aud.engagement_rate = round(float(v[4] or 0.0), 4)
        aud.avg_session_duration = round(float(v[5] or 0.0), 1)

    if not totals_only:
        aud.by_device = _breakdown(client, property_id, start, end, "deviceCategory", "totalUsers", limit=10)
        aud.by_country = _breakdown(client, property_id, start, end, "country", "totalUsers", limit=8)
        aud.by_channel = _breakdown(
            client, property_id, start, end, "sessionDefaultChannelGroup", "sessions", limit=10
        )
    return aud
