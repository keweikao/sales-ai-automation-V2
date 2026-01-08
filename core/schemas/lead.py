"""
Lead schema definitions.

Defines data structures for lead tracking across the sales funnel.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class LeadSource(str, Enum):
    """Origin of the lead."""
    SQUARESPACE = "squarespace"
    LINKEDIN = "linkedin"
    REFERRAL = "referral"
    WEBSITE = "website"
    EVENT = "event"
    COLD_OUTREACH = "cold_outreach"
    OTHER = "other"


class LeadStatus(str, Enum):
    """Current status in the sales funnel."""
    NEW = "new"
    CONTACTED = "contacted"
    MQL = "mql"  # Marketing Qualified Lead
    SQL = "sql"  # Sales Qualified Lead
    OPPORTUNITY = "opportunity"
    NEGOTIATION = "negotiation"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


class UTMData(BaseModel):
    """UTM tracking parameters."""
    source: Optional[str] = None
    medium: Optional[str] = None
    campaign: Optional[str] = None
    term: Optional[str] = None
    content: Optional[str] = None


class Lead(BaseModel):
    """
    Core Lead model representing a potential customer.

    Used across modules:
    - 01-lead-source: Creation and tracking
    - 02-mql-qualification: Scoring and qualification
    - 03-sales-conversation: Context for analysis
    """
    id: str = Field(..., description="Unique lead identifier")

    # Contact info
    email: str
    name: Optional[str] = None
    company: Optional[str] = None
    phone: Optional[str] = None
    title: Optional[str] = None

    # Tracking
    source: LeadSource = LeadSource.OTHER
    status: LeadStatus = LeadStatus.NEW
    utm: Optional[UTMData] = None

    # Scoring
    score: int = Field(default=0, ge=0, le=100)

    # Salesforce integration
    salesforce_id: Optional[str] = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    first_contact_at: Optional[datetime] = None

    # Metadata
    tags: list[str] = Field(default_factory=list)
    custom_fields: dict = Field(default_factory=dict)

    class Config:
        json_schema_extra = {
            "example": {
                "id": "lead_abc123",
                "email": "john@acme.com",
                "name": "John Smith",
                "company": "Acme Corp",
                "source": "squarespace",
                "status": "mql",
                "score": 75,
            }
        }
