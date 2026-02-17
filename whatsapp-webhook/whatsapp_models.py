from datetime import datetime
from typing import List, Optional, Union, Literal
from pydantic import BaseModel, Field

# --- Common Objects ---

class Text(BaseModel):
    body: str

class Image(BaseModel):
    id: str
    mime_type: str
    sha256: str
    caption: Optional[str] = None

class Video(BaseModel):
    id: str
    mime_type: str
    sha256: str
    caption: Optional[str] = None

class Audio(BaseModel):
    id: str
    mime_type: str
    sha256: str
    voice: Optional[bool] = False

class Document(BaseModel):
    id: str
    mime_type: str
    sha256: str
    caption: Optional[str] = None
    filename: Optional[str] = None

class Context(BaseModel):
    from_: str = Field(alias="from")
    id: str

class Error(BaseModel):
    code: int
    title: str
    message: str
    error_data: Optional[dict] = None

class Profile(BaseModel):
    name: str

class Contact(BaseModel):
    profile: Profile
    wa_id: str

class InteractiveListReply(BaseModel):
    id: str
    title: str
    description: Optional[str] = None

class InteractiveButtonReply(BaseModel):
    id: str
    title: str

class Interactive(BaseModel):
    type: Literal["list_reply", "button_reply"]
    list_reply: Optional[InteractiveListReply] = None
    button_reply: Optional[InteractiveButtonReply] = None

class Reaction(BaseModel):
    message_id: str
    emoji: str

class Location(BaseModel):
    latitude: float
    longitude: float
    name: Optional[str] = None
    address: Optional[str] = None

class Sticker(BaseModel):
    mime_type: str
    sha256: str
    id: str
    animated: Optional[bool] = False

class Button(BaseModel):
    payload: Optional[str] = None
    text: str

# --- Message Types ---

class MessageBase(BaseModel):
    from_: str = Field(alias="from")
    id: str
    timestamp: str 
    type: str # Discriminator field
    context: Optional[Context] = None

class TextMessage(MessageBase):
    type: Literal["text"]
    text: Text

class ImageMessage(MessageBase):
    type: Literal["image"]
    image: Image

class VideoMessage(MessageBase):
    type: Literal["video"]
    video: Video

class AudioMessage(MessageBase):
    type: Literal["audio"]
    audio: Audio

class DocumentMessage(MessageBase):
    type: Literal["document"]
    document: Document

class InteractiveMessage(MessageBase):
    type: Literal["interactive"]
    interactive: Interactive

class ReactionMessage(MessageBase):
    type: Literal["reaction"]
    reaction: Reaction

class LocationMessage(MessageBase):
    type: Literal["location"]
    location: Location

class StickerMessage(MessageBase):
    type: Literal["sticker"]
    sticker: Sticker

class ButtonMessage(MessageBase):
    type: Literal["button"]
    button: Button
    
class UnknownMessage(MessageBase):
    type: Literal["unknown"]
    errors: Optional[List[Error]] = None

# Union for all message types
Message = Union[
    TextMessage,
    ImageMessage,
    VideoMessage,
    AudioMessage,
    DocumentMessage,
    InteractiveMessage,
    ReactionMessage,
    LocationMessage,
    StickerMessage,
    ButtonMessage,
    UnknownMessage
]

# --- Status Updates ---

class Pricing(BaseModel):
    billable: bool
    pricing_model: str
    category: str

class Origin(BaseModel):
    type: str

class Conversation(BaseModel):
    id: str
    entry_point: Optional[Origin] = None # 'origin' in some docs
    expiration_timestamp: Optional[str] = None

class Status(BaseModel):
    id: str
    status: Literal["sent", "delivered", "read", "failed"]
    timestamp: str
    recipient_id: str
    conversation: Optional[Conversation] = None
    pricing: Optional[Pricing] = None
    errors: Optional[List[Error]] = None

# --- Webhook Structure ---

class Metadata(BaseModel):
    display_phone_number: str
    phone_number_id: str

class Value(BaseModel):
    messaging_product: str
    metadata: Metadata
    contacts: Optional[List[Contact]] = None
    messages: Optional[List[Message]] = None
    statuses: Optional[List[Status]] = None

class Change(BaseModel):
    value: Value
    field: str

class Entry(BaseModel):
    id: str
    changes: List[Change]

class WhatsAppWebhookPayload(BaseModel):
    object: str
    entry: List[Entry]


# --- Helper Method ---

def parse_webhook_payload(payload: dict) -> WhatsAppWebhookPayload:
    """
    Parses a dictionary payload into a WhatsAppWebhookPayload Pydantic model.
    """
    return WhatsAppWebhookPayload(**payload)
