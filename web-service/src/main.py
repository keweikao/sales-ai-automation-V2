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

from .summary_renderer import (
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
        except Exception as exc:  # noqa: broad-except
            logger.exception("Failed to render summary for %s", case_id)
            abort(500, description=str(exc))

        summary_url = request.url
        user_agent = request.headers.get("User-Agent")
        renderer.record_view(case_id, summary_url, user_agent)

        return render_template("customer_summary.html", **asdict(context))

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
        except Exception as exc:  # noqa: broad-except
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
