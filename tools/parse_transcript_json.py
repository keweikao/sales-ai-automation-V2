import json
import os

INPUT_FILE = "temp_transcript_raw.json"
OUTPUT_FILE = "transcript_202512-IC001.txt"

def parse_firestore_value(value):
    """Recursively parse Firestore REST API value format."""
    if "stringValue" in value:
        return value["stringValue"]
    elif "integerValue" in value:
        return int(value["integerValue"])
    elif "doubleValue" in value:
        return float(value["doubleValue"])
    elif "booleanValue" in value:
        return value["booleanValue"]
    elif "mapValue" in value:
        return {k: parse_firestore_value(v) for k, v in value["mapValue"].get("fields", {}).items()}
    elif "arrayValue" in value:
        return [parse_firestore_value(v) for v in value["arrayValue"].get("values", [])]
    return None

def export_transcript():
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Input file {INPUT_FILE} not found.")
        return

    with open(INPUT_FILE, "r") as f:
        raw_data = json.load(f)

    # Check for error
    if "error" in raw_data:
        print(f"❌ API Error: {raw_data['error']}")
        return

    fields = raw_data.get("fields", {})
    
    # Parse transcription field
    transcription_raw = fields.get("transcription", {})
    transcription = parse_firestore_value(transcription_raw)
    
    if not transcription:
        print("❌ No transcription data found.")
        return

    segments = transcription.get("segments", [])
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("Transcript for Case: 202512-IC001\n")
        f.write("="*50 + "\n\n")
        
        if segments:
            for seg in segments:
                start = seg.get("start", 0.0)
                speaker = seg.get("speaker", "Unknown")
                text = seg.get("text", "")
                
                minutes = int(start // 60)
                seconds = int(start % 60)
                time_str = f"{minutes:02d}:{seconds:02d}"
                
                f.write(f"[{time_str}] {speaker}: {text}\n")
            print(f"✅ Exported {len(segments)} segments to {OUTPUT_FILE}")
        else:
            full_text = transcription.get("text", "")
            if full_text:
                f.write(full_text)
                print(f"✅ Exported full text to {OUTPUT_FILE}")
            else:
                print("❌ No text or segments found.")

if __name__ == "__main__":
    export_transcript()
