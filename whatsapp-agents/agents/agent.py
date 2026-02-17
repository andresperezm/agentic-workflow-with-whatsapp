import logging
import os

from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.llm_agent import LlmAgent
from google.adk.tools.tool_context import ToolContext
from google.adk.models import LlmResponse
from google.genai import types
from typing import Dict, Any, Optional

from .services.user import get_user, GetUserRequest
from .services.order import get_orders, GetOrdersRequest, get_items, GetItemsRequest, get_item, GetItemRequest, get_order, GetOrderRequest, cancel_order, CancelOrderRequest, add_feedback, AddFeedbackRequest, remove_item, RemoveItemRequest
from .services.whatsapp import send_interactive_list_message, InteractiveListMessage, InteractiveHeader, InteractiveBody, InteractiveFooter, InteractiveAction, InteractiveActionSection, InteractiveActionSectionRow, send_text_message, TextMessage, TextObject, send_image_message, ImageMessage, MediaObject, send_interactive_reply_buttons_message, InteractiveReplyButtonsMessage, InteractiveActionButtonReply, InteractiveActionReplyButton

# Setup
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)

agent_path = os.path.dirname(os.path.abspath(__file__))

# Callbacks
def before_agent_modifier(callback_context: CallbackContext) -> Optional[types.Content]:
    if callback_context.state.get('user_phone_number') is None:
        user_phone_number = callback_context.user_id
        # for local testing
        if user_phone_number == "user":
            user_phone_number = os.environ.get('DEFAULT_PHONE_NUMBER')
        callback_context.state['user_phone_number'] = user_phone_number

    if callback_context.state.get('user_email') is None:
        user = get_user(GetUserRequest(phone_number=user_phone_number))
        if user:
            if callback_context.state.get('user_email') is None:
                callback_context.state['user_email'] = user.userEmail
            if callback_context.state.get('user_name') is None:
                callback_context.state['user_name'] = user.userName

    return None

def modify_output_after_agent(callback_context: CallbackContext) -> Optional[types.Content]:
    if callback_context.state.get('message_sent_by_tool'):
        return None
    else:
        send_text_message(TextMessage(
            to=tool_context.state.get('user_phone_number'),
            text=TextObject(body=callback_context.response)
        ))
        return None

def simple_after_model_modifier(callback_context: CallbackContext, llm_response: LlmResponse) -> Optional[LlmResponse]:
    """Inspects/modifies the LLM response after it's received."""
    original_text = ""
    if llm_response.content and llm_response.content.parts:
        if llm_response.content.parts[0].text:
            original_text = llm_response.content.parts[0].text
        elif llm_response.content.parts[0].function_call:
             logger.info("No text modification")
        else:
            logger.info("No text found")
    elif llm_response.error_message:
        logger.info("Agent error")
    else:
        logger.info("Empty LlmResponse.")
    if not callback_context.state.get('whatsapp_message_sent'):
        callback_context.state['whatsapp_message_sent'] = False
        logger.info("Sending message to whatsapp")
        send_text_message(TextMessage(
            to=callback_context.state.get('user_phone_number'),
            text=TextObject(body=original_text)
        ))
        logger.info("Message sent to whatsapp")
    return None

# --- Tools ---

def get_user_email(tool_context: ToolContext) -> str:
    return tool_context.state.get('user_email')

def get_user_phone_number(tool_context: ToolContext) -> str:
    return tool_context.state.get('user_phone_number')

def get_user_name(tool_context: ToolContext) -> str:
    return tool_context.state.get('user_name')

def get_date() -> Dict[str, Any]:
    """Fetches the current date from the service."""
    try:
        response = requests.get(f'{BASE_URL}/date', headers=_get_headers())
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching date: {e}")
        return {"error": str(e)}

def get_user_orders(tool_context: ToolContext) -> Dict[str, Any]:
    email = get_user_email(tool_context)
    orders = get_orders(GetOrdersRequest(email=email))
    message = InteractiveListMessage(
        to=tool_context.state.get('user_phone_number'),
        header=InteractiveHeader(
            type="text",
            text="Órdenes de compra"
        ),
        body=InteractiveBody(
            text="A continuación se muestran tus órdenes de compra:",
        ),
        footer=InteractiveFooter(
            text="Estas son tus órdenes de compra recientes.",
        ),
        action=InteractiveAction(
            button="Ver órdenes",
            sections=[
                InteractiveActionSection(
                    title="Órdenes recientes",
                    rows=[
                        InteractiveActionSectionRow(
                            id=order.orderId,
                            title=f"Orden: {order.orderId}",
                            description=f"Estado: {order.status} | Fecha: {order.createdAt[:10] if order.createdAt else 'N/A'} | Items: {order.itemCount} | Total: ${order.totalAmount}",
                        )
                        for order in orders
                    ],
                )
            ],
        ),
    )
    send_interactive_list_message(message) 
    return {"orders": orders}

