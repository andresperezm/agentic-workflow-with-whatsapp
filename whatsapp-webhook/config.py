
import os
from dotenv import load_dotenv

# Load local environment variables if present
load_dotenv()

class Config:
    # General
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()
    PORT = int(os.environ.get('PORT', 8080))
    
    # GCP
    PROJECT_ID = os.environ.get('PROJECT_ID')
    LOCATION = os.environ.get('LOCATION', 'us-central1')
    
    # Agent
    AGENT_ID = os.environ.get('AGENT_ID')
    AGENT_LANGUAGE_CODE = os.environ.get('AGENT_LANGUAGE_CODE', 'en')
    ROUTING_TARGET = os.environ.get('ROUTING_TARGET', 'AGENT_ENGINE')

    # WhatsApp
    WHATSAPP_VERIFY_TOKEN = os.environ.get('WHATSAPP_VERIFY_TOKEN')
    WHATSAPP_APP_SECRET = os.environ.get('WHATSAPP_APP_SECRET')
    # Default to True for safety if not specified, but verify logic consumes this
    SEND_WHATSAPP_RESPONSE = os.environ.get('SEND_WHATSAPP_RESPONSE', 'TRUE').upper() == 'TRUE'
    WHATSAPP_API_VERSION = os.environ.get('WHATSAPP_API_VERSION', 'v24.0')
    WHATSAPP_API_TOKEN = os.environ.get('WHATSAPP_API_TOKEN')

    @classmethod
    def validate(cls):
        """Validates critical configuration."""
        if not cls.PROJECT_ID:
            raise ValueError("PROJECT_ID environment variable not set.")
        if not cls.AGENT_ID:
            # Maybe not critical if using Dialogflow exclusively, but good to warn
            pass 
