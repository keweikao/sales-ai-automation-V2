# 03-Sales-Conversation Module Skill

## Overview
Core sales conversation analysis module - the heart of the system.
Migrated from V1 with MEDDIC analysis, coaching, and Slack integration.

## Status: MVP (V1 Migration)

## Directory Structure
```
modules/03-sales-conversation/
├── config.yaml              # Module configuration
├── transcript_analyzer/     # Analysis orchestration
├── meddic/                  # MEDDIC framework
│   ├── agents/              # Analysis agents
│   │   └── prompts/         # Agent prompts
├── coaching/                # Sales coaching
├── slack_bot/               # Slack integration
│   ├── handlers/
│   ├── interactions/
│   └── utils/
├── handlers/
└── tests/
```

## V1 Migration Mapping

| V1 Location | V2.1 Location |
|-------------|---------------|
| `analysis-service/src/agents/` | `meddic/agents/` |
| `analysis-service/src/orchestrator.py` | `transcript_analyzer/` |
| `src/slack_app/` | `slack_bot/` |

## Key Features

### MEDDIC Analysis
Multi-agent system evaluating:
- **M**etrics: Quantifiable success measures
- **E**conomic Buyer: Budget authority
- **D**ecision Criteria: Evaluation standards
- **D**ecision Process: Decision-making steps
- **I**dentify Pain: Business problems
- **C**hampion: Internal advocate

### Analysis Agents
- `ContextAgent`: Meeting background analysis
- `BuyerAgent`: Customer insight extraction
- `SellerAgent`: Sales performance evaluation
- `SummaryAgent`: Summary generation
- `CoachAgent`: Coaching recommendations
- `CRMAgent`: CRM data extraction

### Slack Bot Features
- File upload handling
- Interactive analysis notifications
- Summary editing workflow
- Send to customer functionality

## Configuration
See `config.yaml` for:
- MEDDIC dimension weights
- Qualification thresholds
- Agent settings
- Slack bot configuration

## Related Schemas
- `core.schemas.conversation.Conversation`
- `core.schemas.conversation.Transcript`
- `core.schemas.analysis_result.AnalysisResult`
- `core.schemas.analysis_result.MEDDICScore`
- `core.schemas.analysis_result.CoachingInsight`

## Integration Points
- Receives transcripts from Transcription service
- Uses LLM Gateway for analysis
- Sends notifications via Notification service
- Syncs with Salesforce via Integration service

## Development Notes
- Agents run in parallel where possible
- Results are aggregated by orchestrator
- Slack interactions use Block Kit
- Token usage is tracked per conversation

## Prompts
Agent prompts are in `meddic/agents/prompts/`.
When modifying prompts:
1. Test with sample transcripts
2. Verify structured output parsing
3. Check token usage impact
