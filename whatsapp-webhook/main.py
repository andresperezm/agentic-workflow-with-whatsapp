import logging
import hmac
import hashlib
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, request, jsonify, abort
from google.cloud.dialogflowcx_v3.services.sessions.client import SessionsClient
from google.cloud.dialogflowcx_v3.types.session import DetectIntentRequest, TextInput, QueryInput, QueryParameters
import vertexai
from vertexai import agent_engines
from google.protobuf import struct_pb2
import requests

from whatsapp_models import parse_webhook_payload
from config import Config

# Configure logging
logging.basicConfig(level=Config.LOG_LEVEL)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Verify critical config
try:
    Config.validate()
except ValueError as e:
    logger.error(f"Configuration Error: {e}")
    exit(1)

logger.info(f"Using Project ID: {Config.PROJECT_ID} and Region: {Config.LOCATION}")

# Global clients (Lazy loading)
_dialogflow_session_client = None

# ThreadPool for handling webhook tasks
# Adjust max_workers based on expected load and CPU/Memory limits.
# For Cloud Run with 1 vCPU, a small number like 5-10 is often sufficient for IO-bound tasks.
executor = ThreadPoolExecutor(max_workers=10)

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

def get_dialogflow_session_client():
    global _dialogflow_session_client
    if _dialogflow_session_client:
        return _dialogflow_session_client

    if not Config.AGENT_ID:
        logger.error("AGENT_ID environment variable not set (required for Dialogflow Agent ID)")
        raise ValueError("AGENT_ID not set")

    logger.info("Initializing Dialogflow CX Session Client")
    api_endpoint = f"{Config.LOCATION}-dialogflow.googleapis.com"
    _dialogflow_session_client = SessionsClient(client_options={"api_endpoint": api_endpoint})
    return _dialogflow_session_client


def mask_phone_number(phone_number: str) -> str:
    """Masks a phone number, showing only the last 4 digits."""
    if not phone_number or len(phone_number) < 4:
        return "****"
    return f"*****{phone_number[-4:]}"

