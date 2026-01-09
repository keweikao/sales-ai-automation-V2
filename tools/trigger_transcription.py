#!/usr/bin/env python3
"""Create Cloud Task to trigger transcription for a case."""

import json
from google.cloud import tasks_v2

# Configuration
PROJECT_ID = "sales-ai-automation-v2"
LOCATION = "asia-east1"
QUEUE = "transcription-queue"
SERVICE_URL = "https://transcription-service-acv3ye2faq-de.a.run.app/transcribe"
SERVICE_ACCOUNT = "497329205771-compute@developer.gserviceaccount.com"

# Case information
CASE_ID = "202511-IC021"
# You'll need to provide the GCS URI - for now we'll use a placeholder
GCS_URI = "gs://sales-ai-automation-v2-audio/202511-IC021.m4a"  # Update this

# Create task client
client = tasks_v2.CloudTasksClient()
parent = client.queue_path(PROJECT_ID, LOCATION, QUEUE)

# Create task payload
payload = {
    "gcsPath": GCS_URI,
    "caseId": CASE_ID,
}

# Create task
task = {
    "http_request": {
        "http_method": tasks_v2.HttpMethod.POST,
        "url": SERVICE_URL,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(payload).encode(),
        "oidc_token": {
            "service_account_email": SERVICE_ACCOUNT
        }
    }
}

# Submit task
response = client.create_task(request={"parent": parent, "task": task})
print(f"Created task: {response.name}")
print(f"Task will trigger transcription for case: {CASE_ID}")
print(f"GCS URI: {GCS_URI}")
