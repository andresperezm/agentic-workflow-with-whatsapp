import logging
import os
import json
import requests
import google.auth
from typing import Optional, List, Dict, Any, Union, Literal
from pydantic import BaseModel, Field
from .utils import get_secret

# Setup
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)


# --- Common Models ---

class TextObject(BaseModel):
    body: str

class MediaObject(BaseModel):
    link: Optional[str] = None
    id: Optional[str] = None
    caption: Optional[str] = None
    filename: Optional[str] = None

class LocationObject(BaseModel):
    latitude: float
    longitude: float
    name: Optional[str] = None
    address: Optional[str] = None

class ContactName(BaseModel):
    formatted_name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None
    suffix: Optional[str] = None
    prefix: Optional[str] = None

class ContactPhone(BaseModel):
    phone: Optional[str] = None
    type: Optional[str] = None
    wa_id: Optional[str] = None

class ContactObject(BaseModel):
    name: ContactName
    phones: Optional[List[ContactPhone]] = None
    # Add other fields as needed (emails, urls, etc.)

class InteractiveHeader(BaseModel):
    type: Literal["text", "video", "image", "document"]
    text: Optional[str] = None
    video: Optional[MediaObject] = None
    image: Optional[MediaObject] = None
    document: Optional[MediaObject] = None

class InteractiveBody(BaseModel):
    text: str

class InteractiveFooter(BaseModel):
    text: str

class InteractiveActionSectionRow(BaseModel):
    id: str
    title: str
    description: Optional[str] = None

class InteractiveActionSection(BaseModel):
    title: Optional[str] = None
    rows: List[InteractiveActionSectionRow]

class InteractiveActionButtonReply(BaseModel):
    id: str
    title: str

class InteractiveActionReplyButton(BaseModel):
    type: Literal["reply"] = "reply"
    reply: InteractiveActionButtonReply

class InteractiveActionFlowParameters(BaseModel):
    flow_message_version: str = "3"
    flow_token: str
    flow_id: str
    flow_cta: str
    flow_action: str
    flow_action_payload: Optional[Dict[str, Any]] = None

class InteractiveAction(BaseModel):
    button: Optional[str] = None # For List messages (button text)
    buttons: Optional[List[InteractiveActionReplyButton]] = None # For Reply Button messages
    sections: Optional[List[InteractiveActionSection]] = None # For List messages
    name: Optional[str] = None # For CTA URL (cta_url) or Flow (flow)
    parameters: Optional[Dict[str, Any]] = None # For CTA URL or Flow

# --- Models ---

class AudioMessage(BaseModel):
    to: str = Field(..., description="The phone number of the recipient.")
    audio: MediaObject

class ContactMessage(BaseModel):
    to: str = Field(..., description="The phone number of the recipient.")
    contacts: List[ContactObject]

class DocumentMessage(BaseModel):
    to: str = Field(..., description="The phone number of the recipient.")
    document: MediaObject

class ImageMessage(BaseModel):
    to: str = Field(..., description="The phone number of the recipient.")
    image: MediaObject

class InteractiveCtaButtonMessage(BaseModel):
    to: str = Field(..., description="The phone number of the recipient.")
    header: Optional[InteractiveHeader] = None
    body: InteractiveBody
    footer: Optional[InteractiveFooter] = None
    action: InteractiveAction # Must have name="cta_url" and parameters={"display_text": "...", "url": "..."}

class InteractiveFlowMessage(BaseModel):
    to: str = Field(..., description="The phone number of the recipient.")
    header: Optional[InteractiveHeader] = None
    body: InteractiveBody
    footer: Optional[InteractiveFooter] = None
    action: InteractiveAction # Must have name="flow" and parameters

class InteractiveListMessage(BaseModel):
    to: str = Field(..., description="The phone number of the recipient.")
    header: Optional[InteractiveHeader] = None
    body: InteractiveBody
    footer: Optional[InteractiveFooter] = None
    action: InteractiveAction # Must have button and sections

class InteractiveReplyButtonsMessage(BaseModel):
    to: str = Field(..., description="The phone number of the recipient.")
    header: Optional[InteractiveHeader] = None
    body: InteractiveBody
    footer: Optional[InteractiveFooter] = None
    action: InteractiveAction # Must have buttons

class LocationMessage(BaseModel):
    to: str = Field(..., description="The phone number of the recipient.")
    location: LocationObject

class VideoMessage(BaseModel):
    to: str = Field(..., description="The phone number of the recipient.")
    video: MediaObject

class TextMessage(BaseModel):
    to: str = Field(..., description="The phone number of the recipient.")
    text: TextObject


