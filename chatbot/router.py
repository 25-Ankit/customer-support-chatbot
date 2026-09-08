from typing import Any

from chatbot.intent import detect_intent, extract_order_id
from backend.services.order_service import (
    get_order_status,
    cancel_order,
    OrderServiceError,
)


# =========================================================
# Intent → Action Mapping
# =========================================================

INTENT_ACTIONS: dict[str, str] = {
    "CANCEL_ORDER": "cancel_order",
    "REFUND_REQUEST": "create_refund_request",
    "PRODUCT_INFO": "get_product_info",
    "CREATE_TICKET": "create_support_ticket",
    "HUMAN_SUPPORT": "handoff_to_human",
    "ACCOUNT_HELP": "handle_account_help",
    "GREETING": "handle_greeting",
    "UNKNOWN": "handle_unknown",
}


# =========================================================
# Response Builder
# =========================================================

def build_response(
    message: str,
    intent: str,
    action: str | None = None,
    data: Any = None,
    error: str | None = None,
) -> dict:
    """
    Build a consistent response object.

    Keeping response construction in one place makes the
    router easier to maintain and keeps API responses
    predictable.
    """

    response: dict[str, Any] = {
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


# =========================================================
# Order Status Handler
# =========================================================

def handle_order_status(message: str) -> dict:
    """
    Handle an order-status request.

    Flow:

        User message
             ↓
        Extract order ID
             ↓
        Order service
             ↓
        Database
             ↓
        Response
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
            action="get_order_status",
            error="Unable to retrieve order information right now.",
        )

    if order is None:
        return build_response(
            message=message,
            intent="ORDER_STATUS",
            action="get_order_status",
            error=f"Order {order_id} was not found.",
        )

    return build_response(
        message=message,
        intent="ORDER_STATUS",
        action="get_order_status",
        data=order,
    )


# =========================================================
# Order Cancellation Handler
# =========================================================

def handle_order_cancellation(message: str) -> dict:
    """
    Handle a customer request to cancel an order.

    Flow:

        User message
             ↓
        Extract order ID
             ↓
        Cancellation business logic
             ↓
        Database update
             ↓
        Response
    """

    order_id = extract_order_id(message)

    if order_id is None:
        return build_response(
            message=message,
            intent="CANCEL_ORDER",
            action="cancel_order",
            error="Please provide your order ID.",
        )

    try:
        result = cancel_order(order_id)

    except OrderServiceError as error:
        return build_response(
            message=message,
            intent="CANCEL_ORDER",
            action="cancel_order",
            error=str(error),
        )

    return build_response(
        message=message,
        intent="CANCEL_ORDER",
        action="cancel_order",
        data=result,
    )


# =========================================================
# Main Message Router
# =========================================================

def route_message(message: str) -> dict:
    """
    Detect the customer's intent and route the request
    to the appropriate business operation.

    Routing pipeline:

        Input
          ↓
        Validation
          ↓
        Intent Detection
          ↓
        Specialized Handler
          ↓
        Business Service
          ↓
        Response
    """

    # -----------------------------------------------------
    # Input validation
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # Intent detection
    # -----------------------------------------------------

    intent = detect_intent(message)

    # -----------------------------------------------------
    # Specialized business operations
    # -----------------------------------------------------

    if intent == "ORDER_STATUS":
        return handle_order_status(message)

    if intent == "CANCEL_ORDER":
        return handle_order_cancellation(message)

    # -----------------------------------------------------
    # Generic intent → action routing
    # -----------------------------------------------------

    action = INTENT_ACTIONS.get(
        intent,
        "handle_unknown",
    )

    return build_response(
        message=message,
        intent=intent,
        action=action,
    )
