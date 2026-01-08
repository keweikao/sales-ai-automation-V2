# 01-Lead-Source Module Skill

## Overview
Tracks leads from various sources including Squarespace forms and UTM parameters.

## Status: MVP

## Directory Structure
```
modules/01-lead-source/
├── config.yaml          # Module configuration
├── squarespace/         # Squarespace webhook handling
│   └── webhook.py
├── utm_tracking/        # UTM parameter parsing
│   └── parser.py
├── handlers/            # Event handlers
└── tests/
```

## Key Features

### Squarespace Webhook
Receives form submissions and creates leads:
```python
from modules.01-lead-source.squarespace.webhook import SquarespaceWebhookHandler

handler = SquarespaceWebhookHandler()
lead = await handler.handle_submission(payload)
```

### UTM Tracking
Parses UTM parameters from URLs:
```python
from modules.01-lead-source.utm_tracking.parser import UTMParser

parser = UTMParser()
utm_data = parser.parse_url("https://example.com?utm_source=google")
```

## Configuration
See `config.yaml` for:
- Enabled sources
- Field mappings
- Scoring rules
- Notification settings

## Related Schemas
- `core.schemas.lead.Lead`
- `core.schemas.lead.UTMData`
- `core.schemas.lead.LeadSource`

## Integration Points
- Creates `Lead` records in Firestore
- Triggers `lead.created` events
- Notifies via Slack on new leads

## Development Notes
- Webhook endpoint: POST `/webhooks/squarespace`
- Validate webhook signatures in production
- Check for duplicate leads by email
