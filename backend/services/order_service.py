import logging
import os
import sqlite3
from typing import Optional


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

DATABASE = os.path.join(
    os.path.dirname(
        os.path.dirname(
            os.path.dirname(
                os.path.abspath(__file__)
            )
        )
    ),
    "database",
    "customer_support.db"
)


# ---------------------------------------------------------
# Logging
# ---------------------------------------------------------

logger = logging.getLogger(__name__)


# ---------------------------------------------------------
# Custom Exceptions
# ---------------------------------------------------------

class OrderServiceError(Exception):
    """Base exception for order-service errors."""


class InvalidOrderIDError(OrderServiceError):
    """Raised when an invalid order ID is provided."""


class OrderNotFoundError(OrderServiceError):
    """Raised when an order does not exist."""


class DatabaseError(OrderServiceError):
    """Raised when a database operation fails."""


# ---------------------------------------------------------
# Database Connection
# ---------------------------------------------------------

def get_database_connection():
    """
    Create and return a SQLite database connection.

    The connection uses sqlite3.Row so database
    columns can be accessed by name.
    """

    try:
        connection = sqlite3.connect(
            DATABASE,
            timeout=10
        )

        connection.row_factory = sqlite3.Row

        return connection

    except sqlite3.Error as error:

        logger.error(
            "Failed to connect to database: %s",
            error
        )

        raise DatabaseError(
            "Unable to connect to the database."
        ) from error


# ---------------------------------------------------------
# Order Validation
# ---------------------------------------------------------

def validate_order_id(order_id: int) -> None:
    """
    Validate the order ID before querying the database.
    """

    if not isinstance(order_id, int):
        raise InvalidOrderIDError(
            "Order ID must be an integer."
        )

    if order_id <= 0:
        raise InvalidOrderIDError(
            "Order ID must be greater than zero."
        )


# ---------------------------------------------------------
# Get Order
# ---------------------------------------------------------

def get_order_status(order_id: int) -> Optional[dict]:
    """
    Fetch complete order information from the database.

    Returns:
        Dictionary containing order information,
        or None if the order does not exist.
    """

    validate_order_id(order_id)

    connection = None

    try:

        connection = get_database_connection()

        cursor = connection.cursor()

        query = """
            SELECT
                orders.id AS order_id,
                customers.id AS customer_id,
                customers.name AS customer_name,
                customers.email AS customer_email,
                orders.product,
                orders.status
            FROM orders
            JOIN customers
                ON orders.customer_id = customers.id
            WHERE orders.id = ?
        """

        cursor.execute(
            query,
            (order_id,)
        )

        order = cursor.fetchone()

        if order is None:

            logger.info(
                "Order not found: %s",
                order_id
            )

            return None

        result = {
            "order_id": order["order_id"],
            "customer_id": order["customer_id"],
            "customer_name": order["customer_name"],
            "customer_email": order["customer_email"],
            "product": order["product"],
            "status": order["status"],
        }

        logger.info(
            "Order retrieved successfully: %s",
            order_id
        )

        return result

    except sqlite3.Error as error:

        logger.error(
            "Database error while retrieving order %s: %s",
            order_id,
            error
        )

        raise DatabaseError(
            "Unable to retrieve order information."
        ) from error

    finally:

        if connection is not None:
            connection.close()


# ---------------------------------------------------------
# Check Whether Order Exists
# ---------------------------------------------------------

def order_exists(order_id: int) -> bool:
    """
    Check whether an order exists in the database.
    """

    validate_order_id(order_id)

    connection = None

    try:

        connection = get_database_connection()

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT 1
            FROM orders
            WHERE id = ?
            LIMIT 1
            """,
            (order_id,)
        )

        result = cursor.fetchone()

        return result is not None

    except sqlite3.Error as error:

        logger.error(
            "Database error while checking order %s: %s",
            order_id,
            error
        )

        raise DatabaseError(
            "Unable to check order."
        ) from error

    finally:

        if connection is not None:
            connection.close()


# ---------------------------------------------------------
# Get Order Status Only
# ---------------------------------------------------------

def get_status(order_id: int) -> Optional[str]:
    """
    Return only the current status of an order.
    """

    order = get_order_status(order_id)

    if order is None:
        return None

    return order["status"]


# ---------------------------------------------------------
# Check Cancellation Eligibility
# ---------------------------------------------------------

def can_cancel_order(order_id: int) -> bool:
    """
    Determine whether an order can currently be cancelled.

    Orders that are already shipped, delivered,
    or cancelled cannot be cancelled.
    """

    order = get_order_status(order_id)

    if order is None:
        return False

    status = order["status"].lower()

    cancellable_statuses = {
        "processing",
        "pending"
    }

    return status in cancellable_statuses

# =========================================================
# CANCEL ORDER
# =========================================================

def cancel_order(order_id: int) -> dict:
    """
    Cancel an order if its current status allows cancellation.

    Only orders with a status of 'Processing' or 'Pending'
    can be cancelled.

    Args:
        order_id: ID of the order to cancel.

    Returns:
        Dictionary containing the updated order information.

    Raises:
        InvalidOrderIDError: If the order ID is invalid.
        OrderNotFoundError: If the order does not exist.
        OrderServiceError: If the order cannot be cancelled.
        DatabaseError: If the database operation fails.
    """

    validate_order_id(order_id)

    connection = None

    try:
        connection = get_database_connection()

        cursor = connection.cursor()

        # First retrieve the order.
        cursor.execute(
            """
            SELECT
                orders.id AS order_id,
                orders.product,
                orders.status
            FROM orders
            WHERE orders.id = ?
            """,
            (order_id,)
        )

        order = cursor.fetchone()

        if order is None:
            raise OrderNotFoundError(
                f"Order {order_id} was not found."
            )

        current_status = order["status"].strip().lower()

        # Only these statuses can be cancelled.
        cancellable_statuses = {
            "processing",
            "pending",
        }

        if current_status not in cancellable_statuses:
            raise OrderServiceError(
                f"Order {order_id} cannot be cancelled "
                f"because its current status is "
                f"'{order['status']}'."
            )

        # Perform the actual database update.
        cursor.execute(
            """
            UPDATE orders
            SET status = ?
            WHERE id = ?
            """,
            ("Cancelled", order_id)
        )

        connection.commit()

        logger.info(
            "Order %s successfully cancelled.",
            order_id
        )

        return {
            "order_id": order_id,
            "product": order["product"],
            "previous_status": order["status"],
            "status": "Cancelled",
        }

    except (OrderNotFoundError, OrderServiceError):
        if connection is not None:
            connection.rollback()
        raise

    except sqlite3.Error as error:

        if connection is not None:
            connection.rollback()

        logger.error(
            "Database error while cancelling order %s: %s",
            order_id,
            error
        )

        raise DatabaseError(
            "Unable to cancel the order right now."
        ) from error

    finally:

        if connection is not None:
            connection.close()
