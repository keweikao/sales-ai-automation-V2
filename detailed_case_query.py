#!/usr/bin/env python3
"""
Detailed query for case 202511-IC011
"""

import json
from google.cloud import firestore
from datetime import datetime

def detailed_case_query(case_id: str):
    """Get all available data for a case"""
    try:
        db = firestore.Client()
        
        # Query the specific case
        case_ref = db.collection("cases").document(case_id)
        case_doc = case_ref.get()
        
        if not case_doc.exists:
            print(f"Case {case_id} not found")
            return
        
        case_data = case_doc.to_dict()
        
        print(f"\n{'='*80}")
        print(f"COMPLETE CASE DOCUMENT: {case_id}")
        print(f"{'='*80}\n")
        
        # Print all top-level keys
        print("Top-level keys:")
        for key in sorted(case_data.keys()):
            value = case_data.get(key)
            if isinstance(value, dict):
                print(f"  {key}: <dict with {len(value)} keys>")
            elif isinstance(value, list):
                print(f"  {key}: <list with {len(value)} items>")
            elif isinstance(value, str) and len(str(value)) > 100:
                print(f"  {key}: {str(value)[:100]}...")
            else:
                print(f"  {key}: {value}")
        
        # Deep dive into analysis section
        if "analysis" in case_data:
            print(f"\n{'='*80}")
            print("ANALYSIS SECTION (detailed)")
            print(f"{'='*80}\n")
            
            analysis = case_data.get("analysis", {})
            
            for section_key, section_value in sorted(analysis.items()):
                print(f"\n[{section_key}]")
                
                if isinstance(section_value, dict):
                    for k, v in sorted(section_value.items()):
                        if isinstance(v, (list, dict)):
                            print(f"  {k}: <{type(v).__name__} with {len(v)} items>")
                        elif isinstance(v, str) and len(str(v)) > 100:
                            print(f"  {k}: {str(v)[:100]}...")
                        else:
                            print(f"  {k}: {v}")
                elif isinstance(section_value, list):
                    print(f"  <list with {len(section_value)} items>")
                    if len(section_value) > 0 and isinstance(section_value[0], dict):
                        print(f"  Sample item keys: {list(section_value[0].keys())}")
                elif isinstance(section_value, str) and len(str(section_value)) > 100:
                    print(f"  {str(section_value)[:200]}...")
                else:
                    print(f"  {section_value}")
        
        # Check processed_files if audio_file_id exists
        if "audio_file_id" in case_data:
            file_id = case_data.get("audio_file_id")
            print(f"\n{'='*80}")
            print(f"PROCESSED FILE DOCUMENT: {file_id}")
            print(f"{'='*80}\n")
            
            file_ref = db.collection("processed_files").document(file_id)
            file_doc = file_ref.get()
            
            if file_doc.exists:
                file_data = file_doc.to_dict()
                
                print("Top-level keys in processed_files:")
                for key in sorted(file_data.keys()):
                    value = file_data.get(key)
                    if isinstance(value, dict):
                        print(f"  {key}: <dict with {len(value)} keys>")
                    elif isinstance(value, list):
                        print(f"  {key}: <list with {len(value)} items>")
                    elif isinstance(value, str) and len(str(value)) > 100:
                        print(f"  {key}: {str(value)[:100]}...")
                    else:
                        print(f"  {key}: {value}")
            else:
                print("processed_files document not found")
        
        # Check if there are any recent logs or error messages
        print(f"\n{'='*80}")
        print("DIAGNOSTIC INFORMATION")
        print(f"{'='*80}\n")
        
        print(f"Case document size: {len(json.dumps(case_data, default=str))} bytes")
        print(f"Last modified: {case_data.get('updatedAt', 'Not available')}")
        
        # Look for any error-related fields
        error_fields = [k for k in case_data.keys() if 'error' in k.lower()]
        if error_fields:
            print(f"\nError-related fields found:")
            for field in error_fields:
                print(f"  {field}: {case_data.get(field)}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    detailed_case_query("202511-IC011")
