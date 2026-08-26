"""Définition des périodes d'analyse proposées dans le dashboard."""

from __future__ import annotations

from datetime import date, timedelta

# (clé, libellé, nombre de jours)
PERIODS: list[tuple[str, str, int]] = [
    ("7d", "7 jours", 7),
    ("28d", "28 jours", 28),
    ("3m", "3 mois", 90),
    ("6m", "6 mois", 180),
    ("12m", "12 mois", 365),
]

DEFAULT_PERIOD = "28d"


def window(days: int, end: date) -> tuple[date, date]:
    """Fenêtre glissante de `days` jours se terminant à `end`."""
    return end - timedelta(days=days - 1), end
