from typing import Optional, List, Dict, Any
from database import BaseRepository
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class MovementType:
    # consts
    IN = 'in'
    OUT = 'out'
    ADJUSTMENT = 'adjustment'
    RETURN = 'return'

    ALL_TYPES = [IN, OUT, ADJUSTMENT, RETURN]


class ReferenceType:
    # consts
    PURCHASE = 'purchase'
    SALE = 'sale'
    ADJUSTMENT = 'adjustment'
    RETURN = 'return'
    DAMAGED = 'damaged'

    ALL_TYPES = [PURCHASE, SALE, ADJUSTMENT, RETURN, DAMAGED]


class StockMovementRepository(BaseRepository):    
    @staticmethod
    def create_movement(product_id: int, movement_type: str, quantity: int,
                       reference_type: str, user_id: int,
                       reference_id: Optional[int] = None,
                       notes: Optional[str] = None) -> Optional[int]:
        """
        Creating a record of stock_movement
        
        Args:
            product_id: ID
            movement_type: type (in/out/adjustment/return)
            quantity: amount (positive for in, negative for out)
            reference_type: op type (purchase/sale/adjustment/return/damaged)
            user_id: user ID
            reference_id: ID of connected op
            notes: notes
            
        Returns:
            ID
        """
        if movement_type not in MovementType.ALL_TYPES:
            raise ValueError(f"Invalid movement type. Must be one of: {MovementType.ALL_TYPES}")
        
        if reference_type not in ReferenceType.ALL_TYPES:
            raise ValueError(f"Invalid reference type. Must be one of: {ReferenceType.ALL_TYPES}")
        
        query = """
            INSERT INTO stock_movements 
            (product_id, movement_type, quantity, reference_type, reference_id, user_id, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        
        try:
            movement_id = BaseRepository.execute_query(
                query,
                params=(product_id, movement_type, quantity, reference_type, 
                       reference_id, user_id, notes),
                commit=True
            )
            logger.info(f"Stock movement created: ID {movement_id}, Product {product_id}, "
                       f"Type {movement_type}, Quantity {quantity}")
            return movement_id
        except Exception as e:
            logger.error(f"Error creating stock movement: {e}")
            raise
    
    @staticmethod
    def get_movement_by_id(movement_id: int) -> Optional[Dict[str, Any]]:
        # Get movement by ID
        query = """
            SELECT sm.*, 
                   p.product_name, p.sku,
                   u.username, u.full_name
            FROM stock_movements sm
            JOIN products p ON sm.product_id = p.product_id
            JOIN users u ON sm.user_id = u.user_id
            WHERE sm.movement_id = ?
        """
        return BaseRepository.execute_query(query, params=(movement_id,), fetch_one=True)
    
    @staticmethod
    def get_movements_by_product(product_id: int,
                                start_date: Optional[datetime] = None,
                                end_date: Optional[datetime] = None,
                                limit: Optional[int] = 100) -> List[Dict[str, Any]]:
        """
        Get history
        
        Args:
            product_id: ID 
            start_date: Start date
            end_date: End date
            limit: Maximum number
            
        Returns:
            List of records
        """
        query = """
            SELECT sm.*, 
                   u.username, u.full_name
            FROM stock_movements sm
            JOIN users u ON sm.user_id = u.user_id
            WHERE sm.product_id = ?
        """
        params = [product_id]
        
        if start_date:
            query += " AND sm.movement_date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND sm.movement_date <= ?"
            params.append(end_date)
        
        query += " ORDER BY sm.movement_date DESC"
        
        if limit:
            query += f" LIMIT {limit}"
        
        return BaseRepository.execute_query(
            query,
            params=tuple(params),
            fetch_all=True
        ) or []
    
    @staticmethod
    def get_all_movements(movement_type: Optional[str] = None,
                         reference_type: Optional[str] = None,
                         start_date: Optional[datetime] = None,
                         end_date: Optional[datetime] = None,
                         limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get all stock movements with filtering
        
        Args:
            movement_type: Filter by movement
            reference_type: Filter by reference
            start_date: Start date
            end_date: End date
            limit: Maximum number

        Returns:
            List of records
        """
        query = """
            SELECT sm.*, 
                   p.product_name, p.sku,
                   u.username, u.full_name
            FROM stock_movements sm
            JOIN products p ON sm.product_id = p.product_id
            JOIN users u ON sm.user_id = u.user_id
            WHERE 1=1
        """
        params = []
        
        if movement_type:
            query += " AND sm.movement_type = ?"
            params.append(movement_type)
        
        if reference_type:
            query += " AND sm.reference_type = ?"
            params.append(reference_type)
        
        if start_date:
            query += " AND sm.movement_date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND sm.movement_date <= ?"
            params.append(end_date)
        
        query += " ORDER BY sm.movement_date DESC"
        
        if limit:
            query += f" LIMIT {limit}"
        
        return BaseRepository.execute_query(
            query,
            params=tuple(params) if params else None,
            fetch_all=True
        ) or []
    
    @staticmethod
    def get_movements_by_reference(reference_type: str, 
                                   reference_id: int) -> List[Dict[str, Any]]:
        """
        Get all movements related to a specific operation
        For example, all movements for a specific order
        
        Args:
            reference_type: Type of operation
            reference_id: ID
            
        Returns:
            List of records
        """
        query = """
            SELECT sm.*, 
                   p.product_name, p.sku,
                   u.username, u.full_name
            FROM stock_movements sm
            JOIN products p ON sm.product_id = p.product_id
            JOIN users u ON sm.user_id = u.user_id
            WHERE sm.reference_type = ? AND sm.reference_id = ?
            ORDER BY sm.movement_date DESC
        """
        return BaseRepository.execute_query(
            query,
            params=(reference_type, reference_id),
            fetch_all=True
        ) or []


