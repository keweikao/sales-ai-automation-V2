# 02-MQL-Qualification Module Skill

## Overview
Analyzes first contact calls to qualify Marketing Qualified Leads (MQLs).

## Status: MVP

## Directory Structure
```
modules/02-mql-qualification/
├── config.yaml              # Module configuration
├── first_contact_analyzer/  # Call analysis
├── lead_scoring/            # Scoring logic
├── handlers/                # Event handlers
└── tests/
```

## Key Features

### First Contact Analysis
Analyzes initial sales calls to extract:
- Pain points mentioned
- Budget signals
- Timeline indicators
- Decision maker identification

### Lead Scoring
Scores leads based on conversation signals:
- Budget mentioned: +20 points
- Timeline mentioned: +15 points
- Clear pain point: +25 points
- Decision maker identified: +20 points
- Competitor mentioned: +10 points

Thresholds:
- MQL: 40+ points
- SQL: 70+ points

## Configuration
See `config.yaml` for:
- Minimum call duration
- Scoring criteria and weights
- Notification settings

## Related Schemas
- `core.schemas.lead.Lead`
- `core.schemas.conversation.Conversation`

## Integration Points
- Receives transcripts from Transcription service
- Updates lead scores in Firestore
- Triggers `lead.qualified` events
- Notifies sales managers on MQL qualification

## Development Notes
- Only analyze calls >= 60 seconds
- Use LLM Gateway for analysis
- Consider conversation type when scoring
