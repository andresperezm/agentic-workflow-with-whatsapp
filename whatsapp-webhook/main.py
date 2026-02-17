import os
import json
import logging
import requests
import hmac
import hashlib
from flask import Flask, request, jsonify
from google.cloud.dialogflowcx_v3.services.sessions.client import SessionsClient
from google.cloud.dialogflowcx_v3.types.session import DetectIntentRequest, TextInput, QueryInput
import vertexai
from vertexai import agent_engines
from dotenv import load_dotenv
from whatsapp_models import parse_webhook_payload


# Load local environment variables if present
load_dotenv()


# Configure logging
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)


app = Flask(__name__)


# Environment variables
PORT = int(os.environ.get('PORT', 8080))
WEBHOOK_VERIFY_TOKEN = os.environ.get('WEBHOOK_VERIFY_TOKEN')


ROUTING_TARGET = os.environ.get('ROUTING_TARGET', 'AGENT_ENGINE')

if ROUTING_TARGET == 'AGENT_ENGINE':
    logger.info("Agent Engine routing enabled")
    AGENT_ENGINE_PROJECT_NUMBER = os.environ.get('AGENT_ENGINE_PROJECT_NUMBER')
    AGENT_ENGINE_LOCATION = os.environ.get('AGENT_ENGINE_LOCATION')
    AGENT_ENGINE_REASONING_ENGINE_ID = os.environ.get('AGENT_ENGINE_REASONING_ENGINE_ID')

    missing_ae_vars = []
    if not AGENT_ENGINE_PROJECT_NUMBER:
        missing_ae_vars.append('AGENT_ENGINE_PROJECT_NUMBER')
    if not AGENT_ENGINE_LOCATION:
        missing_ae_vars.append('AGENT_ENGINE_LOCATION')
    if not AGENT_ENGINE_REASONING_ENGINE_ID:
        missing_ae_vars.append('AGENT_ENGINE_REASONING_ENGINE_ID')

    if missing_ae_vars:
        logger.error(f"Missing required environment variables for Agent Engine: {', '.join(missing_ae_vars)}")
        exit(1)

    AGENT_ENGINE_RESOURCE_NAME = f"projects/{AGENT_ENGINE_PROJECT_NUMBER}/locations/{AGENT_ENGINE_LOCATION}/reasoningEngines/{AGENT_ENGINE_REASONING_ENGINE_ID}"
    vertex_client = vertexai.Client(
        project=AGENT_ENGINE_PROJECT_NUMBER,
        location=AGENT_ENGINE_LOCATION,
    )
    agent = vertex_client.agent_engines.get(name=AGENT_ENGINE_RESOURCE_NAME)
elif ROUTING_TARGET == 'DIALOGFLOW':
    logger.info("Dialogflow CX routing enabled")
    DIALOGFLOW_PROJECT_ID = os.environ.get('DIALOGFLOW_PROJECT_ID')
    DIALOGFLOW_AGENT_ID = os.environ.get('DIALOGFLOW_AGENT_ID')
    DIALOGFLOW_LOCATION = os.environ.get('DIALOGFLOW_LOCATION')

    missing_df_vars = []
    if not DIALOGFLOW_PROJECT_ID:
        missing_df_vars.append('DIALOGFLOW_PROJECT_ID')
    if not DIALOGFLOW_AGENT_ID:
        missing_df_vars.append('DIALOGFLOW_AGENT_ID')
    if not DIALOGFLOW_LOCATION:
        missing_df_vars.append('DIALOGFLOW_LOCATION')

    if missing_df_vars:
        logger.error(f"Missing required environment variables for Dialogflow CX: {', '.join(missing_df_vars)}")
        exit(1)
    DIALOGFLOW_LANGUAGE_CODE = os.environ.get('DIALOGFLOW_LANGUAGE_CODE', 'en')
    api_endpoint = f"{DIALOGFLOW_LOCATION}-dialogflow.googleapis.com"
    session_client = SessionsClient(client_options={"api_endpoint": api_endpoint})
    
