import os
import uvicorn
import logging

from dotenv import load_dotenv
from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app

logging.basicConfig(format="%(levelname)-8s: %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get the directory where main.py is located
AGENT_DIR = os.path.dirname(os.path.abspath(__file__))

instance_connection_name = os.environ.get("DB_INSTANCE_CONNECTION_NAME")
db_name = os.environ.get("DB_NAME")
db_user = os.environ.get("DB_USER")
db_pass = os.environ.get("DB_PASS")

SESSION_SERVICE_URI = "sqlite:///./my_agent_data.db"
if "K_SERVICE" in os.environ:
    if all([db_user, db_pass, db_name, instance_connection_name]):
        SESSION_SERVICE_URI = (
            f"postgresql+psycopg2://{db_user}:{db_pass}@/{db_name}"
            f"?host=/cloudsql/{instance_connection_name}"
        )

# Example allowed origins for CORS
ALLOWED_ORIGINS = ["http://localhost", "http://localhost:8080", "*"]
# Set web=True if you intend to serve a web interface, False otherwise

def get_env_boolean(env_var_name, default_value=False):
    """
    Retrieves a boolean value from an environment variable.

    Args:
        env_var_name (str): The name of the environment variable.
        default_value (bool): The default boolean value to return if the
                              environment variable is not set or its value
                              cannot be interpreted as a boolean.

    Returns:
        bool: The boolean value from the environment variable, or the
              default_value if not found or invalid.
    """
    env_value = os.getenv(env_var_name)
    if env_value is None:
        return default_value
   
    if env_value.lower() in ('true', '1', 'yes', 't', 'y'):
        return True
    elif env_value.lower() in ('false', '0', 'no', 'f', 'n'):
        return False
    else:
        return default_value


SERVE_WEB_INTERFACE=get_env_boolean("SERVE_WEB_INTERFACE", True)
# Call the function to get the FastAPI app instance
# Ensure the agent directory name ('capital_agent') matches your agent folder
app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    session_service_uri=SESSION_SERVICE_URI,
    allow_origins=ALLOWED_ORIGINS,
    web=SERVE_WEB_INTERFACE,
)


@app.get("/health_check")
async def health_check():
    return {"status": "OK"}


if __name__ == "__main__":
    # Use the PORT environment variable provided by Cloud Run, defaulting to 8080
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
