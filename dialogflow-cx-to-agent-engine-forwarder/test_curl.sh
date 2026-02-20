#!/bin/bash

# Test script for dialogflow-cx-to-agent-engine-forwarder
# Usage: ./test_curl.sh [HOST] [PORT]

HOST="${1:-localhost}"
PORT="${2:-8082}"

echo "Sending test request to http://$HOST:$PORT/message..."

curl -X POST "http://$HOST:$PORT/message" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-session-uwu-001",
    "user_utterance": "Hello, is this working?",
    "agent_id": "placeholder-agent-id",
    "project_id": "placeholder-project-id",
    "location_id": "us-central1",
    "user_phone": "+15551234567"
  }'

echo -e "\nRequest sent."
