# WhatsApp to Dialogflow CX / Agent Engine Webhook

A Python Flask service designed to run on Google Cloud Run. It bridges WhatsApp Cloud API with either **Dialogflow CX** or **Vertex AI Agent Engine** to provide an automated conversational experience.

## Features
- **WhatsApp Integration**: Ingests text and interactive messages via Webhook.
- **Routing Logic**: Routes messages to either Dialogflow CX or Agent Engine based on configuration.
- **Secure Configuration**: Uses Google Cloud Secret Manager for sensitive configuration.
- **Cloud Run Ready**: Packaged with Docker, ready for serverless deployment.

## Prerequisite: GCP Configuration

This service uses **Google Cloud Secret Manager** to store configuration. You must create the following secrets in your Google Cloud Project.

### 1. Enable APIs
Ensure the following APIs are enabled in your project:
```bash
gcloud services enable secretmanager.googleapis.com run.googleapis.com
```

### 2. Create Configuration Secrets
You need to create two secrets containing YAML configuration.

#### Secret: `whatsapp-webhook-dialogflow-config`
Create a file named `dialogflow.yaml` with your Dialogflow info:
```yaml
project_id: "YOUR_PROJECT_ID"
location: "us-central1"
agent_id: "YOUR_AGENT_ID"
language_code: "en" 
```

Upload it to Secret Manager:
```bash
gcloud secrets create whatsapp-webhook-dialogflow-config --replication-policy="automatic"
gcloud secrets versions add whatsapp-webhook-dialogflow-config --data-file="dialogflow.yaml"
```

#### Secret: `whatsapp-webhook-agent-engine-config`
Create a file named `agent_engine.yaml` with your Agent Engine info:
```yaml
project_id: "YOUR_PROJECT_ID"
location: "us-central1"
reasoning_engine_id: "YOUR_REASONING_ENGINE_ID"
```

Upload it to Secret Manager:
```bash
gcloud secrets create whatsapp-webhook-agent-engine-config --replication-policy="automatic"
gcloud secrets versions add whatsapp-webhook-agent-engine-config --data-file="agent_engine.yaml"
```

### 3. Verification Token & WhatsApp Token
- **WHATSAPP_VERIFY_TOKEN**: This should be stored as a secret named `WHATSAPP_VERIFY_TOKEN`.
```bash
gcloud secrets create WHATSAPP_VERIFY_TOKEN --replication-policy="automatic"
echo -n "YOUR_VERIFY_TOKEN" | gcloud secrets versions add WHATSAPP_VERIFY_TOKEN --data-file=-
```

## Environment Variables

The application uses the following environment variables (mostly for non-sensitive routing defaults):

- `ROUTING_TARGET`: Controls where messages are sent. Options: `AGENT_ENGINE` (default) or `DIALOGFLOW`.
- `LOCATION`: The GCP region (default: `us-central1`).
- `LOG_LEVEL`: Logging level (default: `INFO`).

## How to Run Locally

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   # OR with uv
   uv pip install -r pyproject.toml
   ```

2. Set up local authentication:
   ```bash
   gcloud auth application-default login
   ```

3. Run the application:
   ```bash
   python main.py
   ```

## How to Deploy to Google Cloud Run

The included `deploy.sh` script handles deployment.

```bash
./deploy.sh
```

**Note**: The Cloud Run service account must have permission to access the secrets.
```bash
# Grant Secret Accessor to the Compute Engine default service account (or your specific service account)
PROJECT_NUMBER=$(gcloud projects describe $(gcloud config get-value project) --format="value(projectNumber)")
gcloud projects add-iam-policy-binding $(gcloud config get-value project) \
    --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```
