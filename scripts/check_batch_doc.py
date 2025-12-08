import os
from google.cloud import firestore

project_id = os.getenv("GCP_PROJECT_ID", "sales-ai-automation-v2")
db = firestore.Client(project=project_id)

batch_id = "fX8GoBdozA0jzN2wM8Jj"
doc_ref = db.collection("transcription_batches").document(batch_id)
doc = doc_ref.get()

if doc.exists:
    print(f"Batch found: {doc.id}")
    print(doc.to_dict())
else:
    print(f"Batch not found: {batch_id}")
