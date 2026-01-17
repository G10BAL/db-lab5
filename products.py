from typing import Optional, List, Dict, Any, Tuple
from database import BaseRepository
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class CategoryRepository(BaseRepository):
    @staticmethod
    def create_category(category_name: str, description: Optional[str] = None,
                       parent_category_id: Optional[int] = None) -> Optional[int]:
        """
        New category
        
        Args:
            category_name: 
            description: 
            parent_category_id: ID of a parent category
            
        Returns:
            new category ID
        """
        query = """
            INSERT INTO categories (category_name, description, parent_category_id)
            VALUES (?, ?, ?)
        """
        
        try:
            category_id = BaseRepository.execute_query(
                query,
                params=(category_name, description, parent_category_id),
                commit=True
            )
            logger.info(f"Category created: {category_name} (ID: {category_id})")
            return category_id
        except Exception as e:
            logger.error(f"Error creating category {category_name}: {e}")
            raise
    
    @staticmethod
    def get_category_by_id(category_id: int) -> Optional[Dict[str, Any]]:
        """Get category by its ID"""
        query = "SELECT * FROM categories WHERE category_id = ?"
        return BaseRepository.execute_query(query, params=(category_id,), fetch_one=True)
    
    @staticmethod
    def get_all_categories(is_active: Optional[bool] = True) -> List[Dict[str, Any]]:
        """
        Get category list
        
        Args:
            is_active: if none -> all
            
        Returns:
            Category list
        """
        query = "SELECT * FROM categories"
        params = []
        
        if is_active is not None:
            query += " WHERE is_active = ?"
            params.append(is_active)
        
        query += " ORDER BY category_name"
        
        return BaseRepository.execute_query(
            query,
            params=tuple(params) if params else None,
            fetch_all=True
        ) or []
    
    @staticmethod
    def get_subcategories(parent_category_id: int) -> List[Dict[str, Any]]:
        """Get subcategories"""
        query = """
            SELECT * FROM categories 
            WHERE parent_category_id = ? AND is_active = TRUE
            ORDER BY category_name
        """
        return BaseRepository.execute_query(
            query,
            params=(parent_category_id,),
            fetch_all=True
        ) or []
    
    @staticmethod
    def update_category(category_id: int, **kwargs) -> bool:
        """Update category"""
        allowed_fields = ['category_name', 'description', 'parent_category_id', 'is_active']
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not updates:
            return False
        
        set_clause = ", ".join([f"{field} = ?" for field in updates.keys()])
        query = f"UPDATE categories SET {set_clause} WHERE category_id = ?"
        params = tuple(updates.values()) + (category_id,)
        
        try:
            BaseRepository.execute_query(query, params=params, commit=True)
            logger.info(f"Category {category_id} updated")
            return True
        except Exception as e:
            logger.error(f"Error updating category {category_id}: {e}")
            raise


class SupplierRepository(BaseRepository):
    @staticmethod
    def create_supplier(supplier_name: str, phone: str, 
                       contact_person: Optional[str] = None,
                       email: Optional[str] = None,
                       address: Optional[str] = None,
                       country: Optional[str] = None,
                       tax_id: Optional[str] = None) -> Optional[int]:
        """
        New supplier
        
        Args:
            supplier_name:
            phone: (essential)
            contact_person:
            email:
            address:
            country:
            tax_id:
            
        Returns:
            ID of the created supplier
        """
        query = """
            INSERT INTO suppliers 
            (supplier_name, contact_person, email, phone, address, country, tax_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        
        try:
            supplier_id = BaseRepository.execute_query(
                query,
                params=(supplier_name, contact_person, email, phone, address, country, tax_id),
                commit=True
            )
            logger.info(f"Supplier created: {supplier_name} (ID: {supplier_id})")
            return supplier_id
        except Exception as e:
            logger.error(f"Error creating supplier {supplier_name}: {e}")
            raise
    
    @staticmethod
    def get_supplier_by_id(supplier_id: int) -> Optional[Dict[str, Any]]:
        """Get supplier by ID"""
        query = "SELECT * FROM suppliers WHERE supplier_id = ?"
        return BaseRepository.execute_query(query, params=(supplier_id,), fetch_one=True)
    
    @staticmethod
    def get_all_suppliers(is_active: Optional[bool] = True,
                         country: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get supplier list

        Args:
            is_active: Filter by status
            country: Filter by country
            
        Returns:
            Supplier list
        """
        query = "SELECT * FROM suppliers WHERE 1=1"
        params = []
        
        if is_active is not None:
            query += " AND is_active = ?"
            params.append(is_active)
        
        if country:
            query += " AND country = ?"
            params.append(country)
        
        query += " ORDER BY supplier_name"
        
        return BaseRepository.execute_query(
            query,
            params=tuple(params) if params else None,
            fetch_all=True
        ) or []
    
    @staticmethod
    def update_supplier(supplier_id: int, **kwargs) -> bool:
        """Update supplier data"""
        allowed_fields = ['supplier_name', 'contact_person', 'email', 'phone', 
                         'address', 'country', 'tax_id', 'is_active', 'rating']
        
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not updates:
            return False
        
        set_clause = ", ".join([f"{field} = ?" for field in updates.keys()])
        query = f"UPDATE suppliers SET {set_clause} WHERE supplier_id = ?"
        params = tuple(updates.values()) + (supplier_id,)
        
        try:
            BaseRepository.execute_query(query, params=params, commit=True)
            logger.info(f"Supplier {supplier_id} updated")
            return True
        except Exception as e:
            logger.error(f"Error updating supplier {supplier_id}: {e}")
            raise
    
    @staticmethod
    def get_supplier_products(supplier_id: int) -> List[Dict[str, Any]]:
        """Get products from a specific supplier"""
        query = """
            SELECT p.*, c.category_name
            FROM products p
            JOIN categories c ON p.category_id = c.category_id
            WHERE p.supplier_id = ? AND p.is_active = TRUE
            ORDER BY p.product_name
        """
        return BaseRepository.execute_query(
            query,
            params=(supplier_id,),
            fetch_all=True
        ) or []


