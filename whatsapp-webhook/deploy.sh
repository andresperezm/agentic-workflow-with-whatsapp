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
LOG_LEVEL="DEBUG"
SERVICE_NAME="whatsapp-webhook"
MAIN_REGION="us-central1"
ROUTING_TARGET="AGENT_ENGINE" # "DIALOGFLOW" or "AGENT_ENGINE"

# Dialogflow Configuration
DIALOGFLOW_PROJECT_ID="${PROJECT_ID}"
DIALOGFLOW_LOCATION="${MAIN_REGION}"
DIALOGFLOW_AGENT_ID="2f8a6728-39a3-4669-bccc-d58431714db4"

# Agent Engine Configuration
# Agent Engine Resource Name requires Project Number
AGENT_ENGINE_PROJECT_ID="${PROJECT_ID}"
AGENT_ENGINE_LOCATION="${MAIN_REGION}"
AGENT_ENGINE_REASONING_ENGINE_ID="8565058141421568000"

AGENT_ENGINE_PROJECT_NUMBER=$(gcloud projects describe "$AGENT_ENGINE_PROJECT_ID" --format="value(projectNumber)")

echo "🚀 Deploying $SERVICE_NAME to Cloud Run..."
echo "Project ID: $PROJECT_ID"
echo "Region: $MAIN_REGION"

# Deploy from source (Builds container automatically via Cloud Build)
gcloud run deploy "$SERVICE_NAME" \
    --source . \
    --region "$MAIN_REGION" \
    --project "$PROJECT_ID" \
    --memory 1024Mi \
    --allow-unauthenticated \
    --set-env-vars="LOG_LEVEL=$LOG_LEVEL,ROUTING_TARGET=$ROUTING_TARGET,DIALOGFLOW_PROJECT_ID=$DIALOGFLOW_PROJECT_ID,DIALOGFLOW_LOCATION=$DIALOGFLOW_LOCATION,DIALOGFLOW_AGENT_ID=$DIALOGFLOW_AGENT_ID,AGENT_ENGINE_PROJECT_NUMBER=$AGENT_ENGINE_PROJECT_NUMBER,AGENT_ENGINE_LOCATION=$AGENT_ENGINE_LOCATION,AGENT_ENGINE_REASONING_ENGINE_ID=$AGENT_ENGINE_REASONING_ENGINE_ID" \
    --set-secrets="WEBHOOK_VERIFY_TOKEN=WEBHOOK_VERIFY_TOKEN:latest"

if [ $? -eq 0 ]; then
    echo "✅ Deployment successful!"
    echo "Check your service at the URL provided above."
else
    echo "❌ Deployment failed."
    exit 1
fi
