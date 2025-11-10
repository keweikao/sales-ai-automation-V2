# Transcription → Analysis Integration Guide

## Overview

After transcription completes, the transcription service should trigger the analysis service via Cloud Tasks.

## Architecture

```
Transcription Service
    ↓ (transcription complete)
Write to Firestore (cases/{caseId})
    ↓
Create Cloud Task (analysis-queue)
    ↓
Analysis Service receives task
    ↓
Execute Agent 1-5 analysis
    ↓
Write results to Firestore
    ↓
Trigger Slack notification (Phase 5)
```

## Implementation for Transcription Service

### Step 1: Add Cloud Tasks Client

Add to transcription service's `requirements.txt`:

```
google-cloud-tasks>=2.14.0
```

### Step 2: Import and Initialize

```python
from google.cloud import tasks_v2
import json

# Initialize at module level
tasks_client = tasks_v2.CloudTasksClient()
PROJECT_ID = "sales-ai-automation-v2"
LOCATION = "asia-east1"
QUEUE_NAME = "analysis-queue"
```

### Step 3: Create Task After Transcription

Add this function to transcription service:

```python
def trigger_analysis(case_id: str) -> bool:
    """
    Trigger analysis for a completed transcription.

    Args:
        case_id: Firestore case document ID

    Returns:
        True if task created successfully, False otherwise
    """
    try:
        # Construct queue path
        queue_path = tasks_client.queue_path(
            PROJECT_ID,
            LOCATION,
            QUEUE_NAME
        )

        # Construct task payload
        payload = {
            "caseId": case_id,
        }

        # Analysis service URL
        service_url = (
            "https://analysis-service-497329205771.asia-east1.run.app/analyze"
        )

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
                    "service_account_email": (
                        "497329205771-compute@developer.gserviceaccount.com"
                    )
                }
            }
        }

        # Submit task
        response = tasks_client.create_task(
            request={"parent": queue_path, "task": task}
        )

        logger.info(
            f"Analysis task created for case {case_id}: {response.name}"
        )
        return True

    except Exception as e:
        logger.error(
            f"Failed to create analysis task for case {case_id}: {e}",
            exc_info=True
        )
        return False
```

### Step 4: Call After Transcription Complete

In your transcription completion handler:

```python
# After saving transcript to Firestore
case_ref.update({
    'transcription': transcription_data,
    'status': 'transcribed',
    'updatedAt': firestore.SERVER_TIMESTAMP,
})

# Trigger analysis
success = trigger_analysis(case_id)
if not success:
    logger.error(f"Failed to trigger analysis for case {case_id}")
    # Don't fail the transcription, just log the error
    # Cloud Tasks will be retried if the failure is transient
```

## Testing

### Manual Testing

Use the provided test script:

```bash
# Trigger analysis for a specific case
python analysis-service/trigger_analysis.py CASE123
```

### Check Task Status

```bash
# List tasks in queue
gcloud tasks list --queue=analysis-queue --location=asia-east1

# Check Cloud Run logs
gcloud logging read \
  'resource.type=cloud_run_revision AND resource.labels.service_name=analysis-service' \
  --limit 50 \
  --format json
```

### Verify in Firestore

Check that the case document has:

- `analysis.status`: 'completed', 'partial_success', or 'failed'
- `analysis.agents[agent1-5].data`: Analysis results
- `analysis.totalDuration`: Execution time
- `status`: Updated to match analysis status

## Error Handling

### Retry Configuration

The `analysis-queue` is configured with:

- **Max attempts**: 3
- **Min backoff**: 60s
- **Max backoff**: 240s
- **Backoff multiplier**: 2x (60s → 120s → 240s)

### Retryable Errors (500 status)

Analysis service returns 500 for:

- Insufficient data (< 3/5 agents succeeded)
- Firestore read/write failures
- Unexpected exceptions

Cloud Tasks will automatically retry these.

### Non-retryable Errors (404, 400 status)

Analysis service returns:

- **404**: Case not found in Firestore
- **400**: Invalid request payload

Cloud Tasks will NOT retry these.

### Success Cases (200 status)

- **Full success**: 5/5 agents succeeded
- **Partial success**: 3-4/5 agents succeeded

Both return 200 and are considered successful.

## IAM Permissions Checklist

✅ Service account has:

- `roles/cloudtasks.enqueuer` - Create tasks
- `roles/run.invoker` - Invoke analysis-service
- `roles/datastore.user` - Read/write Firestore

✅ Cloud Tasks queue:

- Name: `analysis-queue`
- Location: `asia-east1`
- State: RUNNING

✅ Analysis service:

- Accepts authenticated requests from service account
- `/analyze` endpoint is accessible

## Monitoring

### Key Metrics to Monitor

1. **Task creation rate**: Should match transcription completion rate
2. **Task failure rate**: Should be < 5%
3. **Analysis duration**: Should be 30-60 seconds for Agent 1-5
4. **Partial success rate**: Track how often < 5 agents succeed

### Alerts to Set Up

- Alert when task failure rate > 10% in last hour
- Alert when queue depth > 50 (backlog building up)
- Alert when average analysis duration > 120 seconds

## Next Steps

After this integration is complete:

1. Phase 4: Integrate Agent 6-7 for synthesis
2. Phase 5: Add Slack notification on completion
3. Phase 6: End-to-end testing with real audio files
