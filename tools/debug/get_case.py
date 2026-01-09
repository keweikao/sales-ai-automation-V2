from google.cloud import firestore

def get_case_details(case_id):
    db = firestore.Client(project="sales-ai-automation-v2")
    doc_ref = db.collection("cases").document(case_id)
    doc = doc_ref.get()
    
    if doc.exists:
        print(f"Case ID: {case_id}")
        data = doc.to_dict()
        import json
        from datetime import datetime
        def default(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            return str(obj)
        print(json.dumps(data, indent=2, default=default))
        return data
    else:
        print(f"Case {case_id} not found.")
        return None

if __name__ == "__main__":
    import sys
    case_id = sys.argv[1] if len(sys.argv) > 1 else "202601-IC001"
    get_case_details(case_id)
