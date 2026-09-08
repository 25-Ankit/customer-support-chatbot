from __future__ import annotations

import hashlib
import re
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Final


# =========================================================
# Response Policy
# =========================================================
#
# The policy layer decides how a request should be handled
# BEFORE expensive AI inference is performed.
#
# Main goals:
#
#   1. Avoid unnecessary LLM calls
#   2. Prevent repeated-message abuse
#   3. Limit excessive requests
#   4. Protect the application from AI-cost abuse
#   5. Keep business operations deterministic
#
# NOTE:
# This currently uses in-memory state.
# Later we will move rate limiting to Redis so it works
# correctly across multiple ECS instances.
# =========================================================


# =========================================================
# Policy Actions
# =========================================================

POLICY_BUSINESS: Final[str] = "BUSINESS"
POLICY_FAQ: Final[str] = "FAQ"
POLICY_FIXED: Final[str] = "FIXED"
POLICY_AI: Final[str] = "AI"


# =========================================================
# Rate-Limit Configuration
# =========================================================

# Maximum general requests allowed during the window.
MAX_REQUESTS_PER_WINDOW: Final[int] = 60

# Time window in seconds.
REQUEST_WINDOW_SECONDS: Final[int] = 60


# Maximum identical messages allowed during the window.
MAX_IDENTICAL_MESSAGES: Final[int] = 5

# AI requests get a stricter limit because they cost money.
MAX_AI_REQUESTS_PER_WINDOW: Final[int] = 10


# =========================================================
# Intent → Policy Mapping
# =========================================================

INTENT_POLICIES: Final[dict[str, str]] = {

    # -----------------------------------------------------
    # Deterministic business operations
    # -----------------------------------------------------

    "ORDER_STATUS": POLICY_BUSINESS,
    "CANCEL_ORDER": POLICY_BUSINESS,
    "REFUND_REQUEST": POLICY_BUSINESS,
    "PRODUCT_INFO": POLICY_BUSINESS,
    "CREATE_TICKET": POLICY_BUSINESS,
    "ACCOUNT_HELP": POLICY_BUSINESS,
    "HUMAN_SUPPORT": POLICY_BUSINESS,

    # -----------------------------------------------------
    # Cheap local responses
    # -----------------------------------------------------

    "GREETING": POLICY_FIXED,

    # Unknown requests are NOT automatically sent to AI.
    "UNKNOWN": POLICY_FIXED,
}


# =========================================================
# Fixed Responses
# =========================================================

FIXED_RESPONSES: Final[dict[str, str]] = {

    "GREETING": (
        "Hello! Welcome to customer support. "
        "How can I help you today?"
    ),

    "UNKNOWN": (
        "I can help with orders, cancellations, refunds, "
        "products, account support, and other customer "
        "support requests."
    ),

    "RATE_LIMITED": (
        "You're sending requests too quickly. "
        "Please wait a moment before trying again."
    ),

    "REPEATED_MESSAGE": (
        "It looks like you're repeatedly sending the same "
        "message. Please provide additional information "
        "so I can help you."
    ),

    "AI_LIMITED": (
        "You've reached the temporary limit for complex "
        "support requests. Please try again later or "
        "contact human support."
    ),
}


# =========================================================
# Request Tracking
# =========================================================

@dataclass
class RequestRecord:
    """
    Represents a single request made by a user.
    """

    timestamp: float
    message_hash: str


# user_id → recent requests
_REQUEST_HISTORY: dict[str, deque[RequestRecord]] = defaultdict(
    deque
)


# =========================================================
# AI Request Tracking
# =========================================================

# user_id → timestamps of recent AI requests
_AI_REQUEST_HISTORY: dict[str, deque[float]] = defaultdict(
    deque
)


# =========================================================
# Message Normalization
# =========================================================

def normalize_message(message: str) -> str:
    """
    Normalize a message before comparing it with previous
    messages.

    This prevents simple variations such as:

        "Cancel order #3"
        " cancel   order #3 "
        "CANCEL ORDER #3"

    from bypassing duplicate detection.
    """

    if not isinstance(message, str):
        return ""

    message = message.lower().strip()

    # Collapse repeated whitespace.
    message = re.sub(r"\s+", " ", message)

    return message


# =========================================================
# Message Fingerprint
# =========================================================

def get_message_hash(message: str) -> str:
    """
    Create a stable SHA-256 fingerprint for a message.

    We store the hash rather than the original message in
    the abuse-tracking structure.
    """

    normalized = normalize_message(message)

    return hashlib.sha256(
        normalized.encode("utf-8")
    ).hexdigest()


