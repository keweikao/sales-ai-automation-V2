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
gcloud builds submit --config cloudbuild.transcription.yaml .

# 2. Deploy Analysis Service (with Parallelization Optimization)
echo ""
echo "--------------------------------------------------------"
echo "🧠 Deploying Analysis Service..."
echo "   - Applying Orchestrator Optimizations (Parallel Agent 1, 5, 7)"
echo "   - Preserving existing environment variables"
echo "--------------------------------------------------------"
gcloud builds submit --config cloudbuild.analysis.deploy.yaml .

echo ""
echo "========================================================"
echo "✅ Deployment Complete!"
echo "========================================================"
