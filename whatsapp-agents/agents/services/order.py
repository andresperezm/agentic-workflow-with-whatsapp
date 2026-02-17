import json
import logging
import os
import requests
from typing import List, Dict, Any
from .utils import get_headers
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal

# Setup
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)

# Configuration
PURCHASE_ORDERS_SERVICE_URL = os.environ.get("PURCHASE_ORDERS_SERVICE_URL")

# Models
class OrderItem(BaseModel):
    orderId: Optional[str] = None
    productId: str
    name: str
    quantity: int
    priceAtPurchase: float
    image: Optional[str] = None
    status: str
    carrier: Optional[str] = None
    trackingNumber: Optional[str] = None
    shippedAt: Optional[str] = None # Datetime or empty string

class Order(BaseModel):
    orderId: str
    userEmail: Optional[str] = None
    userPhone: Optional[str] = None
    status: Literal['creada', 'procesando', 'enviada', 'entregada', 'cancelada']
    totalAmount: Optional[float] = None
    shippingAddress: Optional[str] = None
    createdAt: Optional[str] = None # Datetime
    itemCount: int = 0
    items: List[OrderItem] = []

    @field_validator('items', mode='before')
    @classmethod
    def set_items_to_empty_list_if_none(cls, v):
        return v or []

class GetOrdersRequest(BaseModel):
    email: str = Field(..., description="Email of the user")
    status: Optional[Literal['creada', 'procesando', 'enviada', 'entregada', 'cancelada']] = Field(None, description="Filter orders by status")

class GetItemsRequest(BaseModel):
    email: str = Field(..., description="Email of the user")
    order_id: Optional[str] = Field(None, description="Filter items by order ID")

class RemoveItemRequest(BaseModel):
    email: str = Field(..., description="Email of the user")
    order_id: str = Field(..., description="ID of the order")
    product_id: str = Field(..., description="ID of the product to remove")

class CancelOrderRequest(BaseModel):
    email: str = Field(..., description="Email of the user")
    order_id: str = Field(..., description="ID of the order to cancel")

class AddFeedbackRequest(BaseModel):
    email: str = Field(..., description="Email of the user")
    order_id: str = Field(..., description="ID of the order")
    feedback: str = Field(..., description="Feedback text")

class GetItemRequest(BaseModel):
    email: str = Field(..., description="Email of the user")
    product_id: str = Field(..., description="ID of the product")

class GetOrderRequest(BaseModel):
    email: str = Field(..., description="Email of the user")
    order_id: str = Field(..., description="ID of the order")

# Methods

def get_orders(request: GetOrdersRequest) -> List[Order]:
    """Fetches orders for a given email, optionally filtered by status."""
    params = {'email': request.email}
    if request.status:
        params['status'] = request.status
    
    try:
        response = requests.get(f'{PURCHASE_ORDERS_SERVICE_URL}/orders', params=params, headers=get_headers(PURCHASE_ORDERS_SERVICE_URL))
        response.raise_for_status()
        return [Order(**order) for order in response.json()]
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching orders: {e}")
        return []


def get_order(request: GetOrderRequest) -> Optional[Order]:
    """Fetches a single order by ID."""
    params = {'email': request.email}
    try:
        response = requests.get(f'{PURCHASE_ORDERS_SERVICE_URL}/orders/{request.order_id}', params=params, headers=get_headers(PURCHASE_ORDERS_SERVICE_URL))
        response.raise_for_status()
        return Order(**response.json())
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching order: {e}")
        return None


def get_items(request: GetItemsRequest) -> List[OrderItem]:
    """Fetches purchased items for a user, optionally filtered by order ID."""
    params = {'email': request.email}
    if request.order_id:
        params['orderId'] = request.order_id

    try:
        response = requests.get(f'{PURCHASE_ORDERS_SERVICE_URL}/items', params=params, headers=get_headers(PURCHASE_ORDERS_SERVICE_URL))
        response.raise_for_status()
        return [OrderItem(**item) for item in response.json()]
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching items: {e}")
        return []


def remove_item(request: RemoveItemRequest) -> Dict[str, Any]:
    """Removes an item from an order."""
    payload = {
        'email': request.email,
        'orderId': request.order_id,
        'productId': request.product_id
    }
    headers = get_headers(PURCHASE_ORDERS_SERVICE_URL)
    headers['Content-Type'] = 'application/json'

    try:
        response = requests.post(f'{PURCHASE_ORDERS_SERVICE_URL}/orders/remove-item', json=payload, headers=headers)
        return response.json()

    except requests.exceptions.RequestException as e:
        logger.error(f"Error removing item: {e}")
        return {"error": str(e)}
    except ValueError:
        logger.error(f"Error decoding JSON. Status: {response.status_code}, Body: {response.text}")
        return {"error": "Invalid JSON response"}


def get_item(request: GetItemRequest) -> Optional[OrderItem]:
    """Fetches a single item for a user."""
    # Note: URL pattern is /items/<PRODUCT_ID>?email=<EMAIL> as per user request
    params = {'email': request.email}
    
    try:
        response = requests.get(f'{PURCHASE_ORDERS_SERVICE_URL}/items/{request.product_id}', params=params, headers=get_headers(PURCHASE_ORDERS_SERVICE_URL))
        response.raise_for_status()
        return OrderItem(**response.json())
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching item: {e}")
        return None


def cancel_order(request: CancelOrderRequest) -> Dict[str, Any]:
    """Cancels an order."""
    payload = {
        'email': request.email,
        'orderId': request.order_id
    }
    headers = get_headers(PURCHASE_ORDERS_SERVICE_URL)
    headers['Content-Type'] = 'application/json'

    try:
        response = requests.post(f'{PURCHASE_ORDERS_SERVICE_URL}/orders/cancel', json=payload, headers=headers)
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error cancelling order: {e}")
        return {"error": str(e)}
    except ValueError:
         logger.error(f"Error decoding JSON. Status: {response.status_code}, Body: {response.text}")
         return {"error": "Invalid JSON response"}


def add_feedback(request: AddFeedbackRequest) -> Dict[str, Any]:
    """Adds feedback to an order."""
    payload = {
        'email': request.email,
        'orderId': request.order_id,
        'feedback': request.feedback
    }
    headers = get_headers(PURCHASE_ORDERS_SERVICE_URL)
    headers['Content-Type'] = 'application/json'

    try:
        response = requests.post(f'{PURCHASE_ORDERS_SERVICE_URL}/orders/feedback', json=payload, headers=headers)
        return response.json()

    except requests.exceptions.RequestException as e:
        logger.error(f"Error adding feedback: {e}")
        return {"error": str(e)}
    except ValueError:
         logger.error(f"Error decoding JSON. Status: {response.status_code}, Body: {response.text}")
         return {"error": "Invalid JSON response"}
