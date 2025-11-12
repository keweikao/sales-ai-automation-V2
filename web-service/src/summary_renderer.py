"""
SummaryRenderer extracts Firestore case data and prepares context for rendering.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from google.cloud import firestore
from markdown import markdown

logger = logging.getLogger(__name__)


class SummaryNotFoundError(Exception):
    """Raised when a case cannot be located."""


class SummaryUnavailableError(Exception):
    """Raised when the case exists but has no customer summary."""


def _ensure_datetime(value: Any) -> Optional[datetime]:
    """Convert Firestore timestamps or ISO strings into timezone-aware datetimes."""
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    # Firestore may store ISO formatted strings
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


@dataclass
class SummaryContext:
    """Container for template context."""

    case_id: str
    customer_name: str
    summary_html: str
    summary_text: Optional[str]
    meeting_date: Optional[str]
    last_updated: Optional[str]
    unit: Optional[str]
    sales_rep_name: Optional[str]
    sales_rep_email: Optional[str]
    sales_rep_phone: Optional[str]
    line_url: Optional[str]
    key_decisions: list
    next_steps_customer: list
    next_steps_ichef: list
    contacts: Dict[str, Any]
    current_year: int


LOCAL_TZ = timezone(timedelta(hours=8))


class SummaryRenderer:
    """Render customer summaries to HTML using Firestore data."""

    def __init__(
        self,
        db_client: Optional[firestore.Client] = None,
        template_dir: Optional[Path] = None,
    ) -> None:
        project_id = os.getenv("GCP_PROJECT_ID")
        self.db = db_client or firestore.Client(project=project_id)
        self.template_dir = template_dir or Path(__file__).resolve().parents[1] / "templates"

    def _fetch_case(self, case_id: str) -> Dict[str, Any]:
        doc = self.db.collection("cases").document(case_id).get()
        if not doc.exists:
            raise SummaryNotFoundError(f"Case {case_id} not found")
        return doc.to_dict() or {}

    def _build_line_url(self, case_data: Dict[str, Any]) -> Optional[str]:
        line_id = (
            case_data.get("salesRepLineId")
            or case_data.get("salesRep", {}).get("lineId")
            or case_data.get("notification", {}).get("lineUrl")
        )
        if not line_id:
            return None
        if line_id.startswith("http"):
            return line_id
        return f"https://line.me/ti/p/{line_id}"

    def build_context(self, case_id: str) -> SummaryContext:
        """Return the template context for a case."""
        case_data = self._fetch_case(case_id)
        customer_summary = (
            case_data.get("analysis", {}).get("customerSummary") or {}
        )
        markdown_content = customer_summary.get("markdown")
        if not markdown_content:
            raise SummaryUnavailableError(
                f"Case {case_id} does not have customerSummary.markdown"
            )

        summary_html = markdown(
            markdown_content,
            extensions=["tables", "fenced_code", "nl2br"],
        )

        created_at = _ensure_datetime(case_data.get("createdAt"))
        updated_at = _ensure_datetime(customer_summary.get("lastEditedAt"))

        next_steps = customer_summary.get("nextSteps") or {}

        context = SummaryContext(
            case_id=case_id,
            customer_name=case_data.get("customerName", "未命名客戶"),
            summary_html=summary_html,
            summary_text=customer_summary.get("summary"),
            meeting_date=self._format_datetime(created_at),
            last_updated=self._format_datetime(updated_at),
            unit=case_data.get("unit"),
            sales_rep_name=case_data.get("salesRepName"),
            sales_rep_email=case_data.get("salesRepEmail"),
            sales_rep_phone=case_data.get("salesRepPhone"),
            line_url=self._build_line_url(case_data),
            key_decisions=customer_summary.get("keyDecisions", []),
            next_steps_customer=next_steps.get("customer", []),
            next_steps_ichef=next_steps.get("ichef", []),
            contacts=customer_summary.get("contacts", {}),
            current_year=datetime.now(LOCAL_TZ).year,
        )
        return context

    def _format_datetime(self, value: Optional[datetime]) -> Optional[str]:
        if not value:
            return None
        local_dt = value.astimezone(LOCAL_TZ)
        return local_dt.strftime("%Y-%m-%d %H:%M")

    def record_view(self, case_id: str, summary_url: Optional[str], user_agent: Optional[str]) -> None:
        """Increment delivery counters whenever a page is visited."""
        doc_ref = self.db.collection("cases").document(case_id)
        transaction = self.db.transaction()

        @firestore.transactional
        def _update(tx):
            snapshot = doc_ref.get(transaction=tx)
            if not snapshot.exists:
                return

            data = snapshot.to_dict() or {}
            delivery = data.get("delivery") or {}

            update_payload: Dict[str, Any] = {
                "delivery.viewCount": firestore.Increment(1),
                "delivery.lastViewedAt": firestore.SERVER_TIMESTAMP,
            }

            if not delivery.get("firstViewedAt"):
                update_payload["delivery.firstViewedAt"] = firestore.SERVER_TIMESTAMP

            if summary_url:
                if delivery.get("summaryUrl") != summary_url:
                    update_payload["delivery.summaryUrl"] = summary_url

            if user_agent:
                update_payload["delivery.lastViewedUserAgent"] = user_agent[:256]

            tx.update(doc_ref, update_payload)

        try:
            _update(transaction)
        except Exception as exc:  # noqa: broad-except
            logger.warning("Failed to record summary view for %s: %s", case_id, exc)
