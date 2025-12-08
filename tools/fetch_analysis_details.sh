#!/bin/bash
ACCESS_TOKEN=$(gcloud auth print-access-token)
PROJECT_ID="sales-ai-automation-v2"
CASE_ID="202512-IC001"

curl -s -H "Authorization: Bearer $ACCESS_TOKEN" \
  "https://firestore.googleapis.com/v1/projects/$PROJECT_ID/databases/(default)/documents/cases/$CASE_ID" > case_details_full.json

python3 -c "import sys, json; 
try:
    data = json.load(open('case_details_full.json'))
    fields = data.get('fields', {})
    analysis = fields.get('analysis', {}).get('mapValue', {}).get('fields', {})
    
    if not analysis:
        print('No analysis data found')
        sys.exit(0)
        
    status = analysis.get('status', {}).get('stringValue', 'unknown')
    print(f'Analysis Status: {status}')
    
    agents = analysis.get('agents', {}).get('mapValue', {}).get('fields', {})
    print('Agent Results:')
    for agent_id, result in agents.items():
        res_map = result.get('mapValue', {}).get('fields', {})
        a_status = res_map.get('status', {}).get('stringValue', 'unknown')
        error = res_map.get('error', {}).get('stringValue', '')
        print(f'  {agent_id}: {a_status} {error}')

except Exception as e:
    print(f'Error parsing: {e}')
"
