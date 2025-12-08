#!/bin/bash
ACCESS_TOKEN=$(gcloud auth print-access-token)
PROJECT_ID="sales-ai-automation-v2"
CASE_ID="202511-IC021"

curl -s -H "Authorization: Bearer $ACCESS_TOKEN" \
  "https://firestore.googleapis.com/v1/projects/$PROJECT_ID/databases/(default)/documents/cases/$CASE_ID" > case_details.json

python3 -c "import sys, json; 
try:
    data = json.load(open('case_details.json'))
    fields = data.get('fields', {})
    audio_files = fields.get('audioFiles', {}).get('arrayValue', {}).get('values', [])
    if audio_files:
        # Assuming the first file is the one
        gcs_uri = audio_files[0].get('mapValue', {}).get('fields', {}).get('gcsUri', {}).get('stringValue', '')
        print(f'GCS URI: {gcs_uri}')
    else:
        print('No audio files found')
        
except Exception as e:
    print(f'Error: {e}')
"
