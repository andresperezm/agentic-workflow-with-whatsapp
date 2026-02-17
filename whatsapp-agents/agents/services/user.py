import logging
import os
import requests

from typing import Optional
from pydantic import BaseModel, Field

from .utils import get_headers


# Setup
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)

# Configuration
USER_SERVICE_URL = os.environ.get("USER_SERVICE_URL")

# Models

class User(BaseModel):
    userEmail: str
    userName: str
    phoneNumber: str
    createdAt: Optional[str] = None # Datetime or string


class GetUserRequest(BaseModel):
    phone_number: str = Field(..., description="Phone number of the user")

# Methods

def get_user(request: GetUserRequest) -> Optional[User]:
    """Fetches user information using their phone number."""
    try:
        if request.phone_number.startswith("+"):
            params = {'phoneNumber': request.phone_number}
        else:
            params = {'phoneNumber': f"+{request.phone_number}"}
        response = requests.get(f'{USER_SERVICE_URL}/users', params=params, headers=get_headers(USER_SERVICE_URL))
        response.raise_for_status()
        return User(**response.json())
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching user: {e}")
        return None
    except ValueError:
        logger.error(f"Error decoding JSON. Status: {response.status_code}, Body: {response.text}")
        return None