def validate_signature(payload: bytes, signature: str) -> bool:
    """
    Validates the X-Hub-Signature-256 header.
    """
    if not Config.WHATSAPP_APP_SECRET:
        # Check if running in Cloud Run (K_SERVICE is always set in Cloud Run)
        is_cloud_run = os.environ.get('K_SERVICE') is not None
        
        if is_cloud_run:
            logger.error("WHATSAPP_APP_SECRET not set. Cannot validate signature. rejecting request.")
            return False
        else:
            logger.warning("WHATSAPP_APP_SECRET not set. Skipping signature validation (Local).")
            return True
    
    if not signature:
        return False
        
    expected_signature = hmac.new(
        bytes(Config.WHATSAPP_APP_SECRET, 'latin-1'),
        msg=payload,
        digestmod=hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(f'sha256={expected_signature}', signature)

def send_whatsapp_message(phone_number_id: str, to: str, message_body: str) -> None:
    """
    Sends a text message to a user via WhatsApp Graph API.
    """
    if not Config.SEND_WHATSAPP_RESPONSE:
        logger.info(f"[{to}] Skipping WhatsApp message delivery")
        logger.debug(f"[{to}] WhatsApp message: {message_body}")
        return

    if not Config.WHATSAPP_API_TOKEN:
        logger.error("WHATSAPP_API_TOKEN not set. Cannot send message.")
        return

    url = f"https://graph.facebook.com/{Config.WHATSAPP_API_VERSION}/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {Config.WHATSAPP_API_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {"body": message_body}
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        logger.info(f"Message sent to {to}: {response.json()}")
    except Exception as e:
        logger.error(f"Failed to send message to {to}: {e}")

def mark_message_as_read(phone_number_id: str, message_id: str) -> None:
    """
    Marks a message as read.
    """
    if not Config.WHATSAPP_API_TOKEN:
        logger.error("WHATSAPP_API_TOKEN not set. Cannot mark message as read.")
        return

    url = f"https://graph.facebook.com/{Config.WHATSAPP_API_VERSION}/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {Config.WHATSAPP_API_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": message_id
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        logger.debug(f"Message {message_id} marked as read.")
    except Exception as e:
        logger.error(f"Failed to mark message {message_id} as read: {e}")

@app.route('/webhook', methods=['GET', 'POST'])
def webhook_message():
    """
    Handles incoming WhatsApp messages
    https://developers.facebook.com/documentation/business-messaging/whatsapp/webhooks/reference/messages
    """
    # Handle Webhook Verification (GET)
    if request.method == 'GET':
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')

        if mode and token:
            if mode == 'subscribe' and token == Config.WHATSAPP_VERIFY_TOKEN:
                logger.info("Webhook verified successfully.")
                return challenge, 200
            else:
                logger.warning("Webhook verification failed.")
                return 'Forbidden', 403
        return 'Bad Request', 400

    # Handle Message Processing (POST)
    # Validate Signature
    signature = request.headers.get('X-Hub-Signature-256')
    if not validate_signature(request.data, signature):
        logger.warning("Signature verification failed.")
        return 'Forbidden', 403

    try:
        body = request.get_json()
        
        # Submit task to ThreadPoolExecutor
        executor.submit(process_webhook_payload, body)
        
        # Return 200 OK immediately
        return 'OK', 200

    except Exception as e:
        logger.error(f'Error handling webhook POST: {e}', exc_info=True)
        return 'Internal Server Error', 500

def process_webhook_payload(body: dict) -> None:
    """
    Processes the webhook payload in a background thread.
    """
    try:
        payload = parse_webhook_payload(body)

        if payload.entry:
            for entry in payload.entry:
                for change in entry.changes:
                    if change.value.messages:
                        # Extract phone_number_id for API calls
                        phone_number_id = change.value.metadata.phone_number_id

                        for msg in change.value.messages:
                            user_phone_number = msg.from_
                            message_id = msg.id
                            
                            # Mark as read immediately
                            mark_message_as_read(phone_number_id, message_id)
                            
                            masked_phone = mask_phone_number(user_phone_number)
                            logger.info(f"[{masked_phone}] Processing message type: {msg.type}")

                            msg_body = None
                            if msg.type == 'text':
                                msg_body = msg.text.body
                                logger.debug(f'[{masked_phone}] Text message received: "{msg_body}"')
                            elif msg.type == 'interactive':
                                interactive_type = msg.interactive.type
                                if interactive_type == 'button_reply':
                                    if msg.interactive.button_reply:
                                        msg_body = msg.interactive.button_reply.id
                                elif interactive_type == 'list_reply':
                                    if msg.interactive.list_reply:
                                        msg_body = msg.interactive.list_reply.id
                            elif msg.type == 'button':
                                msg_body = msg.button.payload or msg.button.text
                            
                            if msg_body:
                                logger.info(f"[{masked_phone}] Routing message to '{Config.ROUTING_TARGET}'")
                                if Config.ROUTING_TARGET == 'AGENT_ENGINE':
                                    # Already in a background thread from ThreadPool, call directly
                                    forward_to_adk_agent_engine(user_phone_number, msg_body, phone_number_id)
                                elif Config.ROUTING_TARGET == 'DIALOGFLOW':
                                    forward_to_dialogflow_cx(user_phone_number, msg_body, phone_number_id)
                                else:
                                    logger.warning(f"[{masked_phone}] Unknown ROUTING_TARGET: '{Config.ROUTING_TARGET}'")
                            else:
                                logger.warning(f"[{masked_phone}] Unsupported or empty message body for type: {msg.type}")

                    else:
                        logger.info(f"No messages in entry")
    except Exception as e:
        logger.error(f"Error in background processing: {e}", exc_info=True)


def forward_to_dialogflow_cx(user_phone_number: str, query: str, phone_number_id: str) -> None:
    """
    Detects Intent in Dialogflow CX and sends response back to WhatsApp.
    """
    try:
        session_client = get_dialogflow_session_client()
        session_path = session_client.session_path(
            project=Config.PROJECT_ID,
            location=Config.LOCATION,
            agent=Config.AGENT_ID,
            session=user_phone_number
        )

        text_input = TextInput(text=query)
        query_input = QueryInput(text=text_input, language_code=Config.AGENT_LANGUAGE_CODE)

        # Construct QueryParameters with user phone
        query_params = QueryParameters()
        
        if user_phone_number:
            params = struct_pb2.Struct()
            context_struct = struct_pb2.Struct()
            
            context_data = {
                "userPhone": user_phone_number
            }
                
            context_struct.update(context_data)
            params["context"] = context_struct
            
            logger.debug(f"[{mask_phone_number(user_phone_number)}] Adding phone number to Dialogflow request in: $session.params.context.userPhone")
            query_params.parameters = params

        req = DetectIntentRequest(
            session=session_path,
            query_input=query_input,
            query_params=query_params
        )

        response = session_client.detect_intent(request=req)
        # Extract text response from Dialogflow
        response_texts = []
        if response.query_result and response.query_result.response_messages:
            for msg in response.query_result.response_messages:
                if msg.text and msg.text.text:
                    response_texts.extend(msg.text.text)
        
        full_response_text = " ".join(response_texts)
        masked_phone = mask_phone_number(user_phone_number)
        logger.info(f"[{masked_phone}] Dialogflow CX response id: {response.response_id}")
        logger.debug(f"[{masked_phone}] Dialogflow CX response: {response}")
        
        if full_response_text:
            send_whatsapp_message(phone_number_id, user_phone_number, full_response_text)
        else:
            logger.warning(f"[{masked_phone}] No text response from Dialogflow.")

    except Exception as e:
        logger.error(f'Dialogflow CX Error: {e}', exc_info=True)


def forward_to_adk_agent_engine(user_phone_number: str, query: str, phone_number_id: str) -> None:
    """
    Queries the Vertex AI Agent Engine (Reasoning Engine) and sends response back to WhatsApp.
    Ensures only one session exists per user (phone number) by deleting older sessions.
    Runs SYNCHRONOUSLY.
    """
    max_retries = 1
    for attempt in range(max_retries + 1):
        try:
            session_id = ""
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
                send_whatsapp_message(phone_number_id, user_phone_number, full_response_text)
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



if __name__ == '__main__':
    # Used for local development only
    app.run(host='0.0.0.0', port=Config.PORT, debug=True)
