#!/usr/bin/env python3
"""Check transcription status for cases created since yesterday."""

import json
import datetime
from google.cloud import firestore

# Initialize Firestore
db = firestore.Client(project='sales-ai-automation-v2')

# Calculate yesterday's date (midnight) - use UTC timezone
from datetime import timezone
yesterday = datetime.datetime.now(timezone.utc) - datetime.timedelta(days=1)
yesterday_midnight = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)

print(f"Checking cases created since: {yesterday_midnight.isoformat()}")
print("=" * 80)

# Query all cases
cases_ref = db.collection('cases')
cases = cases_ref.stream()

recent_cases = []
for case in cases:
    data = case.to_dict()
    case_id = case.id
    created_at = data.get('createdAt')
    
    # Check if case was created recently
    if created_at:
        if isinstance(created_at, datetime.datetime):
            if created_at >= yesterday_midnight:
                recent_cases.append({
                    'case_id': case_id,
                    'created_at': created_at,
                    'status': data.get('status'),
                    'transcription_status': data.get('transcriptionStatus'),
                    'has_transcription': bool(data.get('transcription', {}).get('text')),
                    'transcription_length': len(data.get('transcription', {}).get('text', '')),
                    'segments_count': len(data.get('transcription', {}).get('segments', [])),
                    'gcs_uri': data.get('gcsUri'),
                    'error': data.get('error'),
                })

# Sort by created_at
recent_cases.sort(key=lambda x: x['created_at'], reverse=True)

if not recent_cases:
    print("No cases found created since yesterday.")
else:
    print(f"Found {len(recent_cases)} case(s) created since yesterday:\n")
    
    for case in recent_cases:
        print(f"Case ID: {case['case_id']}")
        print(f"  Created: {case['created_at'].isoformat()}")
        print(f"  Status: {case['status']}")
        print(f"  Transcription Status: {case['transcription_status']}")
        print(f"  Has Transcription: {case['has_transcription']}")
        if case['has_transcription']:
            print(f"  Transcription Length: {case['transcription_length']} chars")
            print(f"  Segments Count: {case['segments_count']}")
        if case['gcs_uri']:
            print(f"  GCS URI: {case['gcs_uri']}")
        if case['error']:
            print(f"  ERROR: {case['error']}")
        print("-" * 40)

print("\n" + "=" * 80)
print("Summary:")
print(f"  Total cases: {len(recent_cases)}")
completed = sum(1 for c in recent_cases if c['has_transcription'])
print(f"  With transcription: {completed}")
print(f"  Missing transcription: {len(recent_cases) - completed}")
