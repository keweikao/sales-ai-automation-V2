import os
import sys
from google.cloud import firestore

project_id = os.environ.get("GCP_PROJECT_ID", "sales-ai-automation-v2")
db = firestore.Client(project=project_id)

doc = db.collection("cases").document("202512-IC029").get()
if doc.exists:
    data = doc.to_dict()
    print("UploadedBy:", data.get("uploadedBy"))
    print("SalesRep:", data.get("salesRep"))
else:
    print("Case not found")
