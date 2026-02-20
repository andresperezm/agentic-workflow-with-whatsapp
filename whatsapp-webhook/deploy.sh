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

# Configuration
LOG_LEVEL="INFO"
SERVICE_NAME="whatsapp-webhook"
LOCATION="us-central1"
AGENT_LANGUAGE_CODE="en"
ROUTING_TARGET="AGENT_ENGINE" # "DIALOGFLOW" or "AGENT_ENGINE"
AGENT_ID="1872779463893188608" # Replace with your actual Agent ID or Reasoning Engine ID
SEND_WHATSAPP_RESPONSE="TRUE" # "TRUE" or "FALSE"
WHATSAPP_API_VERSION="v24.0"

echo "🚀 Deploying $SERVICE_NAME to Cloud Run..."
echo "Project ID: $PROJECT_ID"
echo "Region: $LOCATION"

# Deploy from source (Builds container automatically via Cloud Build)
gcloud run deploy "$SERVICE_NAME" \
    --source . \
    --region "$LOCATION" \
    --project "$PROJECT_ID" \
    --memory 1024Mi \
    --no-cpu-throttling \
    --allow-unauthenticated \
    --set-env-vars="PROJECT_ID=$PROJECT_ID,LOG_LEVEL=$LOG_LEVEL,ROUTING_TARGET=$ROUTING_TARGET,LOCATION=$LOCATION,AGENT_ID=$AGENT_ID,SEND_WHATSAPP_RESPONSE=$SEND_WHATSAPP_RESPONSE,AGENT_LANGUAGE_CODE=$AGENT_LANGUAGE_CODE,WHATSAPP_API_VERSION=$WHATSAPP_API_VERSION" \
    --set-secrets="WHATSAPP_VERIFY_TOKEN=WHATSAPP_VERIFY_TOKEN:latest,WHATSAPP_API_TOKEN=WHATSAPP_API_TOKEN:latest,WHATSAPP_APP_SECRET=WHATSAPP_APP_SECRET:latest"


if [ $? -eq 0 ]; then
    echo "✅ Deployment successful!"
    echo "Check your service at the URL provided above."
else
    echo "❌ Deployment failed."
    exit 1
fi
