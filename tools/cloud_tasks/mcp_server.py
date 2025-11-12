#!/usr/bin/env python3
"""
Custom MCP Server for Google Cloud Tasks Operations

Provides optimized Cloud Tasks tools to reduce repetitive API calls
and standardize task creation patterns.
"""
import sys
import json
import os
from typing import Any, Dict, Optional
from datetime import datetime

try:
    from google.cloud import tasks_v2
    from google.protobuf import timestamp_pb2
except ImportError:
    tasks_v2 = None


def create_http_task(
    project: str,
    location: str,
    queue: str,
    url: str,
    payload: Dict[str, Any],
    service_account_email: Optional[str] = None,
    schedule_seconds: int = 0,
    task_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create an HTTP POST task in Cloud Tasks queue.

    Args:
        project: GCP project ID
        location: Queue location (e.g., 'asia-east1')
        queue: Queue name (e.g., 'analysis-queue')
        url: Target URL for the task
        payload: JSON payload to send
        service_account_email: Service account for authentication (optional)
        schedule_seconds: Delay before execution in seconds (default: 0)
        task_name: Custom task name (optional, auto-generated if not provided)

    Returns:
        Task creation result with task name and schedule time
    """
    if tasks_v2 is None:
        return {"error": "google-cloud-tasks not installed"}

    try:
        client = tasks_v2.CloudTasksClient()
        queue_path = client.queue_path(project, location, queue)

        # Build task request
        task = {
            "http_request": {
                "http_method": tasks_v2.HttpMethod.POST,
                "url": url,
                "headers": {
                    "Content-Type": "application/json",
                },
                "body": json.dumps(payload).encode(),
            }
        }

        # Add OIDC token if service account provided
        if service_account_email:
            task["http_request"]["oidc_token"] = {
                "service_account_email": service_account_email
            }

        # Add schedule time if specified
        if schedule_seconds > 0:
            import datetime as dt
            schedule_time = dt.datetime.utcnow() + dt.timedelta(seconds=schedule_seconds)
            timestamp = timestamp_pb2.Timestamp()
            timestamp.FromDatetime(schedule_time)
            task["schedule_time"] = timestamp

        # Add custom task name if specified
        if task_name:
            task["name"] = client.task_path(project, location, queue, task_name)

        # Create the task
        response = client.create_task(request={"parent": queue_path, "task": task})

        return {
            "success": True,
            "task_name": response.name,
            "schedule_time": response.schedule_time.ToDatetime().isoformat() if response.schedule_time else None,
            "queue": queue_path,
            "url": url,
            "payload": payload
        }

    except Exception as e:
        return {"error": str(e), "success": False}


def create_transcription_task(
    case_id: str,
    gcs_path: str,
    project: str = "sales-ai-automation-v2",
    location: str = "asia-east1",
    queue: str = "transcription-queue",
    service_url: Optional[str] = None,
    service_account: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a transcription task (common pattern in this project).

    Args:
        case_id: Firestore case document ID
        gcs_path: GCS path to audio file (e.g., 'gs://bucket/path/to/file.mp3')
        project: GCP project ID
        location: Queue location
        queue: Queue name
        service_url: Transcription service URL (auto-detected if not provided)
        service_account: Service account email (auto-detected if not provided)

    Returns:
        Task creation result
    """
    if not service_url:
        service_url = os.environ.get(
            "TRANSCRIPTION_TASK_HANDLER_URL",
            f"https://transcription-service-497329205771.{location}.run.app/transcribe"
        )

    if not service_account:
        service_account = os.environ.get(
            "TRANSCRIPTION_TASK_SERVICE_ACCOUNT",
            "497329205771-compute@developer.gserviceaccount.com"
        )

    payload = {
        "caseId": case_id,
        "gcsPath": gcs_path
    }

    return create_http_task(
        project=project,
        location=location,
        queue=queue,
        url=service_url,
        payload=payload,
        service_account_email=service_account
    )


def create_analysis_task(
    case_id: str,
    project: str = "sales-ai-automation-v2",
    location: str = "asia-east1",
    queue: str = "analysis-queue",
    service_url: Optional[str] = None,
    service_account: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create an analysis task (common pattern in this project).

    Args:
        case_id: Firestore case document ID
        project: GCP project ID
        location: Queue location
        queue: Queue name
        service_url: Analysis service URL (auto-detected if not provided)
        service_account: Service account email (auto-detected if not provided)

    Returns:
        Task creation result
    """
    if not service_url:
        service_url = f"https://analysis-service-497329205771.{location}.run.app/analyze"

    if not service_account:
        service_account = "497329205771-compute@developer.gserviceaccount.com"

    payload = {
        "caseId": case_id
    }

    return create_http_task(
        project=project,
        location=location,
        queue=queue,
        url=service_url,
        payload=payload,
        service_account_email=service_account
    )


def list_tasks(
    project: str,
    location: str,
    queue: str,
    limit: int = 10
) -> Dict[str, Any]:
    """
    List tasks in a Cloud Tasks queue.

    Args:
        project: GCP project ID
        location: Queue location
        queue: Queue name
        limit: Maximum number of tasks to return

    Returns:
        List of tasks with their details
    """
    if tasks_v2 is None:
        return {"error": "google-cloud-tasks not installed"}

    try:
        client = tasks_v2.CloudTasksClient()
        queue_path = client.queue_path(project, location, queue)

        tasks = []
        for i, task in enumerate(client.list_tasks(parent=queue_path)):
            if i >= limit:
                break
            tasks.append({
                "name": task.name,
                "schedule_time": task.schedule_time.ToDatetime().isoformat() if task.schedule_time else None,
                "create_time": task.create_time.ToDatetime().isoformat() if task.create_time else None,
                "dispatch_count": task.dispatch_count,
                "response_count": task.response_count,
            })

        return {
            "success": True,
            "count": len(tasks),
            "tasks": tasks,
            "queue": queue_path
        }

    except Exception as e:
        return {"error": str(e), "success": False}


# MCP Protocol Handler
def handle_request(request: dict) -> dict:
    method = request.get("method")

    if method == "tools/list":
        return {
            "tools": [
                {
                    "name": "cloud_tasks_create_http_task",
                    "description": "Create an HTTP POST task in Cloud Tasks queue with flexible configuration.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "project": {"type": "string", "description": "GCP project ID"},
                            "location": {"type": "string", "description": "Queue location (e.g., 'asia-east1')"},
                            "queue": {"type": "string", "description": "Queue name"},
                            "url": {"type": "string", "description": "Target URL for the task"},
                            "payload": {"type": "object", "description": "JSON payload to send"},
                            "service_account_email": {"type": "string", "description": "Service account for authentication (optional)"},
                            "schedule_seconds": {"type": "integer", "default": 0, "description": "Delay before execution in seconds"},
                            "task_name": {"type": "string", "description": "Custom task name (optional)"}
                        },
                        "required": ["project", "location", "queue", "url", "payload"]
                    }
                },
                {
                    "name": "cloud_tasks_create_transcription_task",
                    "description": "Create a transcription task with project-specific defaults.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "case_id": {"type": "string", "description": "Firestore case document ID"},
                            "gcs_path": {"type": "string", "description": "GCS path to audio file (e.g., 'gs://bucket/path/to/file.mp3')"},
                            "project": {"type": "string", "default": "sales-ai-automation-v2"},
                            "location": {"type": "string", "default": "asia-east1"},
                            "queue": {"type": "string", "default": "transcription-queue"},
                            "service_url": {"type": "string", "description": "Override transcription service URL (optional)"},
                            "service_account": {"type": "string", "description": "Override service account (optional)"}
                        },
                        "required": ["case_id", "gcs_path"]
                    }
                },
                {
                    "name": "cloud_tasks_create_analysis_task",
                    "description": "Create an analysis task with project-specific defaults.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "case_id": {"type": "string", "description": "Firestore case document ID"},
                            "project": {"type": "string", "default": "sales-ai-automation-v2"},
                            "location": {"type": "string", "default": "asia-east1"},
                            "queue": {"type": "string", "default": "analysis-queue"},
                            "service_url": {"type": "string", "description": "Override analysis service URL (optional)"},
                            "service_account": {"type": "string", "description": "Override service account (optional)"}
                        },
                        "required": ["case_id"]
                    }
                },
                {
                    "name": "cloud_tasks_list_tasks",
                    "description": "List tasks in a Cloud Tasks queue.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "project": {"type": "string", "description": "GCP project ID"},
                            "location": {"type": "string", "description": "Queue location"},
                            "queue": {"type": "string", "description": "Queue name"},
                            "limit": {"type": "integer", "default": 10, "description": "Maximum number of tasks to return"}
                        },
                        "required": ["project", "location", "queue"]
                    }
                }
            ]
        }

    elif method == "tools/call":
        tool_name = request["params"]["name"]
        arguments = request["params"]["arguments"]

        if tool_name == "cloud_tasks_create_http_task":
            return create_http_task(**arguments)
        elif tool_name == "cloud_tasks_create_transcription_task":
            return create_transcription_task(**arguments)
        elif tool_name == "cloud_tasks_create_analysis_task":
            return create_analysis_task(**arguments)
        elif tool_name == "cloud_tasks_list_tasks":
            return list_tasks(**arguments)
        else:
            return {"error": f"Unknown tool: {tool_name}"}

    else:
        return {"error": f"Unknown method: {method}"}


if __name__ == "__main__":
    for line in sys.stdin:
        try:
            request = json.loads(line)
            response = handle_request(request)
            print(json.dumps(response, ensure_ascii=False))
            sys.stdout.flush()
        except Exception as e:
            error_response = {"error": str(e)}
            print(json.dumps(error_response, ensure_ascii=False))
            sys.stdout.flush()
