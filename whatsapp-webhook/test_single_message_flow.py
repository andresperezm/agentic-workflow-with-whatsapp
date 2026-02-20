
import os
import logging
import time
from dotenv import load_dotenv
import vertexai

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

PROJECT_ID = os.environ.get('PROJECT_ID', os.popen('gcloud config get-value project').read().strip())
LOCATION = os.environ.get('LOCATION', 'us-central1')
AGENT_ID = os.environ.get('AGENT_ID', '1872779463893188608')

def test_flow():
    user_id = f"test_user_unique_{int(time.time())}" # Ensure new user
    logger.info(f"Testing flow for NEW user: {user_id}")
    
    agent_engine_resource_name = f"projects/{PROJECT_ID}/locations/{LOCATION}/reasoningEngines/{AGENT_ID}"
    vertex_client = vertexai.Client(project=PROJECT_ID, location=LOCATION)
    agent = vertex_client.agent_engines.get(name=agent_engine_resource_name)
    
    # 1. Check existing sessions (Should be 0)
    logger.info("1. Checking existing sessions...")
    resp = agent.list_sessions(user_id=user_id)
    initial_sessions = resp.get('sessions', [])
    logger.info(f"Initial sessions count: {len(initial_sessions)}")
    
    if len(initial_sessions) > 0:
        logger.warning("User already has sessions! Test might be invalid.")
    
    # 2. Simulate logic from main.py
    session_id = ""
    # Logic from main.py: if sessions found, use [0], else leave ""
    if initial_sessions:
        session_id = initial_sessions[0].get('id')
    
    logger.info(f"Session ID to use: '{session_id}' (Empty means create new)")
    
    # 3. Stream query (Should create exactly 1 session)
    logger.info("2. Sending message (stream_query)...")
    query = "Hello, who are you?"
    iterator = agent.stream_query(message=query, user_id=user_id, session_id=session_id)
    
    # Consume iterator
    for chunk in iterator:
        pass 
    logger.info("Stream finished.")
    
    # 4. Check sessions again (Should be 1)
    logger.info("3. Checking sessions after message...")
    resp_after = agent.list_sessions(user_id=user_id)
    final_sessions = resp_after.get('sessions', [])
    logger.info(f"Final sessions count: {len(final_sessions)}")
    
    for s in final_sessions:
        logger.info(f"Session: {s.get('id')} - Created: {s.get('createTime')}")

    if len(final_sessions) == 1:
        logger.info("✅ SUCCESS: Exactly 1 session created.")
    elif len(final_sessions) == 0:
         logger.error("❌ FAILURE: No session created?")
    else:
        logger.error(f"❌ FAILURE: Created {len(final_sessions)} sessions!")

if __name__ == "__main__":
    test_flow()
