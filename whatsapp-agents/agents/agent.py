import logging
import os

from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.llm_agent import LlmAgent
from google.adk.tools.tool_context import ToolContext
from google.adk.tools.base_tool import BaseTool
from google.adk.models import LlmResponse
from google.genai import types
from typing import Dict, Any, Optional

from .services.user import get_user, GetUserRequest
from .services.order import get_orders, GetOrdersRequest, get_items, GetItemsRequest, get_item, GetItemRequest, get_order, GetOrderRequest, cancel_order, CancelOrderRequest, add_feedback, AddFeedbackRequest, remove_item, RemoveItemRequest
from .services.whatsapp import send_interactive_list_message, InteractiveListMessage, InteractiveHeader, InteractiveBody, InteractiveFooter, InteractiveAction, InteractiveActionSection, InteractiveActionSectionRow, send_text_message, TextMessage, TextObject, send_image_message, ImageMessage, MediaObject, send_interactive_reply_buttons_message, InteractiveReplyButtonsMessage, InteractiveActionButtonReply, InteractiveActionReplyButton, send_interactive_carousel_message, InteractiveCarouselMessage, InteractiveCarousel, InteractiveCarouselCard, InteractiveCarouselCardHeader

# Setup
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)

agent_path = os.path.dirname(os.path.abspath(__file__))

# Callbacks
def before_agent_modifier(callback_context: CallbackContext) -> Optional[types.Content]:
    user_phone_number = None
    if callback_context.state.get('user_phone_number') is None:
        user_phone_number = callback_context.user_id
        if user_phone_number == "user":
            user_phone_number = os.environ.get('DEFAULT_PHONE_NUMBER') # for local testing
        callback_context.state['user_phone_number'] = user_phone_number
    else:
        user_phone_number = callback_context.state.get('user_phone_number')

    if not user_phone_number:
        logger.error("User phone number not found")
        return None

    user_email = callback_context.state.get('user_email')
    user_name = callback_context.state.get('user_name')
    if user_email is None:
        userInfo = get_user(GetUserRequest(phone_number=user_phone_number))
        if userInfo:
            callback_context.state['user_email'] = userInfo.userEmail
            callback_context.state['user_name'] = userInfo.userName
        else:
            success, _ = send_text_message(TextMessage(
                to=user_phone_number,
                text=TextObject(body="No hemos encontrado tu usuario. Por favor, regístrate en nuestra página web.")
            ))
            callback_context.state['whatsapp_message_sent'] = success
            logger.error(f"User not found: {user_phone_number}")

    return None

def simple_before_tool_modifier(tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext) -> Optional[Dict]:
    tool_context.state['last_tool_name'] = None
    tool_context.state['last_tool_result'] = None
    return None

