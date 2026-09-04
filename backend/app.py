import os
import sqlite3

from dotenv import load_dotenv
from fastapi import FastAPI
from openai import OpenAI
from pydantic import BaseModel

load_dotenv("../.env")

api_key = os.getenv("OPENROUTER_API_KEY")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key
)

DATABASE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "database",
    "customer_support.db"
)

app = FastAPI()


class ChatRequest(BaseModel):
    message: str


@app.get("/")
def home():
    return {
        "message": "Customer Support Chatbot API is running"
    }

@app.get("/orders/{order_id}")
def get_order(order_id: int):

    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row

    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            orders.id AS order_id,
            customers.name AS customer_name,
            orders.product,
            orders.status
        FROM orders
        JOIN customers
            ON orders.customer_id = customers.id
        WHERE orders.id = ?
    """, (order_id,))

    order = cursor.fetchone()

    connection.close()

    if order is None:
        return {
            "error": "Order not found"
        }

    return dict(order)


@app.post("/chat")
def chat(request: ChatRequest):

    response = client.chat.completions.create(
        model="openrouter/free",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a helpful customer support assistant. "
                    "Give clear and concise answers."
                )
            },
            {
                "role": "user",
                "content": request.message
            }
        ]
    )

    reply = response.choices[0].message.content

    return {
        "user_message": request.message,
        "bot_reply": reply
    }
