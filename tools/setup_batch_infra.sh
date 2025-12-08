#!/bin/bash
set -e

PROJECT_ID="sales-ai-automation-v2"
REGION="asia-east1"
REQUESTS_BUCKET="sales-ai-batch-requests"
RESULTS_BUCKET="sales-ai-batch-results"
TOPIC_NAME="batch-job-complete"
SUBSCRIPTION_NAME="batch-job-complete-sub"
SERVICE_URL="https://transcription-service-497329205771.asia-east1.run.app/webhook/batch_complete"
SERVICE_ACCOUNT="cloud-run-invoker@${PROJECT_ID}.iam.gserviceaccount.com" # Assuming a service account for invoking

echo "Setting up Batch API Infrastructure for Project: $PROJECT_ID"

# 1. Create Buckets
echo "Creating GCS Buckets..."
if ! gsutil ls -b gs://$REQUESTS_BUCKET > /dev/null 2>&1; then
    gsutil mb -l $REGION gs://$REQUESTS_BUCKET
    echo "Created $REQUESTS_BUCKET"
else
    echo "$REQUESTS_BUCKET already exists"
fi

if ! gsutil ls -b gs://$RESULTS_BUCKET > /dev/null 2>&1; then
    gsutil mb -l $REGION gs://$RESULTS_BUCKET
    echo "Created $RESULTS_BUCKET"
else
    echo "$RESULTS_BUCKET already exists"
fi

# 2. Create Pub/Sub Topic
echo "Creating Pub/Sub Topic..."
if ! gcloud pubsub topics describe $TOPIC_NAME --project=$PROJECT_ID > /dev/null 2>&1; then
    gcloud pubsub topics create $TOPIC_NAME --project=$PROJECT_ID
    echo "Created topic $TOPIC_NAME"
else
    echo "Topic $TOPIC_NAME already exists"
fi

# 3. Configure GCS Notification
echo "Configuring GCS Notification..."
# Check if notification already exists (simplified check)
if ! gsutil notification list gs://$RESULTS_BUCKET | grep -q $TOPIC_NAME; then
    gsutil notification create -t $TOPIC_NAME -f json -e OBJECT_FINALIZE gs://$RESULTS_BUCKET
    echo "Created notification for $RESULTS_BUCKET -> $TOPIC_NAME"
else
    echo "Notification already exists"
fi

# 4. Create Pub/Sub Subscription (Push to Cloud Run)
echo "Creating Pub/Sub Subscription..."
# Note: This requires the SERVICE_URL to be known. Since we are redeploying, the URL might change if we deploy a new service, 
# but we are updating the existing service, so URL should be stable.
# We need a service account with run.invoker role.
# For simplicity in this script, we might skip auth or use a specific SA.
# Let's try creating without auth first (if service allows unauthenticated) or use the default compute SA.

if ! gcloud pubsub subscriptions describe $SUBSCRIPTION_NAME --project=$PROJECT_ID > /dev/null 2>&1; then
    gcloud pubsub subscriptions create $SUBSCRIPTION_NAME \
        --topic=$TOPIC_NAME \
        --push-endpoint=$SERVICE_URL \
        --project=$PROJECT_ID \
        --ack-deadline=600
    echo "Created subscription $SUBSCRIPTION_NAME -> $SERVICE_URL"
else
    echo "Subscription $SUBSCRIPTION_NAME already exists. Updating endpoint..."
    gcloud pubsub subscriptions update $SUBSCRIPTION_NAME \
        --push-endpoint=$SERVICE_URL
fi

echo "Infrastructure Setup Complete!"