def po_after_model_callback(callback_context: CallbackContext, llm_response: LlmResponse) -> Optional[LlmResponse]:
    """Inspects/modifies the LLM response after it's received."""
    if llm_response.content and llm_response.content.parts:
        if llm_response.content.parts[0].text:
            text_response = llm_response.content.parts[0].text
            logger.info(f"Response text: {text_response}")

            if callback_context.state.get('whatsapp_message_sent'):
                callback_context.state['whatsapp_message_sent'] = False
                return None

            user_phone_number = get_user_phone_number(callback_context)
            if not user_phone_number:
                logger.error("Cannot send text: user_phone_number not in state")
                return None

            last_tool_name = callback_context.state.get('last_tool_name')
            last_tool_result = callback_context.state.get('last_tool_result')
            
            if last_tool_name == 'get_user_orders' and last_tool_result and last_tool_result.get('orders'):
                orders = last_tool_result.get('orders')
                message = InteractiveListMessage(
                    to=user_phone_number,
                    header=InteractiveHeader(type="text", text="Órdenes de compra"),
                    body=InteractiveBody(text='Estas son tus órdenes de compra recientes.'),
                    footer=InteractiveFooter(text="Estas son tus órdenes de compra recientes."),
                    action=InteractiveAction(
                        button="Ver órdenes",
                        sections=[
                            InteractiveActionSection(
                                title="Órdenes recientes",
                                rows=[
                                    InteractiveActionSectionRow(
                                        id=order.get('orderId', ''),
                                        title=f"Orden: {order.get('orderId', '')}",
                                        description=f"Estado: {order.get('status', '')} | Fecha: {order.get('createdAt', '')[:10] if order.get('createdAt') else 'N/A'} | Items: {order.get('itemCount', 0)} | Total: ${order.get('totalAmount', 0)}",
                                    )
                                    for order in orders
                                ],
                            )
                        ],
                    ),
                )
                success, error_msg = send_interactive_list_message(message)
                if not success: logger.error(f"Cannot send orders list: {error_msg}")

            elif last_tool_name == 'get_user_items' and last_tool_result and last_tool_result.get('items'):
                items = last_tool_result.get('items')[:10]
                
                if len(items) >= 2:
                    message = InteractiveListMessage(
                        to=user_phone_number,
                        header=InteractiveHeader(type="text", text="Items de compra"),
                        body=InteractiveBody(text='Estos son los objetos que compraste recientemente.'),
                        footer=InteractiveFooter(text="Selecciona un item para ver más detalles."),
                        action=InteractiveAction(
                            button="Ver items",
                            sections=[
                                InteractiveActionSection(
                                    title="Items recientes",
                                    rows=[
                                        InteractiveActionSectionRow(
                                            id=f"{item.get('productId', '')}",
                                            title=f"{item.get('name', '')[:21]}..." if len(item.get('name', '')) > 24 else item.get('name', ''),
                                            description=f"Estado: {item.get('status', '')} | Cantidad: {item.get('quantity', 0)} | Precio: ${item.get('priceAtPurchase', 0)}"[:72],
                                        )
                                        for item in items
                                    ],
                                )
                            ],
                        ),
                    )
                success, error_msg = send_interactive_list_message(message)
                if not success: logger.error(f"Cannot send items list: {error_msg}")

            elif last_tool_name in ['get_user_item', 'identify_available_actions_for_item'] and last_tool_result and last_tool_result.get('item'):
                item = last_tool_result.get('item')
                if item.get('image'):
                    header = InteractiveHeader(type="image", image=MediaObject(link=item.get('image')))
                else:
                    header = InteractiveHeader(type="text", text="Detalles del item")
                
                button_id = f"add_feedback_{item.get('orderId')}_{item.get('productId')}" if item.get('orderId') else f"add_feedback_{item.get('productId')}"
                message = InteractiveReplyButtonsMessage(
                    to=user_phone_number,
                    header=header,
                    body=InteractiveBody(text='Este es el objeto al que haces referencia. ¿Qué deseas hacer con él?'),
                    action=InteractiveAction(
                        buttons=[
                            InteractiveActionReplyButton(
                                reply=InteractiveActionButtonReply(id=button_id, title="Agregar feedback")
                            )
                        ]
                    )
                )
                success, error_msg = send_interactive_reply_buttons_message(message)
                if not success: logger.error(f"Cannot send item reply buttons: {error_msg}")

            elif last_tool_name == 'get_user_order' and last_tool_result and last_tool_result.get('order'):
                order = last_tool_result.get('order')
                message = InteractiveReplyButtonsMessage(
                    to=user_phone_number,
                    header=InteractiveHeader(type="text", text="Detalles de la orden"),
                    body=InteractiveBody(text='¿Qué deseas hacer con esta orden?'),
                    action=InteractiveAction(
                        buttons=[
                            InteractiveActionReplyButton(
                                reply=InteractiveActionButtonReply(id=f"cancel_order_{order.get('orderId')}", title="Cancelar orden")
                            ),
                            InteractiveActionReplyButton(
                                reply=InteractiveActionButtonReply(id=f"remove_item_{order.get('orderId')}", title="Remover item")
                            )
                        ]
                    )
                )
                success, error_msg = send_interactive_reply_buttons_message(message)
                if not success: logger.error(f"Cannot send order reply buttons: {error_msg}")

            else:
                success, error_msg = send_text_message(TextMessage(to=user_phone_number, text=TextObject(body=text_response)))
                if not success:
                    logger.error(f"Cannot send text: {error_msg}")

            # Clear state after sending the message
            if last_tool_name:
                callback_context.state['last_tool_name'] = None
                callback_context.state['last_tool_result'] = None

        elif llm_response.content.parts[0].function_call:
             logger.info(f"Using tool: {llm_response.content.parts[0].function_call.name}")
        else:
            logger.warning("No text or function call found in response")
    elif llm_response.error_message:
        logger.error(f"Agent error: {llm_response.error_message}")
    else:
        logger.warning("Empty LlmResponse.")
    return None

