from database import DatabaseConnection
from users import UserRepository, UserRole, AccessControl
from products import ProductRepository, CategoryRepository, SupplierRepository
from orders import OrderRepository, OrderStatus
from stock_movements import StockReportRepository, StockMovementRepository
from datetime import datetime, timedelta
import sys


class CLI:
    def __init__(self):
        self.current_user = None
        self.running = True
    
    def clear_screen(self):
        print("\n" * 2)
    
    def print_header(self, text):
        print("\n" + "="*80)
        print(f"  {text}")
        print("="*80 + "\n")
    
    def login(self):
        self.print_header("ENTRY TO THE SYSTEM")
        
        print("Available test users:")
        print("  admin / admin123     (Administrator)")
        print("  manager1 / manager123 (Manager)")
        print("  client1 / client123   (Client)")
        print()
        
        username = input("Username: ").strip()
        password = input("Password: ").strip()
        
        user = UserRepository.authenticate(username, password)
        
        if user:
            self.current_user = user
            print(f"\nWelcome, {user['full_name']}!")
            print(f"  Role: {user['role']}")
            input("\nPress Enter to continue...")
            return True
        else:
            print("\n✗ Invalid username or password")
            input("\nPress Enter to try again...")
            return False
    
    def main_menu(self):
        while self.running:
            self.clear_screen()
            self.print_header(f"MAIN MENU - {self.current_user['full_name']} ({self.current_user['role']})")

            print("1. Search products")
            print("2. View categories")
            print("3. View suppliers")
            print("4. Stock reports")

            if self.current_user['role'] in [UserRole.ADMIN, UserRole.MANAGER, UserRole.CLIENT]:
                print("5. Orders")
            
            if self.current_user['role'] in [UserRole.ADMIN, UserRole.MANAGER]:
                print("6. Manage products")
                print("7. Stock movements")
            
            if self.current_user['role'] == UserRole.ADMIN:
                print("8. Manage users")
            
            print("\n0. Exit")
            
            choice = input("\nSelect an option: ").strip()
            
            if choice == "1":
                self.search_products_menu()
            elif choice == "2":
                self.view_categories()
            elif choice == "3":
                self.view_suppliers()
            elif choice == "4":
                self.stock_reports_menu()
            elif choice == "5" and self.current_user['role'] in [UserRole.ADMIN, UserRole.MANAGER, UserRole.CLIENT]:
                self.orders_menu()
            elif choice == "6" and self.current_user['role'] in [UserRole.ADMIN, UserRole.MANAGER]:
                self.manage_products_menu()
            elif choice == "7" and self.current_user['role'] in [UserRole.ADMIN, UserRole.MANAGER]:
                self.stock_movements_menu()
            elif choice == "8" and self.current_user['role'] == UserRole.ADMIN:
                self.manage_users_menu()
            elif choice == "0":
                self.running = False
            else:
                print("Invalid selection")
                input("\nPress Enter...")

    def search_products_menu(self):
        self.print_header("SEARCH PRODUCTS")

        print("Enter search criteria (Enter to skip):")

        search_term = input("Search by text: ").strip() or None
        
        categories = CategoryRepository.get_all_categories()
        if categories:
            print("\nCategories:")
            for cat in categories:
                print(f"  {cat['category_id']}. {cat['category_name']}")
            category_input = input("Category ID: ").strip()
            category_id = int(category_input) if category_input else None
        else:
            category_id = None
        
        min_price_input = input("Minimum price: ").strip()
        min_price = float(min_price_input) if min_price_input else None
        
        max_price_input = input("Maximum price: ").strip()
        max_price = float(max_price_input) if max_price_input else None
        
        in_stock_input = input("Only in stock? (y/n): ").strip().lower()
        in_stock_only = in_stock_input == 'y'
        
        # Пошук
        print("\nПошук...")
        products = ProductRepository.search_products(
            search_term=search_term,
            category_id=category_id,
            min_price=min_price,
            max_price=max_price,
            in_stock_only=in_stock_only
        )
        
        # Результати
        print(f"\nFound products: {len(products)}\n")
        
        if products:
            for i, product in enumerate(products, 1):
                print(f"{i}. {product['product_name']}")
                print(f"   SKU: {product['sku']}")
                print(f"   Category: {product['category_name']}")
                print(f"   Price: ${product['unit_price']:.2f}")
                print(f"   In stock: {product['stock_quantity']}")
                print()
        else:
            print("No products found")
        
        input("Press Enter to return...")
    
    def view_categories(self):
        self.print_header("CATEGORIES")
        
        categories = CategoryRepository.get_all_categories()
        
        for cat in categories:
            parent = f" (subcategory {cat['parent_category_id']})" if cat['parent_category_id'] else ""
            print(f"{cat['category_id']}. {cat['category_name']}{parent}")
            if cat['description']:
                print(f"   {cat['description']}")
            print()
        
        input("Press Enter to return...")
    
    def view_suppliers(self):
        self.print_header("SUPPLIERS")
        
        suppliers = SupplierRepository.get_all_suppliers()
        
        for sup in suppliers:
            print(f"{sup['supplier_id']}. {sup['supplier_name']}")
            print(f"   Country: {sup['country']}")
            print(f"   Contact: {sup['contact_person']}")
            print(f"   Phone: {sup['phone']}")
            print(f"   Email: {sup['email']}")
            if sup['rating']:
                print(f"   Rating: {sup['rating']:.2f}/5.00")
            print()
        
        input("Press Enter to return...")
    
    def stock_reports_menu(self):
        self.print_header("STOCK REPORTS")
        
        print("1. Current stock status")
        print("2. Products to reorder")
        print("3. Value by categories")
        print("4. Top products by period")
        print("\n0. Back")
        
        choice = input("\nSelect report: ").strip()
        
        if choice == "1":
            self.current_stock_report()
        elif choice == "2":
            self.reorder_report()
        elif choice == "3":
            self.value_by_category_report()
        elif choice == "4":
            self.top_products_report()
    
    def current_stock_report(self):
        self.print_header("CURRENT STOCK STATUS")
        
        stock_report = StockReportRepository.get_current_stock_report()
        
        total_value = sum(item['stock_value'] for item in stock_report)
        total_items = sum(item['stock_quantity'] for item in stock_report)
        
        print(f"Total products: {len(stock_report)}")
        print(f"Total quantity: {total_items}")
        print(f"Total value: ${total_value:.2f}\n")
        
        for item in stock_report:
            status_icon = {
                'In Stock': '✓',
                'Low Stock': '⚠',
                'Out of Stock': '✗'
            }.get(item['stock_status'], '?')
            
            print(f"{status_icon} {item['product_name']}")
            print(f"   Amount: {item['stock_quantity']}")
            print(f"   Value: ${item['stock_value']:.2f}")
            print(f"   Status: {item['stock_status']}")
            print()
        
        input("Press Enter to return...")
    
    def reorder_report(self):
        self.print_header("PRODUCTS TO REORDER")
        
        reorder = StockReportRepository.get_products_below_reorder_level()
        
        if reorder:
            print(f"Need to reorder: {len(reorder)} products\n")
            
            for item in reorder:
                print(f"Product: {item['product_name']}")
                print(f"   In stock: {item['stock_quantity']}")
                print(f"   Minimum: {item['reorder_level']}")
                print(f"   Shortage: {item['shortage']}")
                print(f"   Reorder cost: ${item['reorder_cost']:.2f}")
                print(f"   Supplier: {item['supplier_name']}")
                print(f"   Phone: {item['supplier_phone']}")
                print()
        else:
            print("✓ All products are in sufficient quantity")
        
        input("\nPress Enter to return...")
    
    def value_by_category_report(self):
        self.print_header("STOCK VALUE BY CATEGORY")
        
        by_category = StockReportRepository.get_stock_value_by_category()
        
        for cat in by_category:
            print(f"Category: {cat['category_name']}")
            print(f"   Products: {cat['products_count']}")
            print(f"   Total quantity: {cat['total_quantity']}")
            print(f"   Total value: ${cat['total_value']:.2f}")
            print(f"   Average price: ${cat['average_price']:.2f}")
            print()
        
        input("Press Enter to return...")
    
    def top_products_report(self):
        self.print_header("TOP PRODUCTS BY PERIOD")
        
        days = input("Number of days (default 30): ").strip()
        days = int(days) if days else 30
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        top_products = StockReportRepository.get_top_selling_products(
            start_date, end_date, limit=10
        )
        
        if top_products:
            print(f"\nTop 10 products in the last {days} days:\n")
            
            for i, product in enumerate(top_products, 1):
                print(f"{i}. {product['product_name']}")
                print(f"   Sold: {product['total_quantity_sold']} units")
                print(f"   Orders: {product['orders_count']}")
                print(f"   Revenue: ${product['total_revenue']:.2f}")
                print()
        else:
            print("\nNo data for this period")
        
        input("Press Enter to return...")
    
    def orders_menu(self):
        self.print_header("ORDERS")
        
        if self.current_user['role'] == UserRole.CLIENT:
            print("1. My orders")
            print("2. Create order")
            print("\n0. Back")
            
            choice = input("\nChoose an option: ").strip()
            
            if choice == "1":
                self.view_my_orders()
            elif choice == "2":
                self.create_order()
        else:
            print("1. All orders")
            print("2. Create order")
            print("3. Process order")
            print("\n0. Back")
            
            choice = input("\nChoose an option: ").strip()
            
            if choice == "1":
                self.view_all_orders()
            elif choice == "2":
                self.create_order()
            elif choice == "3":
                self.process_order()
    
    def view_my_orders(self):
        self.print_header("MY ORDERS")
        
        orders = OrderRepository.get_orders_by_user(self.current_user['user_id'])
        
        if orders:
            for order in orders:
                print(f"Order #{order['order_id']}")
                print(f"   Date: {order['order_date']}")
                print(f"   Status: {order['status']}")
                print(f"   Payment: {order['payment_status']}")
                print(f"   Amount: ${order['total_amount']:.2f}")
                print(f"   Items: {order['items_count']}")
                print()
        else:
            print("You don't have any orders yet")
        
        input("\nPress Enter to return...")
    
    def view_all_orders(self):

        self.print_header("ALL ORDERS")
        
        orders = OrderRepository.get_all_orders(limit=20)
        
        print(f"Last 20 orders:\n")
        
        for order in orders:
            print(f"#{order['order_id']} - {order['full_name']}")
            print(f"   Date: {order['order_date']}")
            print(f"   Status: {order['status']}")
            print(f"   Amount: ${order['total_amount']:.2f}")
            print()
        
        input("Press Enter to return...")
    
    def create_order(self):
        self.print_header("CREATE ORDER")
        
        print("Order creation function")
        print("(For full implementation, use test_interactive.py)")
        
        input("\nPress Enter to return...")
    
    def process_order(self):
        self.print_header("PROCESS ORDER")
        
        order_id = input("Order ID: ").strip()
        
        if not order_id:
            return
        
        order_id = int(order_id)
        order = OrderRepository.get_order_by_id(order_id)
        
        if not order:
            print("Order not found")
            input("\nPress Enter...")
            return

        print(f"\nOrder #{order['order_id']}")
        print(f"Client: {order['full_name']}")
        print(f"Current status: {order['status']}")
        print(f"Amount: ${order['total_amount']:.2f}")
        
        print("\nNew status:")
        print("1. Confirmed")
        print("2. Processing")
        print("3. Shipped")
        print("4. Delivered")
        print("5. Cancelled")
        
        choice = input("\nChoose status: ").strip()
        
        status_map = {
            '1': OrderStatus.CONFIRMED,
            '2': OrderStatus.PROCESSING,
            '3': OrderStatus.SHIPPED,
            '4': OrderStatus.DELIVERED,
            '5': OrderStatus.CANCELLED
        }
        
        if choice in status_map:
            new_status = status_map[choice]
            OrderRepository.update_order_status(
                order_id, 
                new_status, 
                processed_by=self.current_user['user_id']
            )
            print(f"\nStatus changed to '{new_status}'")
        else:
            print("\nStatus not changed")
        
        input("\nPress Enter to return...")
    def manage_products_menu(self):
        self.print_header("MANAGE PRODUCTS")
        
        print("Product management functions")
        
        input("\nPress Enter to return...")
    
    def stock_movements_menu(self):
        self.print_header("STOCK MOVEMENTS")
        
        print("Viewing stock movement history")
        
        input("\nPress Enter to return...")
    
    def manage_users_menu(self):
        self.print_header("MANAGEMENT OF USERS")
        
        users = UserRepository.get_all_users()
        
        for user in users:
            active = "✓" if user['is_active'] else "✗"
            print(f"{user['user_id']}. {user['username']} ({user['role']}) {active}")
            print(f"   {user['full_name']} - {user['email']}")
            print()
        
        input("Press Enter to return...")
    
    def run(self):
        try:
            print("\n" + "="*80)
            print("  System for managing weapon stock")
            print("="*80 + "\n")
            
            # Initialize DB
            print("Connecting...")
            DatabaseConnection.initialize_pool()
            print("Connected\n")
            
            while not self.current_user:
                if not self.login():
                    retry = input("Try again (y/n): ").strip().lower()
                    if retry != 'y':
                        return
            
            self.main_menu()
            
            
        except KeyboardInterrupt:
            print("\n\nEnded by user\n")
        
        except Exception as e:
            print(f"\nError: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            DatabaseConnection.close_pool()
            print("\nConnection closed\n")


if __name__ == "__main__":
    cli = CLI()
    cli.run()