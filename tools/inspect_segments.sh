#!/bin/bash
ACCESS_TOKEN=$(gcloud auth print-access-token)
PROJECT_ID="sales-ai-automation-v2"
CASE_ID="202511-IC021"

curl -s -H "Authorization: Bearer $ACCESS_TOKEN" \
  "https://firestore.googleapis.com/v1/projects/$PROJECT_ID/databases/(default)/documents/cases/$CASE_ID" > transcript_raw.json

python3 -c "import sys, json; 
try:
    data = json.load(open('transcript_raw.json'))
    fields = data.get('fields', {})
    transcription = fields.get('transcription', {}).get('mapValue', {}).get('fields', {})
    
    # Check segments
    segments = transcription.get('segments', {}).get('arrayValue', {}).get('values', [])
    print(f'Segment count: {len(segments)}')
    if segments:
        first_seg = segments[0].get('mapValue', {}).get('fields', {})
        text = first_seg.get('text', {}).get('stringValue', '')
        print(f'First segment: {text}')
        
except Exception as e:
    print(f'Error: {e}')
"
