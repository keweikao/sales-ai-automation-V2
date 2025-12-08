#!/bin/bash

# Configuration
SERVICE_URL="https://analysis-service-acv3ye2faq-de.a.run.app"
CASE_ID="202511-IC021"

echo "🚀 Triggering analysis via direct HTTP call..."
echo "Case ID: $CASE_ID"
echo "Service URL: $SERVICE_URL"

# Get ID Token
echo "🔑 Fetching ID Token..."
TOKEN=$(gcloud auth print-identity-token)

# Make Request
echo "📡 Sending POST request..."
curl -X POST "$SERVICE_URL/analyze" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"caseId\": \"$CASE_ID\"
  }" \
  -v

echo ""
echo "✅ Request sent! Monitor logs with:"
echo "  gcloud logging read 'resource.labels.service_name=\"analysis-service\"' --limit=20"
