#!/bin/bash

# Configuration
PROJECT_ID="sales-ai-automation-v2"
LOCATION="asia-east1"
SERVICE_NAME="transcription-service"
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --platform managed --region $LOCATION --format 'value(status.url)')
SERVICE_ACCOUNT="497329205771-compute@developer.gserviceaccount.com"

echo "Service URL: $SERVICE_URL"

# 1. Trigger Batch Job (Every 4 hours)
JOB_NAME="trigger-stt-batch"
echo "Creating/Updating Scheduler Job: $JOB_NAME..."

gcloud scheduler jobs create http $JOB_NAME \
    --schedule="0 */4 * * *" \
    --uri="$SERVICE_URL/trigger-batch" \
    --http-method=POST \
    --oidc-service-account-email=$SERVICE_ACCOUNT \
    --location=$LOCATION \
    --project=$PROJECT_ID \
    --quiet || \
gcloud scheduler jobs update http $JOB_NAME \
    --schedule="0 */4 * * *" \
    --uri="$SERVICE_URL/trigger-batch" \
    --http-method=POST \
    --oidc-service-account-email=$SERVICE_ACCOUNT \
    --location=$LOCATION \
    --project=$PROJECT_ID \
    --quiet

# 2. Check Results Job (Every 30 minutes)
JOB_NAME="check-stt-results"
echo "Creating/Updating Scheduler Job: $JOB_NAME..."

gcloud scheduler jobs create http $JOB_NAME \
    --schedule="*/30 * * * *" \
    --uri="$SERVICE_URL/check-results" \
    --http-method=POST \
    --oidc-service-account-email=$SERVICE_ACCOUNT \
    --location=$LOCATION \
    --project=$PROJECT_ID \
    --quiet || \
gcloud scheduler jobs update http $JOB_NAME \
    --schedule="*/30 * * * *" \
    --uri="$SERVICE_URL/check-results" \
    --http-method=POST \
    --oidc-service-account-email=$SERVICE_ACCOUNT \
    --location=$LOCATION \
    --project=$PROJECT_ID \
    --quiet

echo "Scheduler jobs setup complete."
