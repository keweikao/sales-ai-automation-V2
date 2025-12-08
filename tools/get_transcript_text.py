import firebase_admin
from firebase_admin import firestore
import sys

# Initialize Firestore
if not firebase_admin._apps:
    firebase_admin.initialize_app()
db = firestore.client()

case_id = '202511-IC021'
if len(sys.argv) > 1:
    case_id = sys.argv[1]

doc = db.collection('cases').document(case_id).get()
if doc.exists:
    text = doc.to_dict().get('transcription', {}).get('text', '')
    print(text)
else:
    print("Case not found")
