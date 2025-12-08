import os
import requests
from google.cloud import firestore

project_id = os.getenv("GCP_PROJECT_ID", "sales-ai-automation-v2")
db = firestore.Client(project=project_id)

case_id = "202512-IC002"
case_ref = db.collection("cases").document(case_id)

print(f"Requeuing case {case_id}...")
case_ref.update({
    "status": "queued_for_batch",
    "updatedAt": firestore.SERVER_TIMESTAMP
})
print("Case status updated to 'queued_for_batch'.")

# Trigger batch
print("Triggering batch...")
# We need the service URL. Assuming it's the one we know.
service_url = "https://transcription-service-acv3ye2faq-de.a.run.app/trigger-batch"
try:
    response = requests.post(service_url, timeout=10)
    print(f"Trigger response: {response.status_code} {response.text}")
except Exception as e:
    print(f"Failed to trigger batch: {e}")
