#!/bin/bash

# Configuration
AGENT_NAME="whatsapp-agents"
AGENT_VERSION=$(date +%Y%m%d_%H%M%S)
REGION="us-central1"

# Get current project ID
PROJECT_ID=$(gcloud config get-value project)

if [ -z "$PROJECT_ID" ]; then
    echo "❌ Error: No Google Cloud Project ID set."
    echo "Please run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo "🚀 Deploying $AGENT_NAME to Agent Engine..."
echo "Project: $PROJECT_ID"
echo "Region: $REGION"

# Deploy from source (Builds container automatically via Cloud Build)
source .venv/bin/activate
# Capture output to file while showing it to stdout
OUTPUT_FILE=$(mktemp)
adk deploy agent_engine --project=$PROJECT_ID --region=$REGION --display_name="${AGENT_NAME}_${AGENT_VERSION}" agents | tee "$OUTPUT_FILE"

# Extract Reasoning Engine ID
# Looking for pattern: projects/PROJECT_ID/locations/REGION/reasoningEngines/ID
REASONING_ENGINE_RESOURCE=$(grep -o "projects/.*/locations/.*/reasoningEngines/[0-9]*" "$OUTPUT_FILE" | head -n 1)
REASONING_ENGINE_ID=$(basename "$REASONING_ENGINE_RESOURCE")

if [ -n "$REASONING_ENGINE_ID" ]; then
    echo "✅ Detected Reasoning Engine ID: $REASONING_ENGINE_ID"
    echo "💡 Please update your webhook AGENT_ID env var with this value."
else
    echo "⚠️  Could not find Reasoning Engine ID."
fi

rm "$OUTPUT_FILE"

if [ $? -eq 0 ]; then
    echo "✅ Deployment successful!"
    echo "Check your service at the URL provided above."
else
    echo "❌ Deployment failed."
    exit 1
fi
