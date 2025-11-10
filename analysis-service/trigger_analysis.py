#!/usr/bin/env python3
"""
Helper script to trigger analysis task via Cloud Tasks.

This script simulates what the transcription service would do after completing
a transcript - it enqueues an analysis task to the analysis-queue.

Usage:
    python trigger_analysis.py CASE_ID

Example:
    python trigger_analysis.py CASE123
"""

import sys
import json
from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2
import datetime


def create_analysis_task(case_id: str, project_id: str = "sales-ai-automation-v2"):
    """
    Create a Cloud Task to trigger analysis for a case.

    Args:
        case_id: The Firestore case document ID
        project_id: GCP project ID
    """
    # Initialize Cloud Tasks client
    client = tasks_v2.CloudTasksClient()

    # Construct the queue path
    location = "asia-east1"
    queue_name = "analysis-queue"
    queue_path = client.queue_path(project_id, location, queue_name)

    # Construct the task payload
    payload = {
        "caseId": case_id,
    }

    # Construct the analysis service URL
    service_url = f"https://analysis-service-497329205771.asia-east1.run.app/analyze"

    # Create the task
    task = {
        "http_request": {
            "http_method": tasks_v2.HttpMethod.POST,
            "url": service_url,
            "headers": {
                "Content-Type": "application/json",
            },
            "body": json.dumps(payload).encode(),
            "oidc_token": {
                "service_account_email": "497329205771-compute@developer.gserviceaccount.com"
            }
        }
    }

    print(f"Creating task for case: {case_id}")
    print(f"Queue: {queue_path}")
    print(f"URL: {service_url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")

    # Create the task
    response = client.create_task(request={"parent": queue_path, "task": task})

    print(f"\n✅ Task created successfully!")
    print(f"Task name: {response.name}")
    print(f"Task scheduled at: {response.schedule_time}")

    return response


def main():
    if len(sys.argv) != 2:
        print("Usage: python trigger_analysis.py CASE_ID")
        print("Example: python trigger_analysis.py CASE123")
        sys.exit(1)

    case_id = sys.argv[1]

    try:
        response = create_analysis_task(case_id)
        print(f"\n🎉 Analysis task triggered for case: {case_id}")
        print(f"\nYou can check the logs with:")
        print(f"  gcloud logging read 'resource.type=cloud_run_revision AND resource.labels.service_name=analysis-service' --limit 50 --format json")
    except Exception as e:
        print(f"\n❌ Error creating task: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
