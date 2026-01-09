import firebase_admin
from firebase_admin import firestore
import os

# Initialize Firestore (assuming default credentials work in this environment)
if not firebase_admin._apps:
    firebase_admin.initialize_app()

db = firestore.client()

CASE_ID = "202512-IC001"
OUTPUT_FILE = f"transcript_{CASE_ID}.txt"

def export_transcript():
    print(f"Fetching transcript for case: {CASE_ID}...")
    
    doc_ref = db.collection("cases").document(CASE_ID)
    doc = doc_ref.get()
    
    if not doc.exists:
        print(f"❌ Case {CASE_ID} not found.")
        return

    data = doc.to_dict()
    transcription = data.get("transcription", {})
    segments = transcription.get("segments", [])
    
    if not segments:
        print("⚠️ No segments found in transcription data.")
        # Fallback to full text if segments are missing
        full_text = transcription.get("text", "")
        if full_text:
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                f.write(full_text)
            print(f"✅ Exported full text to {OUTPUT_FILE}")
        else:
            print("❌ No text found.")
        return

    print(f"Found {len(segments)} segments. Writing to file...")
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(f"Transcript for Case: {CASE_ID}\n")
        f.write("="*50 + "\n\n")
        
        for seg in segments:
            start = seg.get("start", 0.0)
            speaker = seg.get("speaker", "Unknown")
            text = seg.get("text", "")
            
            # Format time as MM:SS
            minutes = int(start // 60)
            seconds = int(start % 60)
            time_str = f"{minutes:02d}:{seconds:02d}"
            
            f.write(f"[{time_str}] {speaker}: {text}\n")
            
    print(f"✅ Transcript exported successfully to: {os.path.abspath(OUTPUT_FILE)}")

if __name__ == "__main__":
    export_transcript()
