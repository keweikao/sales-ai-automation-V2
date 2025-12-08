#!/bin/bash

# Service URL (derived from project/region pattern)
SERVICE_URL="https://analysis-service-acv3ye2faq-de.a.run.app/analyze"
CASE_ID="202512-IC001"

echo "🚀 Triggering Analysis for Case: $CASE_ID"
echo "Target URL: $SERVICE_URL"

# Get ID Token
ID_TOKEN=$(gcloud auth print-identity-token)

# Send Request
curl -X POST "$SERVICE_URL" \
  -H "Authorization: Bearer $ID_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"caseId\": \"$CASE_ID\"}"

echo -e "\n✅ Request sent!"
