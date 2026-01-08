# 06-Analytics Module Skill

## Overview
Performance analytics and reporting for sales team.

## Status: PARTIAL (Weekly Reports Implemented)

## Directory Structure
```
modules/06-analytics/
├── config.yaml
├── rep_performance/     # Future: per-rep dashboards
└── weekly_reports/      # MVP: weekly summary reports
    ├── __init__.py
    └── generator.py
```

## Implemented Features

### Weekly Reports
Generates weekly performance summaries:
```python
from modules.06-analytics.weekly_reports.generator import WeeklyReportGenerator

generator = WeeklyReportGenerator()
report = await generator.generate()
slack_message = generator.format_slack_message(report)
```

Report includes:
- Total conversations and analyzed count
- Average MEDDIC score
- Per-rep breakdown
- Top insights
- Coaching highlights

Schedule: Monday 9 AM (Asia/Taipei)

## Planned Features

### Rep Performance Dashboards
- Conversation count trends
- MEDDIC score progression
- Coaching adoption rate
- Follow-up completion rate

### Trend Analysis
- Week-over-week comparisons
- Team performance trends
- Coaching effectiveness metrics

## Configuration
See `config.yaml` for:
- Report schedule
- Included sections
- Delivery channels

## Integration Points
- Reads from ConversationRepository
- Sends via Notification service
- Scheduled via Scheduler service

## Development Notes
- Weekly reports run via Cloud Scheduler
- Consider BigQuery for historical analytics
- Cache aggregations for performance