class StockReportRepository(BaseRepository):
    @staticmethod
    def get_current_stock_report(category_id: Optional[int] = None,
                                supplier_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get current stock report
        
        Args:
            category_id: Filter by category
            supplier_id: Filter by supplier
            
        Returns:
            List of products with stock info
        """
        query = """
            SELECT 
                p.product_id,
                p.product_name,
                p.sku,
                p.manufacturer,
                p.model,
                c.category_name,
                s.supplier_name,
                p.stock_quantity,
                p.reorder_level,
                p.unit_price,
                p.stock_quantity * p.unit_price as stock_value,
                CASE 
                    WHEN p.stock_quantity <= 0 THEN 'Out of Stock'
                    WHEN p.stock_quantity <= p.reorder_level THEN 'Low Stock'
                    ELSE 'In Stock'
                END as stock_status
            FROM products p
            JOIN categories c ON p.category_id = c.category_id
            JOIN suppliers s ON p.supplier_id = s.supplier_id
            WHERE p.is_active = TRUE
        """
        params = []
        
        if category_id:
            query += " AND p.category_id = ?"
            params.append(category_id)
        
        if supplier_id:
            query += " AND p.supplier_id = ?"
            params.append(supplier_id)
        
        query += " ORDER BY c.category_name, p.product_name"
        
        return BaseRepository.execute_query(
            query,
            params=tuple(params) if params else None,
            fetch_all=True
        ) or []
    
    @staticmethod
    def get_stock_turnover_report(start_date: datetime, 
                                  end_date: datetime) -> List[Dict[str, Any]]:
        """
        Stock turnover report
        
        Args:
            start_date: start date
            end_date: end date

        Returns:
            Report with sales and stock information
        """
        query = """
            SELECT 
                p.product_id,
                p.product_name,
                p.sku,
                c.category_name,
                p.stock_quantity as current_stock,
                COALESCE(SUM(CASE WHEN sm.movement_type = 'out' 
                                 AND sm.reference_type = 'sale' 
                            THEN ABS(sm.quantity) ELSE 0 END), 0) as total_sold,
                COALESCE(SUM(CASE WHEN sm.movement_type = 'in' 
                                 AND sm.reference_type = 'purchase' 
                            THEN sm.quantity ELSE 0 END), 0) as total_purchased,
                p.unit_price,
                COALESCE(SUM(CASE WHEN sm.movement_type = 'out' 
                                 AND sm.reference_type = 'sale' 
                            THEN ABS(sm.quantity) * p.unit_price ELSE 0 END), 0) as sales_revenue
            FROM products p
            JOIN categories c ON p.category_id = c.category_id
            LEFT JOIN stock_movements sm ON p.product_id = sm.product_id
                AND sm.movement_date BETWEEN ? AND ?
            WHERE p.is_active = TRUE
            GROUP BY p.product_id, p.product_name, p.sku, c.category_name, 
                     p.stock_quantity, p.unit_price
            ORDER BY total_sold DESC
        """
        
        return BaseRepository.execute_query(
            query,
            params=(start_date, end_date),
            fetch_all=True
        ) or []
    
    @staticmethod
    def get_stock_movements_summary(start_date: datetime,
                                   end_date: datetime) -> Dict[str, Any]:
        """
        Summary of stock movements

        Args:
            start_date:
            end_date:

        Returns:
            Dictionary with stock movement statistics
        """
        query = """
            SELECT 
                COUNT(*) as total_movements,
                SUM(CASE WHEN movement_type = 'in' THEN 1 ELSE 0 END) as total_in,
                SUM(CASE WHEN movement_type = 'out' THEN 1 ELSE 0 END) as total_out,
                SUM(CASE WHEN movement_type = 'in' THEN quantity ELSE 0 END) as total_quantity_in,
                SUM(CASE WHEN movement_type = 'out' THEN ABS(quantity) ELSE 0 END) as total_quantity_out,
                COUNT(DISTINCT product_id) as products_affected,
                COUNT(DISTINCT user_id) as users_involved
            FROM stock_movements
            WHERE movement_date BETWEEN ? AND ?
        """
        
        return BaseRepository.execute_query(
            query,
            params=(start_date, end_date),
            fetch_one=True
        ) or {}
    
    @staticmethod
    def get_products_below_reorder_level() -> List[Dict[str, Any]]:
        """
        Report of products that need reordering

        Returns:
            List of products with quantity below reorder_level
        """
        query = """
            SELECT 
                p.product_id,
                p.product_name,
                p.sku,
                c.category_name,
                s.supplier_name,
                s.email as supplier_email,
                s.phone as supplier_phone,
                p.stock_quantity,
                p.reorder_level,
                p.reorder_level - p.stock_quantity as shortage,
                p.unit_price,
                (p.reorder_level - p.stock_quantity) * p.unit_price as reorder_cost
            FROM products p
            JOIN categories c ON p.category_id = c.category_id
            JOIN suppliers s ON p.supplier_id = s.supplier_id
            WHERE p.stock_quantity <= p.reorder_level 
                AND p.is_active = TRUE
            ORDER BY p.stock_quantity ASC, shortage DESC
        """
        
        return BaseRepository.execute_query(query, fetch_all=True) or []
    
    @staticmethod
    def get_stock_value_by_category() -> List[Dict[str, Any]]:
        """
        Report of stock value by category

        Returns:
            List of categories with total stock value
        """
        query = """
            SELECT 
                c.category_id,
                c.category_name,
                COUNT(p.product_id) as products_count,
                SUM(p.stock_quantity) as total_quantity,
                SUM(p.stock_quantity * p.unit_price) as total_value,
                AVG(p.unit_price) as average_price
            FROM categories c
            LEFT JOIN products p ON c.category_id = p.category_id 
                AND p.is_active = TRUE
            GROUP BY c.category_id, c.category_name
            HAVING products_count > 0
            ORDER BY total_value DESC
        """
        
        return BaseRepository.execute_query(query, fetch_all=True) or []
    
    @staticmethod
    def get_top_selling_products(start_date: datetime,
                                end_date: datetime,
                                limit: int = 10) -> List[Dict[str, Any]]:
        """
        Top selling products

        Args:
            start_date:
            end_date:
            limit: number of top items

        Returns:
            List of top selling products
        """
        query = """
            SELECT 
                p.product_id,
                p.product_name,
                p.sku,
                c.category_name,
                COUNT(DISTINCT sm.reference_id) as orders_count,
                SUM(ABS(sm.quantity)) as total_quantity_sold,
                SUM(ABS(sm.quantity) * p.unit_price) as total_revenue
            FROM products p
            JOIN categories c ON p.category_id = c.category_id
            JOIN stock_movements sm ON p.product_id = sm.product_id
            WHERE sm.movement_type = 'out' 
                AND sm.reference_type = 'sale'
                AND sm.movement_date BETWEEN ? AND ?
            GROUP BY p.product_id, p.product_name, p.sku, c.category_name
            ORDER BY total_quantity_sold DESC
            LIMIT ?
        """
        
        return BaseRepository.execute_query(
            query,
            params=(start_date, end_date, limit),
            fetch_all=True
        ) or []


# Example
if __name__ == "__main__":
    from database import DatabaseConnection
    from datetime import datetime, timedelta
    
    try:
        DatabaseConnection.initialize_pool()
        
        # Current stock
        print("=== Current Stock Report ===")
        stock_report = StockReportRepository.get_current_stock_report()
        print(f"Total products: {len(stock_report)}")
        for item in stock_report[:5]:  # Перші 5 товарів
            print(f"{item['product_name']}: {item['stock_quantity']} units "
                  f"({item['stock_status']}) - Value: ${item['stock_value']:.2f}")
        
        # Products to reorder
        print("\n=== Products Below Reorder Level ===")
        reorder = StockReportRepository.get_products_below_reorder_level()
        print(f"Products to reorder: {len(reorder)}")
        for item in reorder:
            print(f"{item['product_name']}: Stock {item['stock_quantity']}, "
                  f"Need {item['shortage']} more (Cost: ${item['reorder_cost']:.2f})")
        
        # Price by category
        print("\n=== Stock Value by Category ===")
        by_category = StockReportRepository.get_stock_value_by_category()
        for cat in by_category:
            print(f"{cat['category_name']}: {cat['products_count']} products, "
                  f"Total value: ${cat['total_value']:.2f}")
        
        # Report for the last month
        print("\n=== Stock Movements (Last 30 Days) ===")
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        summary = StockReportRepository.get_stock_movements_summary(start_date, end_date)
        print(f"Total movements: {summary.get('total_movements', 0)}")
        print(f"In: {summary.get('total_in', 0)}, Out: {summary.get('total_out', 0)}")
        print(f"Products affected: {summary.get('products_affected', 0)}")
        
        # Top
        print("\n=== Top Selling Products (Last 30 Days) ===")
        top_products = StockReportRepository.get_top_selling_products(start_date, end_date, limit=5)
        for i, product in enumerate(top_products, 1):
            print(f"{i}. {product['product_name']}: {product['total_quantity_sold']} units, "
                  f"Revenue: ${product['total_revenue']:.2f}")
        
        # History movements
        print("\n=== Stock Movements for Product ID 1 ===")
        movements = StockMovementRepository.get_movements_by_product(1, limit=5)
        for mov in movements:
            print(f"{mov['movement_date']}: {mov['movement_type']} {mov['quantity']} units "
                  f"({mov['reference_type']}) by {mov['username']}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        DatabaseConnection.close_pool()