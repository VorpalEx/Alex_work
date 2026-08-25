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


# Métriques demandées. 'conversions' peut ne pas exister selon la config GA4
# (remplacé par 'keyEvents') : on retente sans si l'API la refuse.
_BASE_METRICS = ["screenPageViews", "userEngagementDuration"]
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
        conversions = float(values[2]) if conversion_metric and len(values) > 2 else 0.0
        avg_time = (engagement / views) if views else 0.0
        result[path] = PageMetrics(
            path=path,
            views=views,
            avg_time_on_page=round(avg_time, 1),
            conversions=conversions,
        )
    return result
