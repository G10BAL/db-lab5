from typing import Optional, List, Dict, Any, Tuple
from database import BaseRepository
from decimal import Decimal
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class OrderStatus:
    """State constants"""
    PENDING = 'pending'
    CONFIRMED = 'confirmed'
    PROCESSING = 'processing'
    SHIPPED = 'shipped'
    DELIVERED = 'delivered'
    CANCELLED = 'cancelled'
    
    ALL_STATUSES = [PENDING, CONFIRMED, PROCESSING, SHIPPED, DELIVERED, CANCELLED]


class PaymentStatus:
    """State constants for payment status"""
    PENDING = 'pending'
    PAID = 'paid'
    REFUNDED = 'refunded'
    FAILED = 'failed'
    
    ALL_STATUSES = [PENDING, PAID, REFUNDED, FAILED]


class OrderRepository(BaseRepository):
    @staticmethod
    def create_order(user_id: int, shipping_address: str,
                    items: List[Dict[str, Any]],
                    billing_address: Optional[str] = None,
                    payment_method: str = 'cash',
                    notes: Optional[str] = None) -> Optional[int]:
        """
        New order transaction
        
        Args:
            user_id: ID 
            shipping_address: 
            items: list [{product_id, quantity, discount_percent}]
            billing_address: 
            payment_method: 
            notes: 
            
        Returns:
            Created order ID
            
        Raises:
            ValueError: If product is not available
        """
        # Use transaction
        with BaseRepository.transaction() as (conn, cursor):
            try:
                # 1. Create order
                order_query = """
                    INSERT INTO orders 
                    (user_id, shipping_address, billing_address, payment_method, notes)
                    VALUES (?, ?, ?, ?, ?)
                """
                
                cursor.execute(
                    order_query,
                    (user_id, shipping_address, billing_address or shipping_address, 
                     payment_method, notes)
                )
                order_id = cursor.lastrowid
                logger.info(f"Order {order_id} created for user {user_id}")
                
                # 2. Adding order items
                for item in items:
                    product_id = item['product_id']
                    quantity = item['quantity']
                    discount_percent = item.get('discount_percent', 0)
                    
                    # Check the availability of the product
                    stock_query = "SELECT stock_quantity, unit_price FROM products WHERE product_id = ?"
                    cursor.execute(stock_query, (product_id,))
                    product = cursor.fetchone()
                    
                    if not product:
                        raise ValueError(f"Product {product_id} not found")
                    
                    current_stock = product[0] if not cursor.description else product['stock_quantity']
                    unit_price = product[1] if not cursor.description else product['unit_price']
                    
                    if current_stock < quantity:
                        raise ValueError(
                            f"Insufficient stock for product {product_id}. "
                            f"Available: {current_stock}, Requested: {quantity}"
                        )
                    
                    # Add item to order
                    item_query = """
                        INSERT INTO order_items 
                        (order_id, product_id, quantity, unit_price, discount_percent)
                        VALUES (?, ?, ?, ?, ?)
                    """
                    cursor.execute(
                        item_query,
                        (order_id, product_id, quantity, unit_price, discount_percent)
                    )
                    
                    # Decrease stock quantity
                    update_stock_query = """
                        UPDATE products 
                        SET stock_quantity = stock_quantity - ?
                        WHERE product_id = ?
                    """
                    cursor.execute(update_stock_query, (quantity, product_id))
                    
                    # Create stock movement record
                    movement_query = """
                        INSERT INTO stock_movements 
                        (product_id, movement_type, quantity, reference_type, reference_id, user_id)
                        VALUES (?, 'out', ?, 'sale', ?, ?)
                    """
                    cursor.execute(movement_query, (-quantity, product_id, order_id, user_id))
                    
                    logger.debug(f"Added item: Product {product_id}, Quantity {quantity}")
                
                logger.info(f"Order {order_id} completed with {len(items)} items")
                return order_id
                
            except Exception as e:
                logger.error(f"Error creating order: {e}")
                raise
    
    @staticmethod
    def get_order_by_id(order_id: int, include_items: bool = True) -> Optional[Dict[str, Any]]:
        """
        Get order by ID

        Args:
            order_id: Order ID
            include_items: Include order items

        Returns:
            Order data with items (if include_items=True)
        """
        # Fetch main order information
        query = """
            SELECT o.*, 
                   u.username, u.full_name, u.email, u.phone,
                   m.username as manager_username
            FROM orders o
            JOIN users u ON o.user_id = u.user_id
            LEFT JOIN users m ON o.processed_by = m.user_id
            WHERE o.order_id = ?
        """
        
        order = BaseRepository.execute_query(query, params=(order_id,), fetch_one=True)
        
        if not order:
            return None
        
        if include_items:
            # Fetch order items
            items_query = """
                SELECT oi.*, p.product_name, p.sku, p.manufacturer, p.model
                FROM order_items oi
                JOIN products p ON oi.product_id = p.product_id
                WHERE oi.order_id = ?
                ORDER BY oi.order_item_id
            """
            items = BaseRepository.execute_query(
                items_query,
                params=(order_id,),
                fetch_all=True
            )
            order['items'] = items or []
        
        return order
    
    @staticmethod
    def get_orders_by_user(user_id: int, 
                          status: Optional[str] = None,
                          limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get orders for a user

        Args:
            user_id:
            status: Filter by status
            limit: Maximum number of results

        Returns:
            List of orders
        """
        query = """
            SELECT o.*, COUNT(oi.order_item_id) as items_count
            FROM orders o
            LEFT JOIN order_items oi ON o.order_id = oi.order_id
            WHERE o.user_id = ?
        """
        params = [user_id]
        
        if status:
            query += " AND o.status = ?"
            params.append(status)
        
        query += " GROUP BY o.order_id ORDER BY o.order_date DESC"
        
        if limit:
            query += f" LIMIT {limit}"
        
        return BaseRepository.execute_query(
            query,
            params=tuple(params),
            fetch_all=True
        ) or []
    
    @staticmethod
    def get_all_orders(status: Optional[str] = None,
                      payment_status: Optional[str] = None,
                      start_date: Optional[datetime] = None,
                      end_date: Optional[datetime] = None,
                      limit: Optional[int] = 100) -> List[Dict[str, Any]]:
        """
        Get all orders with filtering

        Args:
            status: Filter by order status
            payment_status: Filter by payment status
            start_date: Start date
            end_date: End date
            limit: Maximum number of results

        Returns:
            List of orders
        """
        query = """
            SELECT o.*, 
                   u.username, u.full_name,
                   COUNT(oi.order_item_id) as items_count
            FROM orders o
            JOIN users u ON o.user_id = u.user_id
            LEFT JOIN order_items oi ON o.order_id = oi.order_id
            WHERE 1=1
        """
        params = []
        
        if status:
            query += " AND o.status = ?"
            params.append(status)
        
        if payment_status:
            query += " AND o.payment_status = ?"
            params.append(payment_status)
        
        if start_date:
            query += " AND o.order_date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND o.order_date <= ?"
            params.append(end_date)
        
        query += " GROUP BY o.order_id ORDER BY o.order_date DESC"
        
        if limit:
            query += f" LIMIT {limit}"
        
        return BaseRepository.execute_query(
            query,
            params=tuple(params) if params else None,
            fetch_all=True
        ) or []
    
    @staticmethod
    def update_order_status(order_id: int, new_status: str, 
                          processed_by: Optional[int] = None) -> bool:
        """
        Update order status

        Args:
            order_id: Order ID
            new_status: New status
            processed_by: Manager ID who processes the order

        Returns:
            True if update succeeded
        """
        if new_status not in OrderStatus.ALL_STATUSES:
            raise ValueError(f"Invalid status. Must be one of: {OrderStatus.ALL_STATUSES}")
        
        # Update dates depending on status
        if new_status == OrderStatus.SHIPPED:
            query = """
                UPDATE orders 
                SET status = ?, processed_by = ?, shipped_date = CURRENT_TIMESTAMP
                WHERE order_id = ?
            """
        elif new_status == OrderStatus.DELIVERED:
            query = """
                UPDATE orders 
                SET status = ?, delivered_date = CURRENT_TIMESTAMP
                WHERE order_id = ?
            """
            params = (new_status, order_id)
        else:
            query = "UPDATE orders SET status = ?, processed_by = ? WHERE order_id = ?"
            params = (new_status, processed_by, order_id)
        
        try:
            if new_status in [OrderStatus.SHIPPED]:
                params = (new_status, processed_by, order_id)
            
            BaseRepository.execute_query(query, params=params, commit=True)
            logger.info(f"Order {order_id} status updated to {new_status}")
            return True
        except Exception as e:
            logger.error(f"Error updating order status: {e}")
            raise
    
    @staticmethod
    def update_payment_status(order_id: int, new_payment_status: str) -> bool:
        """
        Update payment status

        Args:
            order_id: Order ID
            new_payment_status: New payment status

        Returns:
            True if update succeeded
        """
        if new_payment_status not in PaymentStatus.ALL_STATUSES:
            raise ValueError(f"Invalid payment status. Must be one of: {PaymentStatus.ALL_STATUSES}")
        
        query = "UPDATE orders SET payment_status = ? WHERE order_id = ?"
        
        try:
            BaseRepository.execute_query(
                query,
                params=(new_payment_status, order_id),
                commit=True
            )
            logger.info(f"Order {order_id} payment status updated to {new_payment_status}")
            return True
        except Exception as e:
            logger.error(f"Error updating payment status: {e}")
            raise
    
    @staticmethod
    def cancel_order(order_id: int, user_id: int) -> bool:
        """
        Cancel an order and return items to stock (transactional)

        Args:
            order_id: Order ID
            user_id:

        Returns:
            True if cancellation succeeded
        """
        with BaseRepository.transaction() as (conn, cursor):
            try:
                # Fetch order items
                cursor.execute(
                    "SELECT product_id, quantity FROM order_items WHERE order_id = ?",
                    (order_id,)
                )
                items = cursor.fetchall()
                
                if not items:
                    raise ValueError(f"Order {order_id} has no items or doesn't exist")
                
                # Return items to stock
                for item in items:
                    product_id = item[0] if not cursor.description else item['product_id']
                    quantity = item[1] if not cursor.description else item['quantity']
                    
                    # Increase stock quantity
                    cursor.execute(
                        "UPDATE products SET stock_quantity = stock_quantity + ? WHERE product_id = ?",
                        (quantity, product_id)
                    )
                    
                    # Create stock movement record
                    cursor.execute("""
                        INSERT INTO stock_movements 
                        (product_id, movement_type, quantity, reference_type, reference_id, user_id)
                        VALUES (?, 'in', ?, 'return', ?, ?)
                    """, (product_id, quantity, order_id, user_id))
                
                # Update order status
                cursor.execute(
                    "UPDATE orders SET status = ? WHERE order_id = ?",
                    (OrderStatus.CANCELLED, order_id)
                )
                
                logger.info(f"Order {order_id} cancelled successfully")
                return True
                
            except Exception as e:
                logger.error(f"Error cancelling order {order_id}: {e}")
                raise
    
    @staticmethod
    def get_order_statistics(start_date: Optional[datetime] = None,
                           end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Get order statistics

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            Dictionary with statistics
        """
        query = """
            SELECT 
                COUNT(*) as total_orders,
                SUM(CASE WHEN status = 'delivered' THEN 1 ELSE 0 END) as delivered_orders,
                SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) as cancelled_orders,
                SUM(CASE WHEN payment_status = 'paid' THEN total_amount ELSE 0 END) as total_revenue,
                AVG(total_amount) as average_order_value
            FROM orders
            WHERE 1=1
        """
        params = []
        
        if start_date:
            query += " AND order_date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND order_date <= ?"
            params.append(end_date)
        
        return BaseRepository.execute_query(
            query,
            params=tuple(params) if params else None,
            fetch_one=True
        ) or {}


class OrderItemRepository(BaseRepository):
    """Repository for working with order items"""
    
    @staticmethod
    def get_items_by_order(order_id: int) -> List[Dict[str, Any]]:
        """Get all items of an order"""
        query = """
            SELECT oi.*, p.product_name, p.sku, p.manufacturer, p.model
            FROM order_items oi
            JOIN products p ON oi.product_id = p.product_id
            WHERE oi.order_id = ?
            ORDER BY oi.order_item_id
        """
        return BaseRepository.execute_query(
            query,
            params=(order_id,),
            fetch_all=True
        ) or []
    
    @staticmethod
    def add_item_to_order(order_id: int, product_id: int, 
                         quantity: int, discount_percent: Decimal = 0) -> Optional[int]:
        """
        Add an item to an existing order
        WARNING: Use only for orders in status pending/confirmed

        Args:
            order_id: Order ID
            product_id: Product ID
            quantity: Quantity
            discount_percent: Discount percent

        Returns:
            Created item ID
        """
        with BaseRepository.transaction() as (conn, cursor):
            try:
                # Check order status
                cursor.execute(
                    "SELECT status FROM orders WHERE order_id = ?",
                    (order_id,)
                )
                order = cursor.fetchone()
                
                if not order:
                    raise ValueError(f"Order {order_id} not found")
                
                status = order[0] if not cursor.description else order['status']
                if status not in [OrderStatus.PENDING, OrderStatus.CONFIRMED]:
                    raise ValueError(f"Cannot add items to order with status {status}")
                
                # Check product availability
                cursor.execute(
                    "SELECT stock_quantity, unit_price FROM products WHERE product_id = ?",
                    (product_id,)
                )
                product = cursor.fetchone()
                
                if not product:
                    raise ValueError(f"Product {product_id} not found")
                
                stock = product[0] if not cursor.description else product['stock_quantity']
                price = product[1] if not cursor.description else product['unit_price']
                
                if stock < quantity:
                    raise ValueError(f"Insufficient stock. Available: {stock}")
                
                # Add item
                cursor.execute("""
                    INSERT INTO order_items 
                    (order_id, product_id, quantity, unit_price, discount_percent)
                    VALUES (?, ?, ?, ?, ?)
                """, (order_id, product_id, quantity, price, discount_percent))
                
                item_id = cursor.lastrowid
                
                # Update stock
                cursor.execute(
                    "UPDATE products SET stock_quantity = stock_quantity - ? WHERE product_id = ?",
                    (quantity, product_id)
                )
                
                logger.info(f"Item {item_id} added to order {order_id}")
                return item_id
                
            except Exception as e:
                logger.error(f"Error adding item to order: {e}")
                raise


# Приклад використання
if __name__ == "__main__":
    from database import DatabaseConnection
    
    try:
        DatabaseConnection.initialize_pool()
        
        # Приклад створення замовлення
        print("=== Creating test order ===")
        items = [
            {'product_id': 1, 'quantity': 2, 'discount_percent': 0},
            {'product_id': 3, 'quantity': 1, 'discount_percent': 5}
        ]
        
        order_id = OrderRepository.create_order(
            user_id=3,  # client1
            shipping_address="Wrocław, Poland, Test Street 123",
            items=items,
            payment_method='card',
            notes='Test order'
        )
        print(f"Order created with ID: {order_id}")
        
        # Отримання замовлення
        print("\n=== Getting order details ===")
        order = OrderRepository.get_order_by_id(order_id)
        if order:
            print(f"Order #{order['order_id']}")
            print(f"Customer: {order['full_name']}")
            print(f"Total: ${order['total_amount']}")
            print(f"Status: {order['status']}")
            print(f"Items: {len(order['items'])}")
            for item in order['items']:
                print(f"  - {item['product_name']}: {item['quantity']} x ${item['unit_price']}")
        
        # Оновлення статусу
        print("\n=== Updating order status ===")
        OrderRepository.update_order_status(order_id, OrderStatus.CONFIRMED, processed_by=2)
        print("Status updated to confirmed")
        
        # Статистика
        print("\n=== Order statistics ===")
        stats = OrderRepository.get_order_statistics()
        print(f"Total orders: {stats.get('total_orders', 0)}")
        print(f"Total revenue: ${stats.get('total_revenue', 0)}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        DatabaseConnection.close_pool()