#!/bin/bash

SERVICE_URL="https://transcription-service-497329205771.asia-east1.run.app/transcribe"
CASE_ID="202512-IC001"
GCS_URI="gs://sales-ai-audio-bucket/slack/202512-IC001/202411-122257_桔日員林-Solo_-_鍾志杰.m4a"

echo "Getting ID Token..."
TOKEN=$(gcloud auth print-identity-token)

echo "Triggering Direct Transcription for $CASE_ID..."
curl -s -X POST "$SERVICE_URL" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "gcs_uri": "gs://sales-ai-audio-bucket/slack/202512-IC001/202411-122257_桔日員林-Solo_-_鍾志杰.m4a"
  }' > trigger_output_retry.txt
echo -e "\nDone."
