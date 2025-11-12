# Customer Summary Web Service

Cloud Run friendly Flask app that renders Agent 7 customer summaries as public web pages.

## Features

- Fetches case + summary data from Firestore
- Converts Markdown into branded HTML (Jinja + custom CSS)
- Logs view counts (`delivery.viewCount`) and timestamps
- Provides `/summary/<caseId>` for full pages and `/s/<code>` short-link redirects
- `/health` endpoint for Cloud Run probes

## Local Development

```bash
export GOOGLE_APPLICATION_CREDENTIALS=$HOME/.config/gcloud/application_default_credentials.json
export GCP_PROJECT_ID=sales-ai-automation-v2
pip install -r web-service/requirements.txt
python web-service/src/main.py  # via Flask dev server
```

Or run with Gunicorn:

```bash
cd web-service
gunicorn -b :8080 src.main:app
```

Access `http://localhost:8080/summary/<caseId>` or redirect via `http://localhost:8080/s/<code>`.

## Deployment

Deploy via Cloud Build:

```bash
gcloud builds submit --config cloudbuild.summary-web-service.yaml .
```

This builds/pushes `summary-web-service` to Artifact Registry and deploys Cloud Run (asia-east1) using service account `497329205771-compute@developer.gserviceaccount.com`. After deployment, copy the public URL (e.g. `https://summary-web-service-xxxx.a.run.app`) and update the Slack app build (`cloudbuild.slack.yaml`) substitutions for `SUMMARY_BASE_URL` / `SHORT_URL_BASE`.
