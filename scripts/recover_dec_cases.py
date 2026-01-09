import os
import logging
from google.cloud import firestore

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Firestore
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "sales-ai-automation-v2-85d6460d778e.json"
db = firestore.Client(project='sales-ai-automation-v2')

# Target cases
target_cases = [
    '202512-IC044',
    '202512-IC063',
    '202512-IC064',
    '202512-IC065',
    '202512-IC066',
    '202512-IC067',
    '202512-IC068',
    '202512-IC069',
    '202512-IC070',
    '202512-IC071',
    '202512-IC072',
    '202512-IC073',
    '202512-IC074',
    '202512-IC075',
    '202512-IC076',
    '202512-IC077',
    '202512-IC078',
    '202512-IC079'
]

def reset_cases():
    batch = db.batch()
    count = 0

    print(f"Resetting {len(target_cases)} cases to 'queued_for_batch'...")
    
    for case_id in target_cases:
        doc_ref = db.collection('cases').document(case_id)
        # Check if exists first just to be safe? 
        # Actually batch set/update is fine.
        batch.update(doc_ref, {
            'status': 'queued_for_batch',
            'error': firestore.DELETE_FIELD, # Clear previous errors
            'updatedAt': firestore.SERVER_TIMESTAMP
        })
        count += 1
    
    batch.commit()
    print(f"Successfully reset {count} cases.")

if __name__ == "__main__":
    reset_cases()
