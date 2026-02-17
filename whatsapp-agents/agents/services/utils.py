import google.auth.transport.requests
from google.oauth2 import id_token
from google.cloud import secretmanager
import logging
import os
from typing import Dict

# Setup
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)

def get_headers(audience: str) -> Dict[str, str]:
    headers = {}
    try:
        auth_req = google.auth.transport.requests.Request()
        token = id_token.fetch_id_token(auth_req, audience)
        headers["Authorization"] = f"Bearer {token}"
    except Exception as e:
        logger.error(f"Error fetching ID token: {e}")
    return headers


def get_secret(secret_id: str) -> str:
    client = secretmanager.SecretManagerServiceClient()
    _, project_id = google.auth.default()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8").strip()
