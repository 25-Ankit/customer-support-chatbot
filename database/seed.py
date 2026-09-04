import sqlite3

DATABASE = "database/customer_support.db"

connection = sqlite3.connect(DATABASE)
cursor = connection.cursor()

customers = [
    ("Rahul Sharma", "rahul@example.com"),
    ("Priya Patel", "priya@example.com"),
    ("Amit Kumar", "amit@example.com"),
]

cursor.executemany(
    "INSERT INTO customers (name, email) VALUES (?, ?)",
    customers
)

orders = [
    (1, "Laptop", "Shipped"),
    (1, "Wireless Mouse", "Delivered"),
    (2, "Headphones", "Processing"),
    (3, "Keyboard", "Cancelled"),
]

cursor.executemany(
    "INSERT INTO orders (customer_id, product, status) VALUES (?, ?, ?)",
    orders
)

connection.commit()
connection.close()

print("Sample customers and orders added successfully.")
