import os
from dotenv import load_dotenv

# Load local environment variables if present
load_dotenv()

class Config:
    # General
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()
    PORT = int(os.environ.get('PORT', 8080))
    HOST = os.environ.get('HOST', '0.0.0.0')
    DEBUG = os.environ.get('DEBUG', 'FALSE').upper() == 'TRUE'
    MAX_RETRIES = int(os.environ.get('MAX_RETRIES', 1))

    
    # GCP
    PROJECT_ID = os.environ.get('PROJECT_ID')
    LOCATION = os.environ.get('LOCATION', 'us-central1')
    
    # Agent
    AGENT_ID = os.environ.get('AGENT_ID')

    @classmethod
    def validate(cls):
        """Validates critical configuration."""
        if not cls.PROJECT_ID:
            raise ValueError("PROJECT_ID environment variable not set.")
        if not cls.AGENT_ID:
            raise ValueError("AGENT_ID environment variable not set.")
