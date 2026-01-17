import bcrypt
from typing import Optional, List, Dict, Any
from datetime import datetime
from database import BaseRepository
import logging

logger = logging.getLogger(__name__)


class UserRole:
    """Consts for user roles"""
    ADMIN = 'admin'
    MANAGER = 'manager'
    CLIENT = 'client'
    
    ALL_ROLES = [ADMIN, MANAGER, CLIENT]


class PasswordHasher:
    """Hashing and verifying passwords"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hashing password using bcrypt
        
        Args:
            password: password
            
        Returns:
            hashed password
        """
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        """
        Checking password
        
        Args:
            password: password
            hashed_password: hashed password from DB
            
        Returns:
            True if password is correct
        """
        try:
            return bcrypt.checkpw(
                password.encode('utf-8'),
                hashed_password.encode('utf-8')
            )
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False


class UserRepository(BaseRepository):
    @staticmethod
    def create_user(username: str, password: str, email: str, 
                   full_name: str, role: str = UserRole.CLIENT,
                   phone: Optional[str] = None) -> Optional[int]:
        """
        New user
        
        Args:
            username: 
            password: 
            email: 
            full_name: 
            role: (admin/manager/client)
            phone: (optional)
            
        Returns:
            ID of a user/None
        """
        if role not in UserRole.ALL_ROLES:
            raise ValueError(f"Invalid role. Must be one of: {UserRole.ALL_ROLES}")
        
        # Hashing password
        password_hash = PasswordHasher.hash_password(password)
        
        query = """
            INSERT INTO users (username, password_hash, email, full_name, role, phone)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        
        try:
            user_id = BaseRepository.execute_query(
                query,
                params=(username, password_hash, email, full_name, role, phone),
                commit=True
            )
            logger.info(f"User created successfully: {username} (ID: {user_id})")
            return user_id
        except Exception as e:
            logger.error(f"Error creating user {username}: {e}")
            raise
    
    @staticmethod
    def authenticate(username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Authentification
        
        Args:
            username: username
            password: password
            
        Returns:
            User data/None
        """
        query = """
            SELECT user_id, username, password_hash, email, full_name, 
                   role, phone, is_active, created_at
            FROM users
            WHERE username = ? AND is_active = TRUE
        """
        
        user = BaseRepository.execute_query(query, params=(username,), fetch_one=True)
        
        if not user:
            logger.warning(f"Authentication failed: user {username} not found or inactive")
            return None
        
        if not PasswordHasher.verify_password(password, user['password_hash']):
            logger.warning(f"Authentication failed: invalid password for user {username}")
            return None
        
        # Delete hash
        user.pop('password_hash')
        
        logger.info(f"User {username} authenticated successfully")
        return user
    
    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get user by ID
        
        Args:
            user_id:
            
        Returns:
            User data/None
        """
        query = """
            SELECT user_id, username, email, full_name, role, 
                   phone, is_active, created_at, updated_at
            FROM users
            WHERE user_id = ?
        """
        
        return BaseRepository.execute_query(query, params=(user_id,), fetch_one=True)
    
    @staticmethod
    def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
        """Get user by username"""
        query = """
            SELECT user_id, username, email, full_name, role, 
                   phone, is_active, created_at, updated_at
            FROM users
            WHERE username = ?
        """
        
        return BaseRepository.execute_query(query, params=(username,), fetch_one=True)
    
    @staticmethod
    def get_all_users(role: Optional[str] = None, 
                     is_active: Optional[bool] = None) -> List[Dict[str, Any]]:
        """
        Get user list with filter
        
        Args:
            role: 
            is_active: 
            
        Returns:
            user ist
        """
        query = """
            SELECT user_id, username, email, full_name, role, 
                   phone, is_active, created_at, updated_at
            FROM users
            WHERE 1=1
        """
        params = []
        
        if role:
            query += " AND role = ?"
            params.append(role)
        
        if is_active is not None:
            query += " AND is_active = ?"
            params.append(is_active)
        
        query += " ORDER BY created_at DESC"
        
        return BaseRepository.execute_query(
            query, 
            params=tuple(params) if params else None,
            fetch_all=True
        ) or []
    
    @staticmethod
    def update_user(user_id: int, **kwargs) -> bool:
        """
        Update user fields
        
        Args:
            user_id: 
            **kwargs: Other fields
            
        Returns:
            True if update successful
        """
        allowed_fields = ['email', 'full_name', 'phone', 'role', 'is_active']
        
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not updates:
            logger.warning("No valid fields to update")
            return False
        
        if 'role' in updates and updates['role'] not in UserRole.ALL_ROLES:
            raise ValueError(f"Invalid role. Must be one of: {UserRole.ALL_ROLES}")
        
        set_clause = ", ".join([f"{field} = ?" for field in updates.keys()])
        query = f"UPDATE users SET {set_clause} WHERE user_id = ?"
        
        params = tuple(updates.values()) + (user_id,)
        
        try:
            BaseRepository.execute_query(query, params=params, commit=True)
            logger.info(f"User {user_id} updated successfully")
            return True
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}")
            raise
    
    @staticmethod
    def update_password(user_id: int, new_password: str) -> bool:
        """
        Change user password
        
        Args:
            user_id: 
            new_password: new password
            
        Returns:
            True if update is successful
        """
        password_hash = PasswordHasher.hash_password(new_password)
        
        query = "UPDATE users SET password_hash = ? WHERE user_id = ?"
        
        try:
            BaseRepository.execute_query(
                query,
                params=(password_hash, user_id),
                commit=True
            )
            logger.info(f"Password updated for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating password for user {user_id}: {e}")
            raise
    
    @staticmethod
    def deactivate_user(user_id: int) -> bool:
        """
        Deactivate user (soft delete)
        
        Args:
            user_id:
            
        Returns:
            True if successful
        """
        return UserRepository.update_user(user_id, is_active=False)
    
    @staticmethod
    def delete_user(user_id: int) -> bool:
        """
        Hard delete user from DB
        ATTENTION: This action is irreversible!
        
        Args:
            user_id:
            
        Returns:
            True if successful
        """
        query = "DELETE FROM users WHERE user_id = ?"
        
        try:
            BaseRepository.execute_query(query, params=(user_id,), commit=True)
            logger.info(f"User {user_id} deleted permanently")
            return True
        except Exception as e:
            logger.error(f"Error deleting user {user_id}: {e}")
            raise


class AccessControl:
    # Matrix of access
    PERMISSIONS = {
        # Managing users
        'create_user': [UserRole.ADMIN],
        'update_user': [UserRole.ADMIN],
        'delete_user': [UserRole.ADMIN],
        'view_all_users': [UserRole.ADMIN, UserRole.MANAGER],
        
        # Managing products
        'create_product': [UserRole.ADMIN, UserRole.MANAGER],
        'update_product': [UserRole.ADMIN, UserRole.MANAGER],
        'delete_product': [UserRole.ADMIN],
        'view_products': [UserRole.ADMIN, UserRole.MANAGER, UserRole.CLIENT],

        # Managing suppliers
        'manage_suppliers': [UserRole.ADMIN, UserRole.MANAGER],

        # Managing orders
        'view_all_orders': [UserRole.ADMIN, UserRole.MANAGER],
        'process_order': [UserRole.ADMIN, UserRole.MANAGER],
        'create_order': [UserRole.ADMIN, UserRole.MANAGER, UserRole.CLIENT],
        'view_own_orders': [UserRole.ADMIN, UserRole.MANAGER, UserRole.CLIENT],

        # Managing stock
        'manage_stock': [UserRole.ADMIN, UserRole.MANAGER],
        'view_stock_movements': [UserRole.ADMIN, UserRole.MANAGER],
    }
    
    @staticmethod
    def has_permission(user_role: str, action: str) -> bool:
        """
        Whether the user has permission

        Args:
            user_role:
            action: 
            
        Returns:
            True if allowed
        """
        allowed_roles = AccessControl.PERMISSIONS.get(action, [])
        return user_role in allowed_roles
    
    @staticmethod
    def require_permission(user_role: str, action: str):
        """
        Reaquire permission
        
        Args:
            user_role: 
            action: 
            
        Raises:
            PermissionError if no permission
        """
        if not AccessControl.has_permission(user_role, action):
            raise PermissionError(
                f"User with role '{user_role}' does not have permission for action '{action}'"
            )


# Example
if __name__ == "__main__":
    from database import DatabaseConnection
    
    try:
        DatabaseConnection.initialize_pool()
        
        print("=== Creating new user ===")
        new_user_id = UserRepository.create_user(
            username='testclient',
            password='test123',
            email='test@example.com',
            full_name='Test Client',
            role=UserRole.CLIENT,
            phone='+48501112233'
        )
        print(f"Created user ID: {new_user_id}")
        
        # testing authentication
        print("\n=== Testing authentication ===")
        auth_result = UserRepository.authenticate('testclient', 'test123')
        if auth_result:
            print(f"Authentication successful: {auth_result['username']}")
            print(f"Role: {auth_result['role']}")
        
        # testing wrong password
        print("\n=== Testing wrong password ===")
        wrong_auth = UserRepository.authenticate('testclient', 'wrongpassword')
        print(f"Authentication result: {wrong_auth}")
        
        # testingn getting user by ID
        print("\n=== Getting user by ID ===")
        user = UserRepository.get_user_by_id(new_user_id)
        if user:
            print(f"User found: {user['username']}")
        
        # testing update
        print("\n=== Updating user ===")
        UserRepository.update_user(new_user_id, phone='+48507778899')
        print("User updated")
        
        print("\n=== Getting all clients ===")
        clients = UserRepository.get_all_users(role=UserRole.CLIENT)
        print(f"Found {len(clients)} clients")
        
        # testing access control
        print("\n=== Testing access control ===")
        print(f"Client can create order: {AccessControl.has_permission(UserRole.CLIENT, 'create_order')}")
        print(f"Client can manage stock: {AccessControl.has_permission(UserRole.CLIENT, 'manage_stock')}")
        print(f"Manager can manage stock: {AccessControl.has_permission(UserRole.MANAGER, 'manage_stock')}")
        
        # Deactivating test user
        print("\n=== Deactivating test user ===")
        UserRepository.deactivate_user(new_user_id)
        print("User deactivated")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        DatabaseConnection.close_pool()