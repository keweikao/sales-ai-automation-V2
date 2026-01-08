# Core Module Skill

## Overview
The core module provides shared functionality used across all other modules in Sales AI Automation V2.1.

## Directory Structure
```
core/
├── config/          # Application settings
├── schemas/         # Pydantic data models
├── database/        # Firestore repositories
├── interfaces/      # Abstract interfaces
└── llm/             # LLM client wrapper
```

## Key Components

### Config (`core/config/`)
- `settings.py`: Environment-based configuration using pydantic-settings
- `environments/`: YAML configs for base, dev, prod

Usage:
```python
from core.config import get_settings
settings = get_settings()
print(settings.gcp_project_id)
```

### Schemas (`core/schemas/`)
Pydantic models defining data contracts:
- `lead.py`: Lead, LeadSource, LeadStatus, UTMData
- `conversation.py`: Conversation, Transcript, Speaker
- `analysis_result.py`: AnalysisResult, MEDDICScore, CoachingInsight
- `events.py`: Event, EventType

### Database (`core/database/`)
Repository pattern for Firestore:
- `ConversationRepository`: CRUD for sales_cases collection
- `LeadRepository`: CRUD for leads collection

### Interfaces (`core/interfaces/`)
- `JourneyLogger`: Abstract interface for event logging

### LLM (`core/llm/`)
- `LLMClient`: Unified client for Gemini API

## When Working on Core

1. **Adding new schemas**: Add to `core/schemas/` and export in `__init__.py`
2. **Adding repositories**: Follow the pattern in existing repositories
3. **Changing config**: Update both `settings.py` and environment YAML files

## Dependencies
- pydantic >= 2.0
- pydantic-settings
- google-cloud-firestore
- google-generativeai
