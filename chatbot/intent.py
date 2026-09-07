import re


INTENT_PATTERNS = {
    "ORDER_STATUS": {
        "keywords": [
            "order", "package", "parcel", "shipment",
            "delivery", "tracking", "tracking number", "tracking id"
        ],
        "phrases": [
            "where is my order",
            "where is my package",
            "where is my parcel",
            "where is my delivery",
            "track my order",
            "track my package",
            "track my parcel",
            "track my shipment",
            "check my order status",
            "check order status",
            "what is my order status",
            "has my order shipped",
            "has my package shipped",
            "when will my order arrive",
            "when will my package arrive",
            "when will my delivery arrive",
            "is my order on the way",
            "is my package on the way",
            "order has not arrived",
            "package has not arrived",
            "delivery has not arrived"
        ],
    },

    "CANCEL_ORDER": {
        "keywords": [
            "cancel", "cancellation", "stop", "terminate"
        ],
        "phrases": [
            "cancel my order",
            "cancel an order",
            "i want to cancel",
            "i need to cancel",
            "please cancel",
            "cancel my purchase",
            "stop my order",
            "stop the order",
            "can i cancel my order",
            "how do i cancel my order"
        ],
    },

    "REFUND_REQUEST": {
        "keywords": [
            "refund", "refunded", "reimbursement",
            "money back", "cash back"
        ],
        "phrases": [
            "i want a refund",
            "i need a refund",
            "request a refund",
            "request refund",
            "get my money back",
            "i want my money back",
            "give me my money back",
            "when will i get my refund",
            "where is my refund",
            "refund my order",
            "how can i get a refund",
            "can i get a refund"
        ],
    },

    "PRODUCT_INFO": {
        "keywords": [
            "product", "item", "price", "cost", "stock",
            "available", "availability", "feature", "features",
            "specification", "specifications", "size",
            "color", "colour", "model", "warranty"
        ],
        "phrases": [
            "tell me about this product",
            "tell me about the product",
            "what is the price",
            "how much does it cost",
            "is this product available",
            "is this item available",
            "is it in stock",
            "do you have this in stock",
            "what are the features",
            "what are the specifications",
            "what is the warranty",
            "product details",
            "item details"
        ],
    },

    "CREATE_TICKET": {
        "keywords": [
            "ticket", "complaint", "issue", "problem",
            "broken", "damaged", "defective", "complain"
        ],
        "phrases": [
            "create a ticket",
            "open a ticket",
            "raise a ticket",
            "create support ticket",
            "open support ticket",
            "i have a problem",
            "i have an issue",
            "i want to complain",
            "my product is damaged",
            "my product is broken",
            "my product is defective",
            "item arrived damaged",
            "item is not working"
        ],
    },

    "HUMAN_SUPPORT": {
        "keywords": [
            "human", "agent", "representative",
            "operator", "person", "staff", "employee"
        ],
        "phrases": [
            "talk to a human",
            "speak to a human",
            "speak to an agent",
            "talk to an agent",
            "connect me to an agent",
            "connect me with support",
            "i need human support",
            "i want human support",
            "talk to customer support",
            "speak with customer support",
            "real person"
        ],
    },

    "ACCOUNT_HELP": {
        "keywords": [
            "account", "password", "email", "profile",
            "login", "log in", "logout", "log out", "username"
        ],
        "phrases": [
            "forgot my password",
            "reset my password",
            "change my password",
            "change my email",
            "update my profile",
            "cannot login",
            "cannot log in",
            "can't login",
            "can't log in",
            "account problem",
            "account issue",
            "help with my account",
            "delete my account"
        ],
    },

    "GREETING": {
        "keywords": [
            "hello", "hi", "hey", "hii",
            "good morning", "good afternoon", "good evening"
        ],
        "phrases": [
            "hello there",
            "hi there",
            "hey there",
            "how are you",
            "good morning",
            "good afternoon",
            "good evening"
        ],
    },
}


def normalize_message(message):
    """Clean and normalize the customer's message."""

    message = message.lower().strip()
    message = re.sub(r"[^a-z0-9\s]", " ", message)
    message = re.sub(r"\s+", " ", message)

    return message


def extract_order_id(message):
    """Extract an order ID from the customer's message."""

    patterns = [
        r"order\s*#?\s*(\d+)",
        r"order\s+number\s+(\d+)",
        r"order\s+id\s*[:#]?\s*(\d+)",
        r"tracking\s+id\s*[:#]?\s*(\d+)",
        r"tracking\s+number\s*[:#]?\s*(\d+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)

        if match:
            return int(match.group(1))

    return None


def calculate_scores(message):
    """Calculate a score for every possible intent."""

    scores = {}
    words = message.split()

    for intent, patterns in INTENT_PATTERNS.items():

        score = 0

        # Phrases are stronger signals than individual keywords.
        for phrase in patterns["phrases"]:
            if phrase in message:
                score += 3

        # Keywords provide additional signals.
        for keyword in patterns["keywords"]:
            if keyword in words:
                score += 1
            elif " " in keyword and keyword in message:
                score += 1

        scores[intent] = score

    # Strong cancellation signal.
    if (
        any(word in message for word in ["cancel", "cancellation"])
        and any(word in message for word in ["order", "purchase"])
    ):
        scores["CANCEL_ORDER"] += 5

    # Strong order-status signal.
    if (
        any(word in words for word in [
            "where", "track", "tracking",
            "status", "shipped", "arrive", "arrived"
        ])
        and any(word in words for word in [
            "order", "package", "parcel",
            "shipment", "delivery"
        ])
    ):
        scores["ORDER_STATUS"] += 5

    return scores


def detect_intent(message):
    """Return the most likely customer-support intent."""

    message = normalize_message(message)

    if not message:
        return "UNKNOWN"

    scores = calculate_scores(message)
    best_intent = max(scores, key=scores.get)

    if scores[best_intent] == 0:
        return "UNKNOWN"

    return best_intent


def detect_intent_details(message):
    """Return intent, score and extracted order ID."""

    normalized_message = normalize_message(message)

    if not normalized_message:
        return {
            "intent": "UNKNOWN",
            "score": 0,
            "order_id": None,
        }

    scores = calculate_scores(normalized_message)

    best_intent = max(scores, key=scores.get)
    best_score = scores[best_intent]

    if best_score == 0:
        best_intent = "UNKNOWN"

    return {
        "intent": best_intent,
        "score": best_score,
        "order_id": extract_order_id(normalized_message),
    }
