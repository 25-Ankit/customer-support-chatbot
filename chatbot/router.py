from chatbot.intent import detect_intent


INTENT_ACTIONS = {
    "ORDER_STATUS": "get_order_status",
    "CANCEL_ORDER": "cancel_order",
    "REFUND_REQUEST": "create_refund_request",
    "PRODUCT_INFO": "get_product_info",
    "CREATE_TICKET": "create_support_ticket",
    "HUMAN_SUPPORT": "handoff_to_human",
    "ACCOUNT_HELP": "handle_account_help",
    "GREETING": "handle_greeting",
    "UNKNOWN": "handle_unknown",
}


def route_message(message):
    """Detect the customer's intent and return the corresponding action."""

    intent = detect_intent(message)

    action = INTENT_ACTIONS.get(
        intent,
        "handle_unknown"
    )

    return {
        "message": message,
        "intent": intent,
        "action": action,
    }