WHATSAPP_TOKEN = get_secret("WHATSAPP_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = get_secret("WHATSAPP_PHONE_NUMBER_ID")
BASE_URL = f"https://graph.facebook.com/v17.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"

def send_message(payload: Dict[str, Any]) -> str:
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    try:
        response = requests.post(BASE_URL, headers=headers, json=payload)
        response.raise_for_status()
        return "Message sent successfully"
    except requests.exceptions.RequestException as e:
        error_msg = e.response.text if e.response else str(e)
        logger.error(f'Error sending WhatsApp message: {error_msg}')
        return f"Error sending WhatsApp message: {error_msg}"


def send_audio_message(message: AudioMessage) -> str:
    """Sends an audio message to a WhatsApp user."""
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": message.to,
        "type": "audio",
        "audio": message.audio.model_dump(exclude_none=True)
    }
    return send_message(payload)

def send_contact_message(message: ContactMessage) -> str:
    """Sends a contact message to a WhatsApp user."""
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": message.to,
        "type": "contacts",
        "contacts": [c.model_dump(exclude_none=True) for c in message.contacts]
    }
    return send_message(payload)

def send_document_message(message: DocumentMessage) -> str:
    """Sends a document message to a WhatsApp user."""
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": message.to,
        "type": "document",
        "document": message.document.model_dump(exclude_none=True)
    }
    return send_message(payload)

def send_image_message(message: ImageMessage) -> str:
    """Sends an image message to a WhatsApp user."""
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": message.to,
        "type": "image",
        "image": message.image.model_dump(exclude_none=True)
    }
    return send_message(payload)

def send_interactive_cta_button_message(message: InteractiveCtaButtonMessage) -> str:
    """Sends an interactive CTA button message to a WhatsApp user."""
    interactive = {
        "type": "cta_url",
        "body": message.body.model_dump(exclude_none=True),
        "action": message.action.model_dump(exclude_none=True)
    }
    if message.header:
        interactive["header"] = message.header.model_dump(exclude_none=True)
    if message.footer:
        interactive["footer"] = message.footer.model_dump(exclude_none=True)

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": message.to,
        "type": "interactive",
        "interactive": interactive
    }
    return send_message(payload)

def send_interactive_flow_message(message: InteractiveFlowMessage) -> str:
    """Sends an interactive flow message to a WhatsApp user."""
    interactive = {
        "type": "flow",
        "body": message.body.model_dump(exclude_none=True),
        "action": message.action.model_dump(exclude_none=True)
    }
    if message.header:
        interactive["header"] = message.header.model_dump(exclude_none=True)
    if message.footer:
        interactive["footer"] = message.footer.model_dump(exclude_none=True)

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": message.to,
        "type": "interactive",
        "interactive": interactive
    }
    return send_message(payload)

def send_interactive_list_message(message: InteractiveListMessage) -> str:
    """Sends an interactive list message to a WhatsApp user."""
    interactive = {
        "type": "list",
        "body": message.body.model_dump(exclude_none=True),
        "action": message.action.model_dump(exclude_none=True)
    }
    if message.header:
        interactive["header"] = message.header.model_dump(exclude_none=True)
    if message.footer:
        interactive["footer"] = message.footer.model_dump(exclude_none=True)

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": message.to,
        "type": "interactive",
        "interactive": interactive
    }
    return send_message(payload)

def send_interactive_reply_buttons_message(message: InteractiveReplyButtonsMessage) -> str:
    """Sends an interactive reply buttons message to a WhatsApp user."""
    interactive = {
        "type": "button",
        "body": message.body.model_dump(exclude_none=True),
        "action": message.action.model_dump(exclude_none=True)
    }
    if message.header:
        interactive["header"] = message.header.model_dump(exclude_none=True)
    if message.footer:
        interactive["footer"] = message.footer.model_dump(exclude_none=True)

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": message.to,
        "type": "interactive",
        "interactive": interactive
    }
    return send_message(payload)

def send_location_message(message: LocationMessage) -> str:
    """Sends a location message to a WhatsApp user."""
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": message.to,
        "type": "location",
        "location": message.location.model_dump(exclude_none=True)
    }
    return send_message(payload)

def send_video_message(message: VideoMessage) -> str:
    """Sends a video message to a WhatsApp user."""
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": message.to,
        "type": "video",
        "video": message.video.model_dump(exclude_none=True)
    }
    return send_message(payload)

def send_text_message(message: TextMessage) -> str:
    """Sends a text message to a WhatsApp user."""
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": message.to,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": message.text.body
        }
    }
    return send_message(payload)
