#!/bin/bash
ACCESS_TOKEN=$(gcloud auth print-access-token)
PROJECT_ID="sales-ai-automation-v2"
CASE_ID="202511-IC021"

curl -s -H "Authorization: Bearer $ACCESS_TOKEN" \
  "https://firestore.googleapis.com/v1/projects/$PROJECT_ID/databases/(default)/documents/cases/$CASE_ID" > transcript_raw.json

# Parse with python to handle Firestore JSON format
python3 -c "import sys, json; 
try:
    data = json.load(open('transcript_raw.json'))
    # Navigate the Firestore JSON structure
    fields = data.get('fields', {})
    transcription = fields.get('transcription', {}).get('mapValue', {}).get('fields', {})
    text = transcription.get('text', {}).get('stringValue', 'No text found')
    print(text)
except Exception as e:
    print(f'Error parsing JSON: {e}')
"