class ProductRepository(BaseRepository):
    @staticmethod
    def create_product(product_name: str, category_id: int, supplier_id: int,
                      sku: str, unit_price: Decimal, 
                      description: Optional[str] = None,
                      manufacturer: Optional[str] = None,
                      model: Optional[str] = None,
                      caliber: Optional[str] = None,
                      stock_quantity: int = 0,
                      reorder_level: int = 10,
                      weight_kg: Optional[Decimal] = None,
                      image_url: Optional[str] = None) -> Optional[int]:
        """
        New product
        
        Args:
            product_name: 
            category_id: 
            supplier_id: 
            sku: stock keeping unit
            unit_price:
            description:
            manufacturer: producer
            model:
            caliber:
            stock_quantity: amount
            reorder_level:
            weight_kg:
            image_url: optional
            
        Returns:
            ID of the created product
        """
        query = """
            INSERT INTO products 
            (product_name, category_id, supplier_id, sku, description, 
             manufacturer, model, caliber, unit_price, stock_quantity, 
             reorder_level, weight_kg, image_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        try:
            product_id = BaseRepository.execute_query(
                query,
                params=(product_name, category_id, supplier_id, sku, description,
                       manufacturer, model, caliber, unit_price, stock_quantity,
                       reorder_level, weight_kg, image_url),
                commit=True
            )
            logger.info(f"Product created: {product_name} (ID: {product_id})")
            return product_id
        except Exception as e:
            logger.error(f"Error creating product {product_name}: {e}")
            raise
    
    @staticmethod
    def get_product_by_id(product_id: int) -> Optional[Dict[str, Any]]:
        """
        Get product by ID
        
        Returns:
            Dictionary with product data
        """
        query = """
            SELECT p.*, c.category_name, s.supplier_name
            FROM products p
            JOIN categories c ON p.category_id = c.category_id
            JOIN suppliers s ON p.supplier_id = s.supplier_id
            WHERE p.product_id = ?
        """
        return BaseRepository.execute_query(query, params=(product_id,), fetch_one=True)
    
    @staticmethod
    def get_product_by_sku(sku: str) -> Optional[Dict[str, Any]]:
        """Get product by SKU"""
        query = """
            SELECT p.*, c.category_name, s.supplier_name
            FROM products p
            JOIN categories c ON p.category_id = c.category_id
            JOIN suppliers s ON p.supplier_id = s.supplier_id
            WHERE p.sku = ?
        """
        return BaseRepository.execute_query(query, params=(sku,), fetch_one=True)
    
    @staticmethod
    def search_products(search_term: Optional[str] = None,
                       category_id: Optional[int] = None,
                       supplier_id: Optional[int] = None,
                       min_price: Optional[Decimal] = None,
                       max_price: Optional[Decimal] = None,
                       is_active: bool = True,
                       in_stock_only: bool = False) -> List[Dict[str, Any]]:
        """
        Search products with filtering
        
        Args:
            search_term: Search by name, description, manufacturer, model
            category_id: Filter by category
            supplier_id: Filter by supplier
            min_price: min price
            max_price: max price
            is_active: Only active products
            in_stock_only: Only products in stock
            
        Returns:
            List of products
        """
        query = """
            SELECT p.*, c.category_name, s.supplier_name
            FROM products p
            JOIN categories c ON p.category_id = c.category_id
            JOIN suppliers s ON p.supplier_id = s.supplier_id
            WHERE p.is_active = ?
        """
        params = [is_active]
        
        if search_term:
            query += """ AND (
                p.product_name LIKE ? OR 
                p.description LIKE ? OR 
                p.manufacturer LIKE ? OR 
                p.model LIKE ? OR
                p.sku LIKE ?
            )"""
            search_pattern = f"%{search_term}%"
            params.extend([search_pattern] * 5)
        
        if category_id:
            query += " AND p.category_id = ?"
            params.append(category_id)
        
        if supplier_id:
            query += " AND p.supplier_id = ?"
            params.append(supplier_id)
        
        if min_price is not None:
            query += " AND p.unit_price >= ?"
            params.append(min_price)
        
        if max_price is not None:
            query += " AND p.unit_price <= ?"
            params.append(max_price)
        
        if in_stock_only:
            query += " AND p.stock_quantity > 0"
        
        query += " ORDER BY p.product_name"
        
        return BaseRepository.execute_query(
            query,
            params=tuple(params),
            fetch_all=True
        ) or []
    
    @staticmethod
    def update_product(product_id: int, **kwargs) -> bool:
        """
        Update product
        
        IMPORTANT: stock_quantity should be updated via update_stock
        to automatically create stock_movement records
        """
        allowed_fields = ['product_name', 'category_id', 'supplier_id', 'sku',
                         'description', 'manufacturer', 'model', 'caliber',
                         'unit_price', 'reorder_level', 'weight_kg', 
                         'is_active', 'image_url']
        
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not updates:
            return False
        
        set_clause = ", ".join([f"{field} = ?" for field in updates.keys()])
        query = f"UPDATE products SET {set_clause} WHERE product_id = ?"
        params = tuple(updates.values()) + (product_id,)
        
        try:
            BaseRepository.execute_query(query, params=params, commit=True)
            logger.info(f"Product {product_id} updated")
            return True
        except Exception as e:
            logger.error(f"Error updating product {product_id}: {e}")
            raise
    
    @staticmethod
    def update_stock(product_id: int, new_quantity: int, user_id: int,
                    notes: Optional[str] = None) -> bool:
        """
        Update stock quantity
        Automatically creates a record in stock_movements through a trigger

        Args:
            product_id: ID of the product
            new_quantity: new quantity
            user_id: ID of the user 
            notes:
            
        Returns:
            True if successful
        """
        query = "UPDATE products SET stock_quantity = ? WHERE product_id = ?"
        
        try:
            BaseRepository.execute_query(
                query,
                params=(new_quantity, product_id),
                commit=True
            )
            logger.info(f"Stock updated for product {product_id}: {new_quantity}")
            return True
        except Exception as e:
            logger.error(f"Error updating stock for product {product_id}: {e}")
            raise
    
    @staticmethod
    def get_low_stock_products(threshold: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get products with low stock levels
        
        Args:
            threshold: threshold value, if None uses reorder_level
            
        Returns:
            List of products
        """
        if threshold:
            query = """
                SELECT p.*, c.category_name, s.supplier_name
                FROM products p
                JOIN categories c ON p.category_id = c.category_id
                JOIN suppliers s ON p.supplier_id = s.supplier_id
                WHERE p.stock_quantity <= ? AND p.is_active = TRUE
                ORDER BY p.stock_quantity ASC
            """
            params = (threshold,)
        else:
            query = """
                SELECT p.*, c.category_name, s.supplier_name
                FROM products p
                JOIN categories c ON p.category_id = c.category_id
                JOIN suppliers s ON p.supplier_id = s.supplier_id
                WHERE p.stock_quantity <= p.reorder_level AND p.is_active = TRUE
                ORDER BY p.stock_quantity ASC
            """
            params = None
        
        return BaseRepository.execute_query(query, params=params, fetch_all=True) or []
    
    @staticmethod
    def check_stock_availability(product_id: int, quantity: int) -> Tuple[bool, int]:
        """
        Whether enough stock is available
        
        Args:
            product_id: ID of the product
            quantity: required quantity
            
        Returns:
            Tuple (whether enough stock is available, current stock)
        """
        query = "SELECT stock_quantity FROM products WHERE product_id = ?"
        result = BaseRepository.execute_query(query, params=(product_id,), fetch_one=True)
        
        if not result:
            return False, 0
        
        current_stock = result['stock_quantity']
        return current_stock >= quantity, current_stock


