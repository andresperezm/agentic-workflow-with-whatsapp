import logging
from flask import Flask, request, jsonify
import re
from pydantic import BaseModel
import vertexai
from vertexai import agent_engines
from concurrent.futures import ThreadPoolExecutor

from config import Config
import time


# Configure logging
logging.basicConfig(level=Config.LOG_LEVEL)
logger = logging.getLogger(__name__)

app = Flask(__name__)

class DialogflowCXRequest(BaseModel):
    session_id: str
    user_utterance: str
    agent_id: str
    project_id: str
    location_id: str
    user_phone: str

# Verify critical config
try:
    Config.validate()
except ValueError as e:
    logger.error(f"Configuration Error: {e}")
    exit(1)

executor = ThreadPoolExecutor(max_workers=10)
logger.info(f"Using Project ID: {Config.PROJECT_ID} and Region: {Config.LOCATION}")

def parse_dialogflow_cx_payload(payload: dict) -> DialogflowCXRequest:
    """
    Parses a dictionary payload into a DialogflowCXRequest Pydantic model.
    """
    return DialogflowCXRequest(**payload)

def mask_phone_number(phone_number: str) -> str:
    """Masks a phone number, showing only the last 4 digits."""
    if not phone_number or len(phone_number) < 4:
        return "****"
    return f"*****{phone_number[-4:]}"

def get_vertex_agent():
    if not Config.AGENT_ID:
        logger.error("AGENT_ID environment variable not set")
        raise ValueError("AGENT_ID not set")

    agent_engine_resource_name = f"projects/{Config.PROJECT_ID}/locations/{Config.LOCATION}/reasoningEngines/{Config.AGENT_ID}"
    
    logger.info(f"Initializing Vertex AI Agent Engine: {agent_engine_resource_name}")
    try:
        # Always create a fresh client to ensure it binds to the current (background) asyncio loop
        vertex_client = vertexai.Client(project=Config.PROJECT_ID, location=Config.LOCATION)
        return vertex_client.agent_engines.get(name=agent_engine_resource_name)
    except Exception as e:
        logger.error(f"Failed to get agent {agent_engine_resource_name}: {e}")
        raise e


def forward_to_adk_agent_engine(dialogflow_cx_request: DialogflowCXRequest) -> None:
    """
    Forwards a Dialogflow CX request to the ADK Agent Engine.
    """
    max_retries = Config.MAX_RETRIES

    for attempt in range(max_retries + 1):
        try:
            session_id = ""
            user_phone_number = dialogflow_cx_request.user_phone
            query = dialogflow_cx_request.user_utterance
            agent = get_vertex_agent()
            masked_phone = mask_phone_number(user_phone_number)

            # 1. List existing sessions SYNCHRONOUSLY
            logger.debug(f"[{masked_phone}] Listing sessions (Attempt {attempt+1})...")
            # Using SYNC method
            sessions_resp = agent.list_sessions(user_id=user_phone_number)
            sessions = sessions_resp.get('sessions', [])
            
            # ... (Session optimization logic)
            if sessions:
                 # Use the first session found
                session_id = sessions[0].get('id')
                logger.info(f"[{masked_phone}] Reusing session: {session_id}")
                
                # Delete duplicate sessions if any
                if len(sessions) > 1:
                    logger.info(f"[{masked_phone}] Found {len(sessions)} sessions. Cleaning up duplicates...")
                    for i in range(1, len(sessions)):
                        old_session = sessions[i]
                        old_id = old_session.get('id')
                        try:
                            # Using SYNC method
                            agent.delete_session(user_id=user_phone_number, session_id=old_id)
                            logger.debug(f"[{masked_phone}] Deleted old session: {old_id}")
                        except Exception as del_err:
                            logger.warning(f"[{masked_phone}] Failed to delete session {old_id}: {del_err}")
            else:
                logger.info(f"[{masked_phone}] No existing session found. A new one will be created automatically.")

            full_response_text = ""
            
            # 3. Stream query SYNCHRONOUSLY
            # Pass both user_id and the resolved session_id. Returns an iterator.
            response_iterator = agent.stream_query(message=query, user_id=user_phone_number, session_id=session_id)
            
            for response in response_iterator:
                try:
                    # Check for the structure provided in the sample
                    if 'content' in response and 'parts' in response['content']:
                        parts = response['content']['parts']
                        for part in parts:
                            if 'text' in part:
                                text_chunk = part['text']
                                full_response_text += text_chunk
                                # Optional: Accumulate and send chunks if desired, but buffering full response is safer logic-wise
                    else:
                        # Fallback simple text access if different structure
                        logger.debug(f"[{masked_phone}] Raw response chunk: {response}")
                        
                except Exception as parse_err:
                    logger.warning(f"[{masked_phone}] Error parsing chunk: {parse_err}")

            if full_response_text:
                logger.debug(f"[{masked_phone}] Agent Engine response: {full_response_text}")
            else:
                logger.warning(f"[{masked_phone}] No text in response")
            
            # If we reached here, success
            return

        except Exception as e:
            logger.error(f"[{mask_phone_number(user_phone_number)}] Agent Engine Error (Attempt {attempt+1}): {e}", exc_info=True)
            if attempt < max_retries:
                logger.warning(f"[{mask_phone_number(user_phone_number)}] Retrying after error...")
                time.sleep(1) # Brief pause (sync sleep)
            else:
                logger.error(f"[{mask_phone_number(user_phone_number)}] All retries failed.")


@app.route('/message', methods=['POST'])
def forward_message():
    try:
        payload = request.get_json()
        logger.info(f"Received payload: {payload}")
        if not payload:
             logger.error("Payload is None or empty")
             return jsonify({"error": "Empty payload"}), 400
        
        dialogflow_cx_request = parse_dialogflow_cx_payload(payload)

        executor.submit(forward_to_adk_agent_engine, dialogflow_cx_request)
        return jsonify({"status": "success"}), 200
    except Exception as e:
        logger.error(f"Error processing request: {e}", exc_info=True)
        # Return detailed error for debugging
        return jsonify({"error": str(e), "details": "Check logs for payload"}), 400



if __name__ == '__main__':
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)

