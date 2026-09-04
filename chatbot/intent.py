def detect_intent(message):
    message = message.lower()

    if "where" in message and "order" in message:
        return "ORDER_STATUS"

    if "cancel" in message and "order" in message:
        return "CANCEL_ORDER"

    if "refund" in message:
        return "REFUND_REQUEST"

    if "product" in message:
        return "PRODUCT_INFO"

    if "human" in message or "agent" in message:
        return "HUMAN_SUPPORT"

    return "UNKNOWN"
