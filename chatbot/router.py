from typing import Any

from chatbot.intent import detect_intent, extract_order_id
from backend.services.order_service import (
    get_order_status,
    OrderServiceError,
)


# ---------------------------------------------------------
# Intent → Action Mapping
# ---------------------------------------------------------

INTENT_ACTIONS = {
    "CANCEL_ORDER": "cancel_order",
    "REFUND_REQUEST": "create_refund_request",
    "PRODUCT_INFO": "get_product_info",
    "CREATE_TICKET": "create_support_ticket",
    "HUMAN_SUPPORT": "handoff_to_human",
    "ACCOUNT_HELP": "handle_account_help",
    "GREETING": "handle_greeting",
    "UNKNOWN": "handle_unknown",
}


# ---------------------------------------------------------
# Response Helpers
# ---------------------------------------------------------

def build_response(
    message: str,
    intent: str,
    action: str | None = None,
    data: Any = None,
    error: str | None = None,
) -> dict:
    """
    Build a consistent response structure for the router.
    """

    response = {
        "message": message,
        "intent": intent,
    }

    if action is not None:
        response["action"] = action

    if data is not None:
        response["data"] = data

    if error is not None:
        response["error"] = error

    return response


# ---------------------------------------------------------
# Order Status Handler
# ---------------------------------------------------------

def handle_order_status(message: str) -> dict:
    """
    Handle an order-status request.

    Extracts the order ID, queries the order service,
    and returns the result.
    """

    order_id = extract_order_id(message)

    if order_id is None:
        return build_response(
            message=message,
            intent="ORDER_STATUS",
            error="Please provide your order ID.",
        )

    try:

        order = get_order_status(order_id)

    except OrderServiceError:
        return build_response(
            message=message,
            intent="ORDER_STATUS",
            error="Unable to retrieve order information right now.",
        )

    if order is None:
        return build_response(
            message=message,
            intent="ORDER_STATUS",
            error=f"Order {order_id} was not found.",
        )

    return build_response(
        message=message,
        intent="ORDER_STATUS",
        action="get_order_status",
        data=order,
    )


# ---------------------------------------------------------
# Main Router
# ---------------------------------------------------------

def route_message(message: str) -> dict:
    """
    Detect the customer's intent and route the request
    to the appropriate application operation.
    """

    # Basic input validation.
    if not isinstance(message, str):

        return build_response(
            message=str(message),
            intent="UNKNOWN",
            action="handle_unknown",
            error="Message must be a string.",
        )

    message = message.strip()

    if not message:

        return build_response(
            message="",
            intent="UNKNOWN",
            action="handle_unknown",
            error="Message cannot be empty.",
        )

    # Detect customer's intent.
    intent = detect_intent(message)

    # Order status requires special processing because
    # it needs an order ID and database lookup.
    if intent == "ORDER_STATUS":
        return handle_order_status(message)

    # All other currently supported intents use the
    # central action mapping.
    action = INTENT_ACTIONS.get(
        intent,
        "handle_unknown",
    )

    return build_response(
        message=message,
        intent=intent,
        action=action,
    ) 
