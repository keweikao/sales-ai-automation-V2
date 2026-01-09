import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import datetime

# Initialize Firestore
if not firebase_admin._apps:
    cred = credentials.ApplicationDefault()
    firebase_admin.initialize_app(cred, {
        'projectId': 'sales-ai-automation-v2',
    })

db = firestore.client()

CASE_ID = "202512-IC001"

def serialize(obj):
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    return str(obj)

doc_ref = db.collection("cases").document(CASE_ID)
doc = doc_ref.get()

if doc.exists:
    data = doc.to_dict()
    print(f"Case ID: {CASE_ID}")
    print(f"Status: {data.get('status')}")
    print(f"Transcription Status: {data.get('transcriptionStatus', 'N/A')}")
    
    transcription = data.get("transcription", {})
    if transcription:
        text = transcription.get("text", "")
        print(f"Transcription Length: {len(text)}")
        print(f"Snippet: {text[:200]}...")
        print(f"Segments Count: {len(transcription.get('segments', []))}")
    else:
        print("No transcription data found.")
else:
    print(f"Case {CASE_ID} not found!")