else:
    logger.error(f"Invalid ROUTING_TARGET: {ROUTING_TARGET}")
    exit(1)

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
            if mode == 'subscribe' and token == WEBHOOK_VERIFY_TOKEN:
                logger.info("Webhook verified successfully.")
                return challenge, 200
            else:
                logger.warning("Webhook verification failed.")
                return 'Forbidden', 403
        return 'Bad Request', 400

    # Handle Message Processing (POST)
    try:
        body = request.get_json()
        payload = parse_webhook_payload(body)

        if payload.entry:
            for entry in payload.entry:
                for change in entry.changes:

                    if change.value.messages:
                        for msg in change.value.messages:
                            from_number = msg.from_
                            logger.info(f"[{from_number}] Processing message type: {msg.type}")

                            if msg.type == 'text':
                                msg_body = msg.text.body
                                logger.debug(f'[{from_number}] Text message received: "{msg_body}"')
                                logger.info(f"[{from_number}] Routing text message to {ROUTING_TARGET}")

                                if ROUTING_TARGET == 'AGENT_ENGINE':
                                    forward_to_adk_agent_engine(from_number, msg_body)
                                    return 'OK', 202
                                elif ROUTING_TARGET == 'DIALOGFLOW':
                                    forward_to_dialogflow_cx(from_number, msg_body)
                                    return 'OK', 202

                            elif msg.type == 'interactive':
                                interactive_type = msg.interactive.type
                                msg_body = None

                                if interactive_type == 'button_reply':
                                    if msg.interactive.button_reply:
                                        msg_body = msg.interactive.button_reply.id
                                        logger.debug(f'[{from_number}] Interactive button reply id: "{msg_body}" title: "{msg.interactive.button_reply.title}"')
                                elif interactive_type == 'list_reply':
                                    if msg.interactive.list_reply:
                                        msg_body = msg.interactive.list_reply.id
                                        logger.debug(f'[{from_number}] Interactive list reply id: "{msg_body}" title: "{msg.interactive.list_reply.title}"')
                                else:
                                    logger.warning(f"[{from_number}] Unsupported interactive type: {interactive_type}")
                                    return 'Unsupported interactive type', 415

                                if msg_body:
                                    logger.info(f"[{from_number}] Routing interactive message to {ROUTING_TARGET}")
                                    if ROUTING_TARGET == 'AGENT_ENGINE':
                                        forward_to_adk_agent_engine(from_number, msg_body)
                                        return 'OK', 202
                                    elif ROUTING_TARGET == 'DIALOGFLOW':
                                        forward_to_dialogflow_cx(from_number, msg_body)
                                        return 'OK', 202
                                else:
                                    logger.warning(f"[{from_number}] Missing content for interactive message type: {interactive_type}")
                                    return 'Missing content', 400

                            elif msg.type == 'button':
                                msg_body = msg.button.payload or msg.button.text
                                logger.debug(f'[{from_number}] Button message received: "{msg_body}"')
                                logger.info(f"[{from_number}] Routing button message to {ROUTING_TARGET}")

                                if ROUTING_TARGET == 'AGENT_ENGINE':
                                    forward_to_adk_agent_engine(from_number, msg_body)
                                    return 'OK', 202
                                elif ROUTING_TARGET == 'DIALOGFLOW':
                                    forward_to_dialogflow_cx(from_number, msg_body)
                                    return 'OK', 202

                            else:
                                logger.warning(f"[{from_number}] Unsupported message type: {msg.type}")
                                return 'Unsupported message type', 415
                    else:
                        logger.debug(f"No messages in entry: {entry}")
                        return 'No messages entry', 200

            return 'Unprocessable Entity', 400
        else:
            logger.warning("No entry in payload")
            return 'No entry in payload', 400

    except Exception as e:
        logger.error(f'Error handling webhook POST: {e}', exc_info=True)
        return 'Internal Server Error', 500


def forward_to_dialogflow_cx(session_id: str, query: str):
    """
    Detects Intent in Dialogflow CX
    """
    try:
        session_path = session_client.session_path(
            project=DIALOGFLOW_PROJECT_ID,
            location=DIALOGFLOW_LOCATION,
            agent=DIALOGFLOW_AGENT_ID,
            session=session_id
        )

        text_input = TextInput(text=query)
        query_input = QueryInput(text=text_input, language_code=DIALOGFLOW_LANGUAGE_CODE)

        req = DetectIntentRequest(
            session=session_path,
            query_input=query_input
        )

        response = session_client.detect_intent(request=req)
        logger.info(f"[{session_id}] Message processed by Dialogflow CX")
        logger.debug(f"[{session_id}] Dialogflow CX Response: {response}")

    except Exception as e:
        logger.error(f'Dialogflow CX Error: {e}', exc_info=True)


def forward_to_adk_agent_engine(user_id: str, query: str):
    """
    Queries the Vertex AI Agent Engine (Reasoning Engine)
    Ensures only one session exists per user (phone number).
    """
    try:
        session_id = None
        # Check for existing sessions for this user
        try:
            sessions_resp = agent.list_sessions(user_id=user_id)
            for session in sessions_resp.get('sessions', []):
                if session.get('userId') == user_id:
                    session_id = session.get('id')
                    logger.info(f"[{user_id}] Found existing session: {session_id}")
                    break
        except Exception as e:
            logger.error(f"[{user_id}] Error listing sessions: {e}", exc_info=True)

        # Create new session if none found
        if not session_id:
            try:
                logger.info(f"[{user_id}] Creating new session...")
                session = agent.create_session(user_id=user_id)
                if hasattr(session, 'name'):
                    session_id = session.name.split('/')[-1]
                elif isinstance(session, dict):
                    session_id = session.get('id') or session.get('name', '').split('/')[-1]
                logger.info(f"[{user_id}] Created new session: {session_id}")
            except Exception as e:
                logger.error(f"[{user_id}] Failed to create session: {e}", exc_info=True)

        full_response_text = ""
        
        # Stream query the agent
        # Pass both user_id and the resolved session_id
        for response in agent.stream_query(message=query, user_id=user_id, session_id=session_id):
            try:
                # Check for the structure provided in the sample
                if 'content' in response and 'parts' in response['content']:
                    parts = response['content']['parts']
                    for part in parts:
                        if 'text' in part:
                            full_response_text += part['text']
            except Exception as e:
                logger.error(f"[{user_id}] Error parsing chunk: {e}")

        if full_response_text:
            logger.debug(f"[{user_id}] Agent Engine response: {full_response_text}")
        else:
            logger.warning(f"[{user_id}] No text in response")

    except Exception as e:
        logger.error(f'[{user_id}] Agent Engine Error: {e}', exc_info=True)



if __name__ == '__main__':
    # Used for local development only
    app.run(host='0.0.0.0', port=PORT, debug=True)
