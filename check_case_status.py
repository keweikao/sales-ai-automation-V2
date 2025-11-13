#!/usr/bin/env python3
"""
Query case 202511-IC011 transcription status from Firestore
"""

import json
import sys
from typing import Optional, Dict, Any
from google.cloud import firestore
from datetime import datetime

def check_case_transcription_status(case_id: str) -> Dict[str, Any]:
    """
    Check transcription status for a specific case from Firestore.
    
    Args:
        case_id: The case ID to check (e.g., "202511-IC011")
    
    Returns:
        Dictionary with case information and transcription status
    """
    try:
        # Initialize Firestore client
        db = firestore.Client()
        
        # Query the specific case
        case_ref = db.collection("cases").document(case_id)
        case_doc = case_ref.get()
        
        if not case_doc.exists:
            return {
                "status": "NOT_FOUND",
                "case_id": case_id,
                "message": f"Case {case_id} not found in Firestore"
            }
        
        case_data = case_doc.to_dict()
        
        # Extract transcription-related information
        analysis = case_data.get("analysis", {})
        transcription = analysis.get("transcription", {})
        
        result = {
            "case_id": case_id,
            "found": True,
            "case_data": {
                "customer_name": case_data.get("customer_name"),
                "rep_name": case_data.get("rep_name"),
                "created_date": str(case_data.get("created_date")),
                "status": case_data.get("status"),
            },
            "transcription": {
                "step": transcription.get("step"),
                "progress": transcription.get("progress"),
                "error": transcription.get("error"),
                "updated_at": str(transcription.get("updatedAt")),
                "total_chunks": transcription.get("totalChunks"),
                "completed_chunks": transcription.get("completedChunks"),
            }
        }
        
        # Add detail (first 500 chars of transcript if completed)
        if transcription.get("detail"):
            detail_str = str(transcription.get("detail"))
            result["transcription"]["detail_preview"] = detail_str[:500]
            result["transcription"]["detail_length"] = len(detail_str)
        
        # Check for diarization
        if "diarization_segments" in analysis:
            diarization = analysis.get("diarization_segments", [])
            result["diarization"] = {
                "segments_count": len(diarization) if isinstance(diarization, list) else 0,
                "has_diarization": len(diarization) > 0 if isinstance(diarization, list) else False
            }
        
        # Check for speakers
        if "speakers" in analysis:
            speakers = analysis.get("speakers", [])
            result["speakers"] = {
                "count": len(speakers) if isinstance(speakers, list) else 0,
                "speakers": speakers if isinstance(speakers, list) else []
            }
        
        # Check for processed_files related to this case
        if case_data.get("audio_file_id"):
            file_id = case_data.get("audio_file_id")
            file_ref = db.collection("processed_files").document(file_id)
            file_doc = file_ref.get()
            
            if file_doc.exists:
                file_data = file_doc.to_dict()
                result["processed_file"] = {
                    "file_id": file_id,
                    "transcription_step": file_data.get("transcriptionStep"),
                    "transcription_progress": file_data.get("transcriptionProgress"),
                    "transcription_completed_chunks": file_data.get("transcriptionCompletedChunks"),
                    "transcription_total_chunks": file_data.get("transcriptionTotalChunks"),
                    "error": file_data.get("error")
                }
        
        return result
        
    except Exception as e:
        return {
            "status": "ERROR",
            "case_id": case_id,
            "error": str(e),
            "error_type": type(e).__name__
        }

def main():
    case_id = "202511-IC011"
    
    print(f"\n{'='*80}")
    print(f"Checking Transcription Status for Case: {case_id}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"{'='*80}\n")
    
    result = check_case_transcription_status(case_id)
    
    # Pretty print the result
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # Additional summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    
    if result.get("found"):
        transcription = result.get("transcription", {})
        step = transcription.get("step")
        progress = transcription.get("progress")
        error = transcription.get("error")
        
        print(f"Case Found: YES")
        print(f"Transcription Step: {step}")
        print(f"Progress: {progress if progress is not None else 'N/A'}")
        
        if error:
            print(f"Error: {error}")
        
        if step == "completed":
            detail_length = result.get("transcription", {}).get("detail_length", 0)
            diarization_count = result.get("diarization", {}).get("segments_count", 0)
            speakers_count = result.get("speakers", {}).get("count", 0)
            
            print(f"\nTranscription Details:")
            print(f"  - Transcript length: {detail_length} characters")
            print(f"  - Diarization segments: {diarization_count}")
            print(f"  - Speakers detected: {speakers_count}")
            
            if speakers_count > 0:
                speakers = result.get("speakers", {}).get("speakers", [])
                print(f"  - Speaker list: {speakers}")
        elif step == "in_progress":
            print(f"\nProgress Details:")
            print(f"  - Chunks completed: {transcription.get('completed_chunks', 'N/A')}")
            print(f"  - Total chunks: {transcription.get('total_chunks', 'N/A')}")
        
        print(f"Last updated: {transcription.get('updated_at')}")
    else:
        print(f"Case Found: NO")
        print(f"Status: {result.get('status')}")
        if "message" in result:
            print(f"Message: {result.get('message')}")
    
    print(f"{'='*80}\n")

if __name__ == "__main__":
    main()
