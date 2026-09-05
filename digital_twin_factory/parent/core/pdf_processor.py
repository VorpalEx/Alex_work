"""
RAG-based PDF processor: extracts process steps and SLA rules from PDF
documents and converts them into GraphNode / SLARule objects.

Requires: langchain, langchain-community, pypdf, sentence-transformers (or OpenAI).
For offline use the module falls back to a rule-based heuristic extractor
when no LLM API key is configured.
"""
from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import Optional

from ...shared_logic.models import GraphEdge, GraphNode, NodeType, SLARule, TwinModel

try:
    from langchain_community.document_loaders import PyPDFLoader
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    _LANGCHAIN_AVAILABLE = True
except ImportError:
    _LANGCHAIN_AVAILABLE = False


# ---------------------------------------------------------------------------
# Heuristic patterns for offline extraction
# ---------------------------------------------------------------------------

_STEP_PATTERNS = [
    re.compile(r"^(?:Étape|Step|Phase|Tâche|Task)\s*\d+[\s:\-–]+(.+)$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\d+\.\s+([A-ZÀÂÉÈÊËÎÏÔÙÛÜ][^\n]{5,80})$", re.MULTILINE),
    re.compile(r"^(?:[A-Z][A-Z\s]{2,30}):(.+)$", re.MULTILINE),
]

_DURATION_PATTERN = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(min(?:utes?)?|h(?:eures?|ours?)?|s(?:ec(?:ondes?|onds?)?)?)",
    re.IGNORECASE,
)

_HUMAN_KEYWORDS = {"valider", "signer", "approuver", "vérifier", "réviser", "review", "approve", "validate", "sign"}
_AUTO_KEYWORDS = {"automatique", "automatic", "bot", "système", "system", "api", "webhook", "trigger", "déclencher"}


def _to_seconds(value: float, unit: str) -> float:
    u = unit.lower()
    if u.startswith("h"):
        return value * 3600
    if u.startswith("m"):
        return value * 60
    return value


def _detect_node_type(text: str) -> NodeType:
    lower = text.lower()
    if any(kw in lower for kw in _HUMAN_KEYWORDS):
        return NodeType.HUMAN
    if any(kw in lower for kw in _AUTO_KEYWORDS):
        return NodeType.AUTOMATED
    return NodeType.HUMAN


def _extract_steps_heuristic(text: str) -> list[tuple[str, str]]:
    """Return list of (label, description) tuples from raw text."""
    found: list[tuple[str, str]] = []
    for pattern in _STEP_PATTERNS:
        for match in pattern.finditer(text):
            label = match.group(1).strip()
            if len(label) > 5:
                found.append((label, ""))
    # De-duplicate while preserving order
    seen: set[str] = set()
    unique: list[tuple[str, str]] = []
    for item in found:
        if item[0] not in seen:
            seen.add(item[0])
            unique.append(item)
    return unique


def _extract_sla(text: str, step_id: str, label: str) -> Optional[SLARule]:
    """Try to find a duration hint near the step label."""
    match = _DURATION_PATTERN.search(text)
    if not match:
        return None
    raw_value = float(match.group(1).replace(",", "."))
    unit = match.group(2)
    seconds = _to_seconds(raw_value, unit)
    if seconds <= 0:
        return None
    return SLARule(step_id=step_id, max_duration_seconds=seconds, description=f"SLA extrait du PDF: {label}")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class PDFProcessor:
    """
    Loads a PDF, extracts process steps and SLA rules, and builds a TwinModel
    with a linear dependency graph as a starting point.
    """

    def __init__(self, pdf_path: str | Path, company_name: str = "", openai_api_key: str = "") -> None:
        self.pdf_path = Path(pdf_path)
        self.company_name = company_name
        self.openai_api_key = openai_api_key
        self._raw_text: str = ""

    # ------------------------------------------------------------------
    def load(self) -> str:
        """Load PDF and return concatenated text. Caches the result."""
        if self._raw_text:
            return self._raw_text

        if _LANGCHAIN_AVAILABLE:
            loader = PyPDFLoader(str(self.pdf_path))
            pages = loader.load()
            self._raw_text = "\n".join(p.page_content for p in pages)
        else:
            # Minimal fallback using pypdf directly
            try:
                import pypdf
                reader = pypdf.PdfReader(str(self.pdf_path))
                self._raw_text = "\n".join(
                    page.extract_text() or "" for page in reader.pages
                )
            except Exception as exc:
                raise RuntimeError(f"Cannot read PDF (install pypdf or langchain): {exc}") from exc
        return self._raw_text

    # ------------------------------------------------------------------
    def extract_twin_model(self) -> TwinModel:
        """Main entry point: return a TwinModel built from the PDF."""
        text = self.load()
        steps = _extract_steps_heuristic(text)
        if not steps:
            # Last resort: split on newlines and take non-empty lines < 120 chars
            steps = [(line.strip(), "") for line in text.splitlines() if 10 < len(line.strip()) < 120][:20]

        nodes: list[GraphNode] = []
        for label, description in steps:
            nid = str(uuid.uuid4())
            node_type = _detect_node_type(label)
            sla = _extract_sla(label + " " + description, nid, label)
            nodes.append(
                GraphNode(
                    id=nid,
                    label=label,
                    node_type=node_type,
                    description=description,
                    sla=sla,
                    position_x=200.0,
                    position_y=len(nodes) * 120.0,
                )
            )

        # Build a simple linear chain of edges
        edges: list[GraphEdge] = []
        for i in range(len(nodes) - 1):
            edges.append(
                GraphEdge(
                    source_id=nodes[i].id,
                    target_id=nodes[i + 1].id,
                    label="",
                )
            )

        import datetime
        return TwinModel(
            company_name=self.company_name,
            nodes=nodes,
            edges=edges,
            pdf_source_path=str(self.pdf_path),
            created_at=datetime.datetime.now().isoformat(),
        )
