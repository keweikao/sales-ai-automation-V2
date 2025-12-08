#!/bin/bash
# Direct HTTP call to transcription service

CASE_ID="202511-IC021"
GCS_URI="gs://sales-ai-audio-bucket/slack/202511-IC021/202411-122257_桔日員林-Solo_-_鍾志杰.m4a"
SERVICE_URL="https://transcription-service-acv3ye2faq-de.a.run.app/transcribe"

echo "🚀 Triggering transcription via direct HTTP call..."
echo "Case ID: $CASE_ID"
echo "GCS URI: $GCS_URI"
echo ""

# Get ID token for authentication
ID_TOKEN=$(gcloud auth print-identity-token)

# Make HTTP request
curl -X POST "$SERVICE_URL" \
  -H "Authorization: Bearer $ID_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"gcsPath\": \"$GCS_URI\", \"caseId\": \"$CASE_ID\"}" \
  -w "\n\nHTTP Status: %{http_code}\n"

echo ""
echo "✅ Request sent! Monitor logs with:"
echo "  gcloud logging read 'resource.labels.service_name=\"transcription-service\" AND textPayload=~\"Gemini\"' --limit=20"
