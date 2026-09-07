import os

from dotenv import load_dotenv
from fastapi import FastAPI
from openai import OpenAI
from pydantic import BaseModel

from chatbot.router import route_message


# ---------------------------------------------------------
# Environment Configuration
# ---------------------------------------------------------

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

ENV_FILE = os.path.join(
    BASE_DIR,
    ".env"
)

load_dotenv(ENV_FILE)

api_key = os.getenv("OPENROUTER_API_KEY")


# ---------------------------------------------------------
# OpenRouter Client
# ---------------------------------------------------------

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key
)


# ---------------------------------------------------------
# FastAPI Application
# ---------------------------------------------------------

app = FastAPI(
    title="Customer Support Chatbot API",
    description="Backend API for an AI-powered customer support system.",
    version="1.0.0"
)


# ---------------------------------------------------------
# Request Models
# ---------------------------------------------------------

class ChatRequest(BaseModel):
    message: str


# ---------------------------------------------------------
# Health / Home Endpoint
# ---------------------------------------------------------

@app.get("/")
def home():
    return {
        "message": "Customer Support Chatbot API is running",
        "status": "healthy"
    }


# ---------------------------------------------------------
# Chat Endpoint
# ---------------------------------------------------------

@app.post("/chat")
def chat(request: ChatRequest):

    message = request.message.strip()

    # Basic validation.
    if not message:
        return {
            "error": "Message cannot be empty."
        }

    # -----------------------------------------------------
    # Route the customer's request
    # -----------------------------------------------------

    routing_result = route_message(message)

    intent = routing_result["intent"]

    # -----------------------------------------------------
    # Business Logic: Order Status
    # -----------------------------------------------------

    if intent == "ORDER_STATUS":

        # If the router found an error, return it directly.
        if "error" in routing_result:
            return routing_result

        order = routing_result.get("data")

        return {
            "user_message": message,
            "intent": intent,
            "source": "database",
            "response": (
                f"Your order #{order['order_id']} "
                f"for {order['product']} is currently "
                f"{order['status'].lower()}."
            ),
            "order": order
        }

    # -----------------------------------------------------
    # Other intents → AI Assistant
    # -----------------------------------------------------

    response = client.chat.completions.create(
        model="openrouter/free",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a helpful customer support assistant. "
                    "Give clear, concise and professional answers. "
                    "Do not invent order information, customer information, "
                    "refund status, or other business data. "
                    "If the system has not provided the required information, "
                    "ask the customer for the necessary details."
                )
            },
            {
                "role": "user",
                "content": message
            }
        ]
    )

    reply = response.choices[0].message.content

    return {
        "user_message": message,
        "intent": intent,
        "action": routing_result.get("action"),
        "source": "ai",
        "bot_reply": reply
    }
