"""
SaaS connector: tests connectivity and retrieves live execution data
from Zapier, Make.com, and n8n.

Each provider exposes a uniform interface:
    - test_connection() -> bool
    - get_recent_executions(limit) -> list[ExecutionRecord]
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional

import requests

from ...shared_logic.models import SaaSConfig, SaaSProvider, StepStatus


@dataclass
class ExecutionRecord:
    """A single workflow execution record returned by a SaaS provider."""
    execution_id: str
    module_id: str
    status: StepStatus
    started_at: float   # Unix timestamp
    finished_at: float  # Unix timestamp
    duration_seconds: float = 0.0
    error_message: str = ""
    raw: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.duration_seconds == 0.0 and self.finished_at > self.started_at:
            self.duration_seconds = self.finished_at - self.started_at


class _BaseConnector:
    TIMEOUT = 10

    def __init__(self, config: SaaSConfig) -> None:
        self.config = config

    def _get(self, url: str, headers: dict | None = None, params: dict | None = None) -> dict[str, Any]:
        resp = requests.get(url, headers=headers or {}, params=params or {}, timeout=self.TIMEOUT)
        resp.raise_for_status()
        return resp.json()

    def test_connection(self) -> bool:
        raise NotImplementedError

    def get_recent_executions(self, limit: int = 50) -> list[ExecutionRecord]:
        raise NotImplementedError


class ZapierConnector(_BaseConnector):
    """Zapier NLA / Zap history API connector."""

    def test_connection(self) -> bool:
        try:
            self._get(
                "https://api.zapier.com/v1/zaps",
                headers={"Authorization": f"Bearer {self.config.api_key}"},
            )
            return True
        except Exception:
            return False

    def get_recent_executions(self, limit: int = 50) -> list[ExecutionRecord]:
        try:
            data = self._get(
                "https://api.zapier.com/v1/zap-runs",
                headers={"Authorization": f"Bearer {self.config.api_key}"},
                params={"limit": limit},
            )
            records: list[ExecutionRecord] = []
            for item in data.get("results", []):
                status_raw = item.get("status", "").lower()
                status = StepStatus.OK if status_raw == "success" else (
                    StepStatus.ERROR if status_raw in ("error", "failed") else StepStatus.IDLE
                )
                started = item.get("created_at_unix", time.time())
                finished = item.get("updated_at_unix", started)
                records.append(
                    ExecutionRecord(
                        execution_id=str(item.get("id", "")),
                        module_id=str(item.get("zap_id", "")),
                        status=status,
                        started_at=float(started),
                        finished_at=float(finished),
                        raw=item,
                    )
                )
            return records
        except Exception:
            return []


class MakeConnector(_BaseConnector):
    """Make.com (formerly Integromat) API connector."""

    def _base_url(self) -> str:
        return self.config.base_url or "https://eu1.make.com/api/v2"

    def test_connection(self) -> bool:
        try:
            self._get(
                f"{self._base_url()}/users/me",
                headers={"Authorization": f"Token {self.config.api_key}"},
            )
            return True
        except Exception:
            return False

    def get_recent_executions(self, limit: int = 50) -> list[ExecutionRecord]:
        try:
            data = self._get(
                f"{self._base_url()}/scenarios/logs",
                headers={"Authorization": f"Token {self.config.api_key}"},
                params={"pg[limit]": limit},
            )
            records: list[ExecutionRecord] = []
            for item in data.get("scenariologs", []):
                status_raw = item.get("status", "").lower()
                status = StepStatus.OK if status_raw == "success" else (
                    StepStatus.ERROR if status_raw in ("error", "warning") else StepStatus.IDLE
                )
                started = item.get("imtStartedAt", time.time())
                finished = item.get("imtStoppedAt", started)
                records.append(
                    ExecutionRecord(
                        execution_id=str(item.get("id", "")),
                        module_id=str(item.get("scenarioId", "")),
                        status=status,
                        started_at=float(started),
                        finished_at=float(finished),
                        raw=item,
                    )
                )
            return records
        except Exception:
            return []


class N8nConnector(_BaseConnector):
    """n8n self-hosted / cloud API connector."""

    def _base_url(self) -> str:
        return self.config.base_url or "http://localhost:5678/api/v1"

    def test_connection(self) -> bool:
        try:
            self._get(
                f"{self._base_url()}/workflows",
                headers={"X-N8N-API-KEY": self.config.api_key},
            )
            return True
        except Exception:
            return False

    def get_recent_executions(self, limit: int = 50) -> list[ExecutionRecord]:
        try:
            data = self._get(
                f"{self._base_url()}/executions",
                headers={"X-N8N-API-KEY": self.config.api_key},
                params={"limit": limit, "includeData": "false"},
            )
            records: list[ExecutionRecord] = []
            for item in data.get("data", []):
                status_raw = item.get("finished", False)
                err = item.get("data", {}) if isinstance(item.get("data"), dict) else {}
                status = StepStatus.OK if status_raw else StepStatus.ERROR
                started = item.get("startedAt", "")
                finished = item.get("stoppedAt", "")
                import datetime
                def _parse(ts: str) -> float:
                    try:
                        return datetime.datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
                    except Exception:
                        return time.time()
                t_start = _parse(started) if started else time.time()
                t_end = _parse(finished) if finished else t_start
                records.append(
                    ExecutionRecord(
                        execution_id=str(item.get("id", "")),
                        module_id=str(item.get("workflowId", "")),
                        status=status,
                        started_at=t_start,
                        finished_at=t_end,
                        raw=item,
                    )
                )
            return records
        except Exception:
            return []


def make_connector(config: SaaSConfig) -> _BaseConnector:
    """Factory: return the right connector for the given provider."""
    mapping = {
        SaaSProvider.ZAPIER: ZapierConnector,
        SaaSProvider.MAKE: MakeConnector,
        SaaSProvider.N8N: N8nConnector,
    }
    cls = mapping.get(config.provider, _BaseConnector)
    return cls(config)
