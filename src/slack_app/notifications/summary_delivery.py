"""
summary_delivery.py

Handles final approval flows: builds summary URLs, sends SMS via Twilio,
and updates Firestore delivery metadata.
"""

from __future__ import annotations

import logging
import os
import re
import secrets
import string
from dataclasses import dataclass
from typing import Any, Dict, Optional

from google.cloud import firestore

try:
    from twilio.rest import Client as TwilioClient
except ImportError:  # pragma: no cover - Twilio optional in some environments
    TwilioClient = None  # type: ignore

logger = logging.getLogger(__name__)

PHONE_REGEX = re.compile(r"^\+?[0-9\-]{8,20}$")


@dataclass
class DeliveryResult:
    status: str
    summary_url: str
    phone: Optional[str] = None
    sid: Optional[str] = None
    error: Optional[str] = None


class SummaryDeliveryService:
    """Encapsulates summary delivery logic (approval + SMS + Firestore updates)."""

    def __init__(
        self,
        db_client: firestore.Client,
        summary_base_url: Optional[str] = None,
        short_url_base: Optional[str] = None,
    ) -> None:
        self.db = db_client
        summary_base = summary_base_url or os.getenv("SUMMARY_BASE_URL") or ""
        self.summary_base_url = summary_base.rstrip("/") if summary_base else ""
        short_base = short_url_base if short_url_base is not None else os.getenv("SHORT_URL_BASE")
        if short_base is None and self.summary_base_url:
            candidate = self.summary_base_url.rstrip("/")
            if candidate.endswith("/summary"):
                candidate = candidate[: -len("/summary")]
            short_base = candidate.rstrip("/") + "/s"
        self.short_url_base = short_base.rstrip("/") if short_base else None
        self.twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.twilio_number = os.getenv("TWILIO_PHONE_NUMBER")
        self.twilio_enabled = all([self.twilio_sid, self.twilio_token, self.twilio_number, TwilioClient])
        self.twilio_client = (
            TwilioClient(self.twilio_sid, self.twilio_token) if self.twilio_enabled else None
        )

    def _build_summary_url(self, case_id: str) -> str:
        if self.summary_base_url:
            base = self.summary_base_url
        else:
            base = "https://sales.ichefpos.com"
        if not base.endswith("/summary"):
            base = base.rstrip("/") + "/summary"
        return f"{base}/{case_id}"

    def _fetch_case(self, case_id: str) -> Dict[str, Any]:
        doc = self.db.collection("cases").document(case_id).get()
        if not doc.exists:
            raise ValueError(f"Case {case_id} not found")
        return doc.to_dict() or {}

    def _validate_phone(self, phone_number: str) -> str:
        candidate = phone_number.strip()
        if not PHONE_REGEX.match(candidate):
            raise ValueError("無效的電話號碼格式，請輸入包含國碼的數字（例：+886912345678）")
        return candidate

    def send_summary(
        self,
        case_id: str,
        initiated_by: str,
        phone_number: Optional[str] = None,
    ) -> DeliveryResult:
        """Send the summary link via SMS (if Twilio configured)."""
        case_data = self._fetch_case(case_id)
        phone = phone_number or case_data.get("customerPhone")
        if not phone:
            raise ValueError("此案件尚未設定客戶電話，無法發送摘要")
        phone = self._validate_phone(phone)

        summary_page_url = self._build_summary_url(case_id)
        if self.short_url_base:
            summary_url = self._ensure_short_url(case_id, summary_page_url)
        else:
            summary_url = summary_page_url

        sales_rep = case_data.get("salesRepName") or "iCHEF 顧問"
        message = (
            f"您好，我是 iCHEF 的 {sales_rep}。\n\n"
            "感謝您今天與我們的會議！我已為您整理好會議摘要：\n"
            f"{summary_url}\n\n"
            "若有任何問題，歡迎隨時與我聯繫 📞"
        )

        delivery_status = "skipped"
        sid = None
        error = None

        if self.twilio_client:
            try:
                result = self.twilio_client.messages.create(
                    body=message,
                    from_=self.twilio_number,
                    to=phone,
                )
                sid = result.sid
                delivery_status = "sent"
                logger.info("SMS sent (sid=%s, case=%s)", sid, case_id)
            except Exception as exc:  # pragma: no cover - depends on Twilio runtime
                delivery_status = "failed"
                error = str(exc)
                logger.error("SMS sending failed for %s: %s", case_id, exc)
        else:
            error = "TWILIO_NOT_CONFIGURED"
            logger.warning(
                "Twilio credentials missing, skipping SMS send for %s (phone=%s)",
                case_id,
                phone,
            )

        self._record_delivery(
            case_id=case_id,
            phone=phone,
            summary_url=summary_url,
            summary_page_url=summary_page_url,
            initiated_by=initiated_by,
            status=delivery_status,
            sid=sid,
            error=error,
        )

        return DeliveryResult(
            status=delivery_status,
            summary_url=summary_url,
            phone=phone,
            sid=sid,
            error=error,
        )

    def _record_delivery(
        self,
        *,
        case_id: str,
        phone: str,
        summary_url: str,
        summary_page_url: str,
        initiated_by: str,
        status: str,
        sid: Optional[str],
        error: Optional[str],
    ) -> None:
        doc_ref = self.db.collection("cases").document(case_id)
        update_payload: Dict[str, Any] = {
            "delivery.customerPhone": phone,
            "delivery.summaryUrl": summary_url,
            "delivery.summaryPageUrl": summary_page_url,
            "delivery.smsStatus": status,
            "delivery.confirmedBy": initiated_by,
            "delivery.summaryApprovedAt": firestore.SERVER_TIMESTAMP,
        }
        if status == "sent":
            update_payload["delivery.sentAt"] = firestore.SERVER_TIMESTAMP
            update_payload["delivery.smsSid"] = sid
            update_payload["delivery.smsError"] = None
        else:
            update_payload["delivery.smsError"] = error or "unknown_error"

        doc_ref.update(update_payload)

    def _ensure_short_url(self, case_id: str, target_url: str) -> str:
        """Ensure a short URL exists for a case before sending to customer."""
        case_ref = self.db.collection("cases").document(case_id)
        snapshot = case_ref.get()
        if not snapshot.exists:
            raise ValueError(f"Case {case_id} not found when creating short url")

        delivery = (snapshot.to_dict() or {}).get("delivery") or {}
        existing = delivery.get("shortUrl")
        if existing:
            return existing

        for _ in range(5):
            code = self._generate_short_code()
            short_ref = self.db.collection("shortUrls").document(code)
            if short_ref.get().exists:
                continue
            short_url = f"{self.short_url_base}/{code}"
            short_ref.set(
                {
                    "caseId": case_id,
                    "targetUrl": target_url,
                    "createdAt": firestore.SERVER_TIMESTAMP,
                    "clickCount": 0,
                    "active": True,
                }
            )
            case_ref.update(
                {
                    "delivery.shortUrl": short_url,
                    "delivery.shortCode": code,
                    "delivery.summaryPageUrl": target_url,
                }
            )
            return short_url

        raise RuntimeError("短網址生成失敗，請稍後再試")

    @staticmethod
    def _generate_short_code(length: int = 7) -> str:
        alphabet = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(length))
