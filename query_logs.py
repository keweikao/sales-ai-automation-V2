#!/usr/bin/env python3
"""
Query GCP Cloud Logging for transcription errors
"""

from google.cloud import logging as cloud_logging
from datetime import datetime, timedelta
import json

def query_transcription_logs():
    """Query Cloud Logging for transcription service errors"""
    try:
        # Initialize Cloud Logging client
        logging_client = cloud_logging.Client()
        
        # Query for recent errors in transcription service
        # Looking for the case ID and error patterns
        
        query_filter = """
        resource.type="cloud_run_revision"
        AND (
            resource.labels.service_name="transcription-service"
            OR resource.labels.service_name="analysis-service"
        )
        AND (
            jsonPayload.case_id="202511-IC011"
            OR textPayload=~"202511-IC011"
            OR textPayload=~"NoneType.*callable"
        )
        AND severity >= "ERROR"
        """
        
        print(f"\n{'='*80}")
        print("GCP Cloud Logging Query")
        print(f"{'='*80}\n")
        
        print(f"Query filter: {query_filter}\n")
        
        # Get last 24 hours of logs
        entries = logging_client.list_entries(
            filter_=query_filter,
            order_by=cloud_logging.DESCENDING,
            page_size=50
        )
        
        entries_list = list(entries)
        
        if not entries_list:
            print("No error logs found for case 202511-IC011")
        else:
            print(f"Found {len(entries_list)} log entries\n")
            
            for i, entry in enumerate(entries_list, 1):
                print(f"\n[Entry {i}]")
                print(f"Timestamp: {entry.timestamp}")
                print(f"Severity: {entry.severity}")
                print(f"Resource: {entry.resource.labels}")
                
                if entry.payload:
                    if isinstance(entry.payload, dict):
                        print(f"Payload: {json.dumps(entry.payload, indent=2, default=str)}")
                    else:
                        print(f"Payload: {entry.payload}")
    
    except Exception as e:
        print(f"Error querying logs: {e}")
        import traceback
        traceback.print_exc()

def query_recent_transcription_logs():
    """Query for any recent transcription service logs"""
    try:
        logging_client = cloud_logging.Client()
        
        # Simpler query for recent transcription activity
        query_filter = """
        resource.type="cloud_run_revision"
        AND (
            resource.labels.service_name="transcription-service"
            OR resource.labels.service_name like "transcription"
        )
        AND timestamp >= "2025-11-13T02:00:00Z"
        """
        
        print(f"\n{'='*80}")
        print("Recent Transcription Service Logs (Last 24 hours)")
        print(f"{'='*80}\n")
        
        entries = logging_client.list_entries(
            filter_=query_filter,
            order_by=cloud_logging.DESCENDING,
            page_size=20
        )
        
        entries_list = list(entries)
        
        print(f"Found {len(entries_list)} recent log entries\n")
        
        for i, entry in enumerate(entries_list[:10], 1):
            print(f"\n[Entry {i}]")
            print(f"Timestamp: {entry.timestamp}")
            print(f"Severity: {entry.severity}")
            
            if entry.payload:
                payload_str = str(entry.payload)[:200]
                print(f"Message: {payload_str}")
    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("Attempting to query Cloud Logging...\n")
    query_transcription_logs()
    print("\n" + "="*80 + "\n")
    query_recent_transcription_logs()
