#!/bin/bash

# Configuration
SERVICE_NAME="purchase-orders-service"
REGION="us-central1"

# Get current project ID
PROJECT_ID=$(gcloud config get-value project)

if [ -z "$PROJECT_ID" ]; then
    echo "❌ Error: No Google Cloud Project ID set."
    echo "Please run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo "🚀 Deploying $SERVICE_NAME to Cloud Run..."
echo "Project: $PROJECT_ID"
echo "Region: $REGION"

# Deploy from source (Builds container automatically via Cloud Build)
gcloud run deploy "$SERVICE_NAME" \
    --source . \
    --region "$REGION" \
    --project "$PROJECT_ID" \
    --allow-unauthenticated \
    --set-env-vars="GCP_PROJECT=$PROJECT_ID"

if [ $? -eq 0 ]; then
    echo "✅ Deployment successful!"
    echo "Check your service at the URL provided above."
else
    echo "❌ Deployment failed."
    exit 1
fi
