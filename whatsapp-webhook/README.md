# WhatsApp to Dialogflow CX Webhook

A Node.js service designed to run on Google Cloud Run. It bridges WhatsApp Cloud API and Dialogflow CX to provide an automated conversational experience.

## Features
- WhatsApp text message ingestion via Webhook.
- Integration to Dialogflow CX `DetectIntent` API.
- Replies back out to WhatsApp Graph API using the Dialogflow CX response text.
- Packaged as a Docker container, ready for Cloud Run.

## Environment Variables
The application requires the following environment variables to function correctly:

- `PORT`: (Optional) Port to run on. Defaults to 8080.
- `WEBHOOK_VERIFY_TOKEN`: A custom token used by WhatsApp to verify the webhook URL.
- `WHATSAPP_TOKEN`: A permanent or temporary access token from Meta App Dashboard to send messages back.
- `DIALOGFLOW_PROJECT_ID`: Your Google Cloud Project ID.
- `DIALOGFLOW_LOCATION`: Location of your CX Agent (e.g., `global`, `us-central1`).
- `DIALOGFLOW_AGENT_ID`: The ID of your Dialogflow CX Agent.

## How to Run Locally

1. Install dependencies:
   ```bash
   npm install
   ```

2. Create a `.env` file in the root directory and define the variables mentioned above.

3. Start the server
  ```bash
  npm start
  ```

## How to Deploy to Google Cloud Run

1. Build and push the Docker image to Google Container Registry or Artifact Registry:
   ```bash
   gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/whatsapp-webhook
   ```

2. Deploy the container to Cloud Run:
   ```bash
   gcloud run deploy whatsapp-webhook \
     --image gcr.io/YOUR_PROJECT_ID/whatsapp-webhook \
     --platform managed \
     --region YOUR_REGION \
     --allow-unauthenticated \
     --set-env-vars WEBHOOK_VERIFY_TOKEN=...,WHATSAPP_TOKEN=...,DIALOGFLOW_PROJECT_ID=...,DIALOGFLOW_LOCATION=...,DIALOGFLOW_AGENT_ID=...
   ```

## WhatsApp Webhook Configuration
In the Meta App Dashboard, set your Webhook URL to the Cloud Run service URL appended with `/webhook` (e.g. `https://whatsapp-webhook-abc123def-uc.a.run.app/webhook`). Use the `WEBHOOK_VERIFY_TOKEN` you configured. Subscribe to the `messages` event.
