#!/usr/bin/env python3
"""Check case status in Firestore"""
import os
os.environ["GOOGLE_CLOUD_PROJECT"] = "sales-ai-automation-v2"

from google.cloud import firestore

db = firestore.Client()

case_id = "202510-121832"
case_ref = db.collection("cases").document(case_id)
case_doc = case_ref.get()

if case_doc.exists:
    data = case_doc.to_dict()
    print(f"Case {case_id} found:")
    print(f"  Status: {data.get('status')}")
    print(f"  GCS Path: {data.get('audio', {}).get('gcsPath', 'Not set')}")
    print(f"  Error: {data.get('error', 'None')}")
    print(f"  Customer: {data.get('customer', {}).get('name')}")
    print(f"  Sales Rep: {data.get('salesRep', {}).get('name')}")
    print(f"\nFull document:")
    for key, value in sorted(data.items()):
        print(f"  {key}: {value}")
else:
    print(f"Case {case_id} NOT FOUND in Firestore")

# Also check processed_files
file_id = "F09S7PAHBR6"
processed_ref = db.collection("processed_files").document(file_id)
processed_doc = processed_ref.get()

print(f"\n{'='*60}")
if processed_doc.exists:
    data = processed_doc.to_dict()
    print(f"Processed file {file_id} found:")
    print(f"  Case ID: {data.get('caseId')}")
    print(f"  Status: {data.get('status')}")
    print(f"  GCS Path: {data.get('gcsPath', 'Not set')}")
    print(f"  Error: {data.get('error', 'None')}")
else:
    print(f"Processed file {file_id} NOT FOUND in Firestore")
