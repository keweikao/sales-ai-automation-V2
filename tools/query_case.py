#!/usr/bin/env python3
"""Query Firestore case and trigger transcription."""

import json
from google.cloud import firestore

# Initialize Firestore
db = firestore.Client(project='sales-ai-automation-v2')

# Query case
case_id = '202511-IC021'
case_ref = db.collection('cases').document(case_id)
case_doc = case_ref.get()

if not case_doc.exists:
    print(json.dumps({"error": f"Case {case_id} not found"}))
    exit(1)

case_data = case_doc.to_dict()

# Extract relevant info
result = {
    "caseId": case_id,
    "status": case_data.get("status"),
    "createdAt": str(case_data.get("createdAt")),
    "updatedAt": str(case_data.get("updatedAt")),
    "audioFiles": case_data.get("audioFiles", []),
    "transcription": case_data.get("transcription", {}),
}

print(json.dumps(result, indent=2, ensure_ascii=False))
