#!/bin/bash

# Configuration
# Get current project ID
PROJECT_ID=$(gcloud config get-value project)

if [ -z "$PROJECT_ID" ]; then
    echo "❌ Error: No Google Cloud Project ID set."
    echo "Please run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

# Configuration
SERVICE_NAME="dialogflow-cx-to-agent-engine-forwarder"
LOCATION=${LOCATION:-"us-central1"}
LOG_LEVEL=${LOG_LEVEL:-"INFO"}
DEBUG=${DEBUG:-"FALSE"}
MAX_RETRIES=${MAX_RETRIES:-"1"}
AGENT_ID=${AGENT_ID:-"855528898060877824"} 

if [ -z "$AGENT_ID" ]; then
    echo "⚠️ Warning: AGENT_ID not set. Please set AGENT_ID environment variable or pass it to this script."
    # We don't exit here because maybe the user wants to set it later via Console, but it's good to warn.
fi

echo "🚀 Deploying $SERVICE_NAME to Cloud Run..."
echo "Project ID: $PROJECT_ID"
echo "Region: $LOCATION"

# Deploy from source (Builds container automatically via Cloud Build)
# Note: Removed secrets that are not used by this service (WHATSAPP_*)
gcloud run deploy "$SERVICE_NAME" \
    --source . \
    --region "$LOCATION" \
    --project "$PROJECT_ID" \
    --memory 1024Mi \
    --no-cpu-throttling \
    --allow-unauthenticated \
    --set-env-vars="PROJECT_ID=$PROJECT_ID,LOCATION=$LOCATION,AGENT_ID=$AGENT_ID,LOG_LEVEL=$LOG_LEVEL,DEBUG=$DEBUG,MAX_RETRIES=$MAX_RETRIES"

if [ $? -eq 0 ]; then
    echo "✅ Deployment successful!"
    echo "Check your service at the URL provided above."
else
    echo "❌ Deployment failed."
    exit 1
fi
