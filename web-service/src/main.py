"""
Customer summary web service entrypoint.
"""

from __future__ import annotations

import logging
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict

from flask import Flask, abort, jsonify, redirect, render_template, request
from google.cloud import firestore

from summary_renderer import (
    SummaryNotFoundError,
    SummaryRenderer,
    SummaryUnavailableError,
)

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
)
logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "templates"
STATIC_DIR = Path(__file__).resolve().parents[1] / "static"


def create_app() -> Flask:
    """Flask application factory."""
    app = Flask(
        __name__,
        template_folder=str(TEMPLATE_DIR),
        static_folder=str(STATIC_DIR),
    )
    renderer = SummaryRenderer()

    @app.get("/health")
    def health() -> Dict[str, Any]:
        return {"status": "ok"}

    @app.get("/summary/<case_id>")
    def render_summary(case_id: str):
        logger.info("Rendering summary page for case %s", case_id)
        try:
            context = renderer.build_context(case_id)
        except SummaryNotFoundError as exc:
            logger.warning("Summary requested for missing case %s", case_id)
            abort(404, description=str(exc))
        except SummaryUnavailableError as exc:
            logger.warning("Summary unavailable for %s", case_id)
            abort(404, description=str(exc))
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to render summary for %s", case_id)
            abort(500, description=str(exc))

        summary_url = request.url
        user_agent = request.headers.get("User-Agent")
        renderer.record_view(case_id, summary_url, user_agent)

        return render_template("customer_summary.html", **asdict(context))

    @app.get("/edit/<case_id>")
    def edit_summary(case_id: str):
        """Edit page for sales reps to modify the summary."""
        logger.info("Loading edit page for case %s", case_id)
        try:
            case_data = renderer._fetch_case(case_id)
            customer_summary = case_data.get("analysis", {}).get("customerSummary") or {}
            markdown_content = customer_summary.get("markdown", "")
            
            if not markdown_content:
                # Fallback: try to get markdown from agent4.data
                agent4_data = case_data.get("analysis", {}).get("agents", {}).get("agent4", {}).get("data", {})
                markdown_content = agent4_data.get("markdown", "")
                
                # Legacy fallback: email_body
                if not markdown_content:
                    email_body = agent4_data.get("email_body", "")
                    email_subject = agent4_data.get("email_subject", "")
                    if email_body:
                        markdown_content = f"# {email_subject}\n\n{email_body}" if email_subject else email_body
            
            edit_count = customer_summary.get("editCount", 0)
            last_updated = customer_summary.get("lastEditedAt")
            
            # Get customer and sales rep info
            customer_name = case_data.get("customerName", "未命名客戶")
            sales_rep_name = case_data.get("salesRepName") or case_data.get("uploadedByName") or "業務代表"
            
            return render_template(
                "edit_summary.html",
                case_id=case_id,
                customer_name=customer_name,
                sales_rep_name=sales_rep_name,
                markdown_content=markdown_content,
                edit_count=edit_count,
                last_updated=renderer._format_datetime(last_updated) if last_updated else None,
            )
        except SummaryNotFoundError as exc:
            abort(404, description=str(exc))
        except Exception as exc:
            logger.exception("Failed to load edit page for %s", case_id)
            abort(500, description=str(exc))

    @app.put("/api/summary/<case_id>")
    def save_summary(case_id: str):
        """API to save edited summary."""
        logger.info("Saving summary for case %s", case_id)
        try:
            data = request.get_json()
            if not data or "markdown" not in data:
                return jsonify({"error": "Missing markdown content"}), 400
            
            new_markdown = data["markdown"]
            
            # Fetch current summary to preserve original
            doc_ref = renderer.db.collection("cases").document(case_id)
            doc = doc_ref.get()
            if not doc.exists:
                return jsonify({"error": f"Case {case_id} not found"}), 404
            
            case_data = doc.to_dict() or {}
            customer_summary = case_data.get("analysis", {}).get("customerSummary") or {}
            
            # Preserve original markdown if this is first edit
            original_markdown = customer_summary.get("originalMarkdown") or customer_summary.get("markdown")
            edit_count = customer_summary.get("editCount", 0) + 1
            
            # Update Firestore
            doc_ref.update({
                "analysis.customerSummary.markdown": new_markdown,
                "analysis.customerSummary.originalMarkdown": original_markdown,
                "analysis.customerSummary.isEdited": True,
                "analysis.customerSummary.editCount": edit_count,
                "analysis.customerSummary.lastEditedAt": firestore.SERVER_TIMESTAMP,
            })
            
            logger.info("Summary saved for case %s (edit #%d)", case_id, edit_count)
            return jsonify({"success": True, "editCount": edit_count})
            
        except Exception as exc:
            logger.exception("Failed to save summary for %s", case_id)
            return jsonify({"error": str(exc)}), 500

    @app.get("/report/upload/<report_id>")
    def view_upload_report(report_id: str):
        """Display weekly upload report page."""
        logger.info("Viewing upload report %s", report_id)

        doc = renderer.db.collection("upload_reports").document(report_id).get()
        if not doc.exists:
            abort(404, description="報表不存在")

        report_data = doc.to_dict()
        return render_template("upload_report.html", report=report_data)

    @app.get("/s/<code>")
    def redirect_short_link(code: str):
        short_ref = renderer.db.collection("shortUrls").document(code)
        doc = short_ref.get()
        if not doc.exists:
            abort(404, description="短網址不存在")

        data = doc.to_dict() or {}
        target_url = data.get("targetUrl")
        if not target_url:
            abort(404, description="短網址未設定目標")

        try:
            short_ref.update(
                {
                    "clickCount": firestore.Increment(1),
                    "lastClickedAt": firestore.SERVER_TIMESTAMP,
                }
            )
            renderer.db.collection("cases").document(data.get("caseId")).update(
                {
                    "delivery.shortUrlLastClickedAt": firestore.SERVER_TIMESTAMP,
                    "delivery.lastViewedViaShortUrl": firestore.SERVER_TIMESTAMP,
                }
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed updating short url stats for %s: %s", code, exc)

        return redirect(target_url, code=302)

    @app.errorhandler(404)
    def not_found(err):  # type: ignore[override]
        return (
            render_template(
                "error.html",
                status_code=404,
                message=err.description if hasattr(err, "description") else str(err),
            ),
            404,
        )

    @app.errorhandler(500)
    def internal_error(err):  # type: ignore[override]
        return (
            render_template(
                "error.html",
                status_code=500,
                message="系統目前無法生成摘要，請稍後再試。",
            ),
            500,
        )

    return app


app = create_app()