def get_user_items(tool_context: ToolContext) -> Dict[str, Any]:
    email = get_user_email(tool_context)
    items = get_items(GetItemsRequest(email=email))
    if not items:
        # Send a text message instead if no items found
        send_text_message(TextMessage(
            to=tool_context.state.get('user_phone_number'),
            text=TextObject(body="No se encontraron items recientes asociados a tu cuenta.")
        ))
        return {"items": []}

    # Limit to 10 items
    items = items[:10]

    message = InteractiveListMessage(
        to=tool_context.state.get('user_phone_number'),
        header=InteractiveHeader(
            type="text",
            text="Items de compra"
        ),
        body=InteractiveBody(
            text="A continuación se muestran los items de compra recientes:",
        ),
        footer=InteractiveFooter(
            text="Selecciona un item para ver más detalles.",
        ),
        action=InteractiveAction(
            button="Ver items",
            sections=[
                InteractiveActionSection(
                    title="Items recientes",
                    rows=[
                        InteractiveActionSectionRow(
                            id=f"{item.productId}",
                            title=f"{item.name[:21]}..." if len(item.name) > 24 else item.name,
                            description=f"Estado: {item.status} | Cantidad: {item.quantity} | Precio: ${item.priceAtPurchase}"[:72],
                        )
                        for item in items
                    ],
                )
            ],
        ),
    )   
    send_interactive_list_message(message) 
    return {"items": items}

def get_user_item(product_id: str, tool_context: ToolContext) -> Dict[str, Any]:
    email = get_user_email(tool_context)
    item = get_item(GetItemRequest(email=email, product_id=product_id))

    if not item:
        send_text_message(TextMessage(
            to=tool_context.state.get('user_phone_number'),
            text=TextObject(body=f"No se encontraron detalles del item.")
        ))
        return {"error": "Item not found"}

    if item.image:
        header = InteractiveHeader(
            type="image",
            image=MediaObject(link=item.image)
        )
    else:
        header = InteractiveHeader(
             type="text",
             text="Detalles del item"
        )

    message_body = f"Item: {item.name}\nEstado: {item.status}\nPrecio: ${item.priceAtPurchase}"

    # Use reply button for Add Feedback
    # Note: Assuming orderId is available on the item. If not, maybe use productId. But user asked for add_feedback.
    # The ID must be unique. Let's encode the action.
    button_id = f"add_feedback_{item.orderId}_{item.productId}" if item.orderId else f"add_feedback_{item.productId}"

    message = InteractiveReplyButtonsMessage(
        to=tool_context.state.get('user_phone_number'),
        header=header,
        body=InteractiveBody(text=message_body),
        action=InteractiveAction(
            buttons=[
                InteractiveActionReplyButton(
                    reply=InteractiveActionButtonReply(
                        id=button_id,
                        title="Agregar feedback"
                    )
                )
            ]
        )
    )
    send_interactive_reply_buttons_message(message)

    return {"item": item}

def get_user_order(order_id: str, tool_context: ToolContext) -> Dict[str, Any]:
    email = get_user_email(tool_context)
    order = get_order(GetOrderRequest(email=email, order_id=order_id))

    if not order:
        send_text_message(TextMessage(
            to=tool_context.state.get('user_phone_number'),
            text=TextObject(body="No se encontraron detalles de la orden.")
        ))
        return {"error": "Order not found"}

    message_body = f"Orden: {order.orderId}\nEstado: {order.status}\nTotal: ${order.totalAmount}\nItems: {order.itemCount}"

    message = InteractiveReplyButtonsMessage(
        to=tool_context.state.get('user_phone_number'),
        header=InteractiveHeader(
            type="text",
            text="Detalles de la orden"
        ),
        body=InteractiveBody(text=message_body),
        action=InteractiveAction(
            buttons=[
                InteractiveActionReplyButton(
                    reply=InteractiveActionButtonReply(
                        id=f"cancel_order_{order.orderId}",
                        title="Cancelar orden"
                    )
                ),
                InteractiveActionReplyButton(
                    reply=InteractiveActionButtonReply(
                        id=f"remove_item_{order.orderId}",
                        title="Remover item"
                    )
                )
            ]
        )
    )
    send_interactive_reply_buttons_message(message)
    return {"order": order}

