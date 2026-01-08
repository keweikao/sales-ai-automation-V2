"""
Squarespace form submission webhook handler.

Receives form submissions from Squarespace and creates leads.
"""

from fastapi import APIRouter, Request, HTTPException
from typing import Optional
from core.schemas.lead import Lead, LeadSource
from core.database import LeadRepository

router = APIRouter()


class SquarespaceWebhookHandler:
    """Handles Squarespace form submission webhooks."""

    def __init__(self, lead_repo: Optional[LeadRepository] = None):
        self.lead_repo = lead_repo or LeadRepository()
        self.field_mappings = {
            "email": "email",
            "name": "name",
            "company": "company",
            "phone": "phone",
        }

    async def handle_submission(self, payload: dict) -> Lead:
        """
        Process a Squarespace form submission.

        Args:
            payload: Webhook payload from Squarespace

        Returns:
            Created Lead object
        """
        # Extract form data
        form_data = self._extract_form_data(payload)

        # Check for existing lead
        existing = await self.lead_repo.get_by_email(form_data.get("email", ""))
        if existing:
            # Update existing lead
            await self.lead_repo.update(existing.id, **form_data)
            return existing

        # Create new lead
        import uuid
        lead = Lead(
            id=f"lead_{uuid.uuid4().hex[:12]}",
            email=form_data.get("email", ""),
            name=form_data.get("name"),
            company=form_data.get("company"),
            phone=form_data.get("phone"),
            source=LeadSource.SQUARESPACE,
        )

        await self.lead_repo.create(lead)
        return lead

    def _extract_form_data(self, payload: dict) -> dict:
        """Extract relevant fields from Squarespace payload."""
        data = {}

        # Squarespace sends form fields in various formats
        form_submission = payload.get("formSubmission", {})
        fields = form_submission.get("data", {})

        for ss_field, our_field in self.field_mappings.items():
            if ss_field in fields:
                data[our_field] = fields[ss_field]

        return data


@router.post("/webhooks/squarespace")
async def squarespace_webhook(request: Request):
    """
    Webhook endpoint for Squarespace form submissions.

    Squarespace sends POST requests when forms are submitted.
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    handler = SquarespaceWebhookHandler()
    lead = await handler.handle_submission(payload)

    return {"status": "success", "lead_id": lead.id}
