
import os
from google.cloud import firestore

project_id = os.environ.get("GCP_PROJECT_ID", "sales-ai-automation-v2")
db = firestore.Client(project=project_id)


case_id = "202512-IC002"
doc_ref = db.collection("cases").document(case_id)
doc = doc_ref.get()

if doc.exists:
    print(f"Case {case_id} exists.")
    data = doc.to_dict()
    print(f"Status: {data.get('status')}")
    print(f"GCS URI: {data.get('gcsUri')}")
    print(f"Batch ID: {data.get('batchId')}")
    print(f"Operation Name: {data.get('operationName')}")
else:
    print(f"Case {case_id} does not exist.")