# =========================================================
# Remove Expired Requests
# =========================================================

def _cleanup_requests(
    user_id: str,
    current_time: float,
) -> None:
    """
    Remove requests outside the current rate-limit window.
    """

    history = _REQUEST_HISTORY[user_id]

    cutoff = current_time - REQUEST_WINDOW_SECONDS

    while history and history[0].timestamp < cutoff:
        history.popleft()


# =========================================================
# Remove Expired AI Requests
# =========================================================

def _cleanup_ai_requests(
    user_id: str,
    current_time: float,
) -> None:
    """
    Remove expired AI request timestamps.
    """

    history = _AI_REQUEST_HISTORY[user_id]

    cutoff = current_time - REQUEST_WINDOW_SECONDS

    while history and history[0] < cutoff:
        history.popleft()


# =========================================================
# General Request Rate Limit
# =========================================================

def is_request_rate_limited(
    user_id: str,
    current_time: float | None = None,
) -> bool:
    """
    Determine whether a user has exceeded the general
    request limit.
    """

    if current_time is None:
        current_time = time.time()

    _cleanup_requests(
        user_id,
        current_time,
    )

    return len(_REQUEST_HISTORY[user_id]) >= (
        MAX_REQUESTS_PER_WINDOW
    )


# =========================================================
# Repeated Message Detection
# =========================================================

def is_repeated_message(
    user_id: str,
    message: str,
    current_time: float | None = None,
) -> bool:
    """
    Determine whether the user has sent the same message
    too many times within the current window.
    """

    if current_time is None:
        current_time = time.time()

    _cleanup_requests(
        user_id,
        current_time,
    )

    message_hash = get_message_hash(message)

    identical_count = sum(
        1
        for request in _REQUEST_HISTORY[user_id]
        if request.message_hash == message_hash
    )

    return identical_count >= MAX_IDENTICAL_MESSAGES


# =========================================================
# AI Request Limit
# =========================================================

def is_ai_rate_limited(
    user_id: str,
    current_time: float | None = None,
) -> bool:
    """
    Determine whether the user has exceeded the stricter
    AI request limit.
    """

    if current_time is None:
        current_time = time.time()

    _cleanup_ai_requests(
        user_id,
        current_time,
    )

    return len(_AI_REQUEST_HISTORY[user_id]) >= (
        MAX_AI_REQUESTS_PER_WINDOW
    )


# =========================================================
# Record Request
# =========================================================

def record_request(
    user_id: str,
    message: str,
    current_time: float | None = None,
) -> None:
    """
    Record a request after it passes validation.
    """

    if current_time is None:
        current_time = time.time()

    _cleanup_requests(
        user_id,
        current_time,
    )

    _REQUEST_HISTORY[user_id].append(
        RequestRecord(
            timestamp=current_time,
            message_hash=get_message_hash(message),
        )
    )


# =========================================================
# Record AI Request
# =========================================================

def record_ai_request(
    user_id: str,
    current_time: float | None = None,
) -> None:
    """
    Record an AI request for cost-control purposes.
    """

    if current_time is None:
        current_time = time.time()

    _cleanup_ai_requests(
        user_id,
        current_time,
    )

    _AI_REQUEST_HISTORY[user_id].append(
        current_time
    )


# =========================================================
# Get Policy
# =========================================================

def get_policy(intent: str) -> str:
    """
    Return the handling policy for an intent.

    Unknown intents are intentionally handled as FIXED.
    """

    return INTENT_POLICIES.get(
        intent,
        POLICY_FIXED,
    )


# =========================================================
# Get Fixed Response
# =========================================================

def get_fixed_response(
    intent: str,
) -> str | None:
    """
    Return a predefined response for an intent.
    """

    return FIXED_RESPONSES.get(intent)


# =========================================================
# Get Security Response
# =========================================================

def get_security_response(
    reason: str,
) -> str:
    """
    Return a safe response when a request is blocked by
    abuse or cost-control rules.
    """

    return FIXED_RESPONSES.get(
        reason,
        FIXED_RESPONSES["RATE_LIMITED"],
    )


# =========================================================
# Reset User Tracking
# =========================================================

def reset_user_tracking(user_id: str) -> None:
    """
    Clear rate-limit state for a user.

    Mainly useful for tests and administrative operations.
    """

    _REQUEST_HISTORY.pop(
        user_id,
        None,
    )

    _AI_REQUEST_HISTORY.pop(
        user_id,
        None,
    )
