# Ops Directory

Operational documentation and runbooks for Sales AI Automation V2.1.

## Contents

### Deployment

See root-level `cloudbuild.*.yaml` files for Cloud Build configurations.

Services:
- `cloudbuild.transcription.yaml` - Transcription service
- `cloudbuild.slack.yaml` - Slack app
- `cloudbuild.analysis.deploy.yaml` - Analysis service
- `cloudbuild.crm-service.yaml` - CRM/Salesforce service
- `cloudbuild.sms-service.yaml` - SMS service
- `cloudbuild.summary-web-service.yaml` - Web service

### Environment Variables

See `.env.example` for required environment variables.

Key variables:
- `SLACK_BOT_TOKEN`, `SLACK_SIGNING_SECRET`, `SLACK_APP_TOKEN`
- `GEMINI_API_KEY`, `GROQ_API_KEY`
- `GCP_PROJECT_ID`
- `SLACK_AUDIO_BUCKET`

### Monitoring

Error notifications are sent to `#sales-ai-alerts` Slack channel.

See `modules/07-ops-automation/monitoring/error_notifier.py` for error handling.

### Runbooks

TODO: Add runbooks for common operations:
- [ ] Reprocessing failed transcriptions
- [ ] Manual analysis trigger
- [ ] Salesforce sync troubleshooting
- [ ] Slack app restart procedure

## Migration Notes

V2.1 architecture is in parallel with V1 during migration.

Use `tools/migration/v1_to_v2_migrator.py` to check migration status:
```bash
python -m tools.migration.v1_to_v2_migrator --check
```