def cancel_user_order(order_id: str, tool_context: ToolContext) -> Dict[str, Any]:
    email = get_user_email(tool_context)
    result = cancel_order(CancelOrderRequest(email=email, order_id=order_id))
    if result.get('error'):
         send_text_message(TextMessage(
            to=tool_context.state.get('user_phone_number'),
            text=TextObject(body=f"No se pudo cancelar la orden: {result.get('error')}")
        ))
         return result
    
    send_text_message(TextMessage(
        to=tool_context.state.get('user_phone_number'),
        text=TextObject(body=f"La orden {order_id} ha sido cancelada.")
    ))
    return result

def add_user_feedback(order_id: str, feedback: str, tool_context: ToolContext) -> Dict[str, Any]:
    email = get_user_email(tool_context)
    result = add_feedback(AddFeedbackRequest(email=email, order_id=order_id, feedback=feedback))
    if result.get('error'):
        send_text_message(TextMessage(
            to=tool_context.state.get('user_phone_number'),
            text=TextObject(body=f"No se pudo agregar el feedback: {result.get('error')}")
        ))
        return result

    send_text_message(TextMessage(
        to=tool_context.state.get('user_phone_number'),
        text=TextObject(body="¡Gracias por tus comentarios!")
    ))
    return result

def remove_user_item(order_id: str, product_id: str, tool_context: ToolContext) -> Dict[str, Any]:
    email = get_user_email(tool_context)
    result = remove_item(RemoveItemRequest(email=email, order_id=order_id, product_id=product_id))
    if result.get('error'):
        send_text_message(TextMessage(
            to=tool_context.state.get('user_phone_number'),
            text=TextObject(body=f"No se pudo remover el item: {result.get('error')}")
        ))
        return result

    send_text_message(TextMessage(
        to=tool_context.state.get('user_phone_number'),
        text=TextObject(body=f"El item {product_id} ha sido removido de la orden {order_id}.")
    ))
    return result

# Agents

## Purchase Orders Agent
PURCHASE_ORDERS_AGENT_NAME = "purchase_orders_agent"
PURCHASE_ORDERS_AGENT_MODEL = "gemini-2.5-flash"
purchase_orders_agent_prompt_path = os.path.join(agent_path, "prompts", f"{PURCHASE_ORDERS_AGENT_NAME}_instructions.md")
purchase_orders_agent_prompt = None
with open(purchase_orders_agent_prompt_path, "r") as file:
    purchase_orders_agent_prompt = file.read()
if not purchase_orders_agent_prompt:
    logger.error(f"Failed to load {PURCHASE_ORDERS_AGENT_NAME} instructions. path: {purchase_orders_agent_prompt_path}")
    raise SystemExit(1)

purchase_orders_agent = LlmAgent(
    name=PURCHASE_ORDERS_AGENT_NAME,
    model=PURCHASE_ORDERS_AGENT_MODEL,
    instruction=purchase_orders_agent_prompt,
    tools=[
        get_date,
        get_user_email,
        get_user_phone_number,
        get_user_name,
        get_user_orders,
        get_user_items,
        get_user_item,
        get_user_order,
        cancel_user_order,
        add_user_feedback,
        remove_user_item
    ],
    before_agent_callback=before_agent_modifier,
    after_model_callback=simple_after_model_modifier
)

## Steering Agent
STEERING_AGENT_NAME = "steering_agent"
STEERING_AGENT_MODEL = "gemini-2.5-flash"
steering_agent_prompt_path = os.path.join(agent_path, "prompts", f"{STEERING_AGENT_NAME}_instructions.md")
steering_agent_prompt = None
with open(steering_agent_prompt_path, "r") as file:
    steering_agent_prompt = file.read()
if not steering_agent_prompt:
    logger.error(f"Failed to load {STEERING_AGENT_NAME} instructions. path: {steering_agent_prompt_path}")
    raise SystemExit(1)

root_agent = LlmAgent(
    name=STEERING_AGENT_NAME,
    model=STEERING_AGENT_MODEL,
    instruction=steering_agent_prompt,
    sub_agents=[purchase_orders_agent],
    after_model_callback=simple_after_model_modifier
)
