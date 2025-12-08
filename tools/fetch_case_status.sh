#!/bin/bash
ACCESS_TOKEN=$(gcloud auth print-access-token)
PROJECT_ID="sales-ai-automation-v2"
CASE_ID="202512-IC001"

curl -s -H "Authorization: Bearer $ACCESS_TOKEN" \
  "https://firestore.googleapis.com/v1/projects/$PROJECT_ID/databases/(default)/documents/cases/$CASE_ID" > case_details_new.json

python3 -c "import sys, json; 
try:
    data = json.load(open('case_details_new.json'))
    if 'error' in data:
        print(f'Error: {data[\"error\"][\"message\"]}')
        sys.exit(0)

    fields = data.get('fields', {})
    status = fields.get('status', {}).get('stringValue', 'unknown')
    print(f'Status: {status}')
    print(f'Created At: {data.get(\"createTime\")}')
    
    # Check transcription
    transcription = fields.get('transcription', {}).get('mapValue', {}).get('fields', {})
    if transcription:
        print('Transcription: Present')
    else:
        print('Transcription: Missing')
        
    # Check analysis
    analysis = fields.get('analysis', {}).get('mapValue', {}).get('fields', {})
    if analysis:
        print('Analysis: Present')
    else:
        print('Analysis: Missing')

except Exception as e:
    print(f'Error parsing: {e}')
"