# Example
if __name__ == "__main__":
    from database import DatabaseConnection
    from decimal import Decimal
    
    try:
        DatabaseConnection.initialize_pool()
        
        # Searching
        print("=== Searching products ===")
        products = ProductRepository.search_products(search_term="Glock")
        print(f"Found {len(products)} products")
        for p in products:
            print(f"- {p['product_name']}: ${p['unit_price']}, Stock: {p['stock_quantity']}")
        
        # Low stock
        print("\n=== Low stock products ===")
        low_stock = ProductRepository.get_low_stock_products()
        print(f"Found {len(low_stock)} products with low stock")
        
        # Availability
        print("\n=== Checking stock availability ===")
        available, current = ProductRepository.check_stock_availability(1, 10)
        print(f"Product ID 1: Available for 10 units: {available}, Current stock: {current}")
        
        # Category
        print("\n=== Getting categories ===")
        categories = CategoryRepository.get_all_categories()
        print(f"Found {len(categories)} categories:")
        for cat in categories:
            print(f"- {cat['category_name']}")
        
        # Supplier
        print("\n=== Getting suppliers ===")
        suppliers = SupplierRepository.get_all_suppliers()
        print(f"Found {len(suppliers)} suppliers:")
        for sup in suppliers:
            print(f"- {sup['supplier_name']} ({sup['country']})")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        DatabaseConnection.close_pool()