def root_after_model_callback(callback_context: CallbackContext, llm_response: LlmResponse) -> Optional[LlmResponse]:
    user_phone_number = get_user_phone_number(callback_context)
    if llm_response.content and llm_response.content.parts:
        if llm_response.content.parts[0].text:
            text_response = llm_response.content.parts[0].text
            logger.info(f"Response text: {text_response}")
            success, error_msg = send_text_message(TextMessage(to=user_phone_number, text=TextObject(body=text_response)))
            if not success:
                logger.error(f"Cannot send text: {error_msg}")

        elif llm_response.content.parts[0].function_call:
             logger.info(f"Using tool: {llm_response.content.parts[0].function_call.name}")
        else:
            logger.warning("No text or function call found in response")
    elif llm_response.error_message:
        logger.error(f"Agent error: {llm_response.error_message}")
    else:
        logger.warning("Empty LlmResponse.")
    return None

# --- Tools ---

def get_user_email(tool_context: ToolContext) -> str:
    """Gets the user email from the tool context."""
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
    orders_dict = [order.model_dump() for order in orders] if orders else []
    tool_context.state['last_tool_name'] = 'get_user_orders'
    tool_context.state['last_tool_result'] = {"orders": orders_dict}

    if not orders:
        return {"message": "No hemos encontrado órdenes de compra para tu usuario."}
    return {"orders": orders_dict}

def get_user_items(tool_context: ToolContext) -> Dict[str, Any]:
    email = get_user_email(tool_context)
    items = get_items(GetItemsRequest(email=email))
    items_dict = [item.model_dump() for item in items] if items else []
    tool_context.state['last_tool_name'] = 'get_user_items'
    tool_context.state['last_tool_result'] = {"items": items_dict}

    if not items:
        return {"message": "No se encontraron items recientes asociados a tu cuenta."}
    return {"items": items_dict}

def identify_available_actions_for_item(product_id: str, tool_context: ToolContext) -> Dict[str, Any]:
    email = get_user_email(tool_context)
    item = get_item(GetItemRequest(email=email, product_id=product_id))
    item_dict = item.model_dump() if item else None
    tool_context.state['last_tool_name'] = 'identify_available_actions_for_item'
    tool_context.state['last_tool_result'] = {"item": item_dict}

    if not item:
        return {"message": "No se encontraron detalles del item."}
    return {"item": item_dict}

def get_user_item(product_id: str, tool_context: ToolContext) -> Dict[str, Any]:
    email = get_user_email(tool_context)
    item = get_item(GetItemRequest(email=email, product_id=product_id))
    item_dict = item.model_dump() if item else None
    tool_context.state['last_tool_name'] = 'get_user_item'
    tool_context.state['last_tool_result'] = {"item": item_dict}

    if not item:
        return {"message": "No se encontraron detalles del item."}
    return {"item": item_dict}

def get_user_order(order_id: str, tool_context: ToolContext) -> Dict[str, Any]:
    email = get_user_email(tool_context)
    order = get_order(GetOrderRequest(email=email, order_id=order_id))
    order_dict = order.model_dump() if order else None
    tool_context.state['last_tool_name'] = 'get_user_order'
    tool_context.state['last_tool_result'] = {"order": order_dict}

    if not order:
        return {"message": "No se encontraron detalles de la orden."}
    return {"order": order_dict}

def cancel_user_order(order_id: str, tool_context: ToolContext) -> Dict[str, Any]:
    email = get_user_email(tool_context)
    result = cancel_order(CancelOrderRequest(email=email, order_id=order_id))
    tool_context.state['last_tool_name'] = 'cancel_user_order'
    tool_context.state['last_tool_result'] = {"result": result}
    return result

def add_user_feedback(order_id: str, feedback: str, tool_context: ToolContext) -> Dict[str, Any]:
    email = get_user_email(tool_context)
    result = add_feedback(AddFeedbackRequest(email=email, order_id=order_id, feedback=feedback))
    tool_context.state['last_tool_name'] = 'add_user_feedback'
    tool_context.state['last_tool_result'] = {"result": result}
    return result

def remove_user_item(order_id: str, product_id: str, tool_context: ToolContext) -> Dict[str, Any]:
    email = get_user_email(tool_context)
    result = remove_item(RemoveItemRequest(email=email, order_id=order_id, product_id=product_id))
    tool_context.state['last_tool_name'] = 'remove_user_item'
    tool_context.state['last_tool_result'] = {"result": result}
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
        get_user_phone_number,
        get_user_email,
        get_user_name,
        get_user_orders,
        get_user_items,
        get_user_item,
        get_user_order,
        cancel_user_order,
        add_user_feedback,
        remove_user_item,
        identify_available_actions_for_item
    ],
    before_agent_callback=before_agent_modifier,
    before_tool_callback=simple_before_tool_modifier,
    after_model_callback=po_after_model_callback
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
    before_agent_callback=before_agent_modifier,
    after_model_callback=root_after_model_callback
)
