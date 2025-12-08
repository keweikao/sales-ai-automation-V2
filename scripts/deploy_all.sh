#!/bin/bash
set -e

echo "========================================================"
echo "🚀 Starting Deployment for Sales AI Automation V2.0"
echo "========================================================"

# 1. Deploy Transcription Service (with Diarization Fix)
echo ""
echo "--------------------------------------------------------"
echo "📡 Deploying Transcription Service..."
echo "   - Enabling Diarization (ENABLE_DIARIZATION=true)"
echo "   - Linking Hugging Face Token"
echo "--------------------------------------------------------"
gcloud builds submit --config deploy/transcription/cloudbuild.transcription.yaml .

# 2. Deploy Analysis Service (with Parallelization Optimization)
echo ""
echo "--------------------------------------------------------"
echo "🧠 Deploying Analysis Service..."
echo "   - Applying Orchestrator Optimizations (Parallel Agent 1, 5, 7)"
echo "   - Preserving existing environment variables"
echo "--------------------------------------------------------"
# gcloud builds submit --config deploy/analysis/cloudbuild.analysis.deploy.yaml .

# 3. Deploy Slack App
echo ""
echo "--------------------------------------------------------"
echo "💬 Deploying Slack App..."
echo "   - Using deploy/slack/cloudbuild.slack.yaml"
echo "--------------------------------------------------------"
gcloud builds submit --config deploy/slack/cloudbuild.slack.yaml .

# 4. Deploy Web Service
echo ""
echo "--------------------------------------------------------"
echo "🌐 Deploying Web Service..."
echo "   - Using deploy/web/cloudbuild.summary-web-service.yaml"
echo "--------------------------------------------------------"
# gcloud builds submit --config deploy/web/cloudbuild.summary-web-service.yaml .

# 5. Deploy SMS Service
echo ""
echo "--------------------------------------------------------"
echo "📱 Deploying SMS Service..."
echo "   - Using deploy/sms/cloudbuild.sms.yaml"
echo "--------------------------------------------------------"
# gcloud builds submit --config deploy/sms/cloudbuild.sms.yaml .

echo ""
echo "========================================================"
echo "✅ Deployment Complete!"
echo "========================================================"
