"""
Database models for StreamRev
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import bcrypt


class BaseModel:
    """Base model class"""
    
    def __init__(self, db):
        self.db = db


class User(BaseModel):
    """User model"""
    
    def create(self, username: str, password: str, **kwargs) -> Optional[int]:
        """Create new user"""
        query = """
            INSERT INTO users (username, password, email, status, exp_date, 
                             max_connections, reseller_id, is_trial)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            username,
            self._hash_password(password),
            kwargs.get('email'),
            kwargs.get('status', 1),
            kwargs.get('exp_date'),
            kwargs.get('max_connections', 1),
            kwargs.get('reseller_id'),
            kwargs.get('is_trial', 0)
        )
        
        if self.db.execute(query, params):
            return self.db.last_insert_id()
        return None
    
    def get_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username"""
        query = "SELECT * FROM users WHERE username = %s"
        return self.db.fetch_one(query, (username,))
    
    def get_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        query = "SELECT * FROM users WHERE id = %s"
        return self.db.fetch_one(query, (user_id,))
    
    def authenticate(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user"""
        user = self.get_by_username(username)
        if user and self._verify_password(password, user['password']):
            return user
        return None
    
    def update(self, user_id: int, **kwargs) -> bool:
        """Update user"""
        fields = []
        values = []
        
        for key, value in kwargs.items():
            if key in ['email', 'status', 'exp_date', 'max_connections', 'last_ip']:
                fields.append(f"{key} = %s")
                values.append(value)
        
        if not fields:
            return False
        
        values.append(user_id)
        query = f"UPDATE users SET {', '.join(fields)} WHERE id = %s"
        return self.db.execute(query, tuple(values))
    
    def delete(self, user_id: int) -> bool:
        """Delete user"""
        query = "DELETE FROM users WHERE id = %s"
        return self.db.execute(query, (user_id,))
    
    def list_all(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """List all users"""
        query = "SELECT * FROM users ORDER BY created_at DESC LIMIT %s OFFSET %s"
        return self.db.fetch_all(query, (limit, offset))
    
    @staticmethod
    def _hash_password(password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    @staticmethod
    def _verify_password(password: str, hashed: str) -> bool:
        """Verify password against hash using constant-time comparison"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


class Reseller(BaseModel):
    """Reseller model"""
    
    def create(self, username: str, password: str, **kwargs) -> Optional[int]:
        """Create new reseller"""
        query = """
            INSERT INTO resellers (username, password, email, status, credits, parent_id)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        params = (
            username,
            User._hash_password(password),
            kwargs.get('email'),
            kwargs.get('status', 1),
            kwargs.get('credits', 0.00),
            kwargs.get('parent_id')
        )
        
        if self.db.execute(query, params):
            return self.db.last_insert_id()
        return None
    
    def get_by_id(self, reseller_id: int) -> Optional[Dict[str, Any]]:
        """Get reseller by ID"""
        query = "SELECT * FROM resellers WHERE id = %s"
        return self.db.fetch_one(query, (reseller_id,))


class Stream(BaseModel):
    """Stream (Live TV) model"""
    
    def create(self, name: str, stream_source: str, **kwargs) -> Optional[int]:
        """Create new stream"""
        query = """
            INSERT INTO streams (name, stream_display_name, stream_icon, stream_type,
                               stream_source, category_id, status, transcode_profile)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            name,
            kwargs.get('stream_display_name', name),
            kwargs.get('stream_icon'),
            kwargs.get('stream_type', 'live'),
            stream_source,
            kwargs.get('category_id'),
            kwargs.get('status', 1),
            kwargs.get('transcode_profile')
        )
        
        if self.db.execute(query, params):
            return self.db.last_insert_id()
        return None
    
    def get_by_id(self, stream_id: int) -> Optional[Dict[str, Any]]:
        """Get stream by ID"""
        query = "SELECT * FROM streams WHERE id = %s"
        return self.db.fetch_one(query, (stream_id,))
    
    def list_all(self, category_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """List all streams"""
        if category_id:
            query = "SELECT * FROM streams WHERE category_id = %s AND status = 1 ORDER BY `order`"
            return self.db.fetch_all(query, (category_id,))
        else:
            query = "SELECT * FROM streams WHERE status = 1 ORDER BY `order`"
            return self.db.fetch_all(query)


class VOD(BaseModel):
    """VOD (Movies) model"""
    
    def create(self, name: str, stream_source: str, **kwargs) -> Optional[int]:
        """Create new VOD"""
        query = """
            INSERT INTO vod (name, title, year, director, cast, description, plot,
                           duration, rating, cover, backdrop, category_id, stream_source, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            name,
            kwargs.get('title', name),
            kwargs.get('year'),
            kwargs.get('director'),
            kwargs.get('cast'),
            kwargs.get('description'),
            kwargs.get('plot'),
            kwargs.get('duration'),
            kwargs.get('rating'),
            kwargs.get('cover'),
            kwargs.get('backdrop'),
            kwargs.get('category_id'),
            stream_source,
            kwargs.get('status', 1)
        )
        
        if self.db.execute(query, params):
            return self.db.last_insert_id()
        return None
    
    def get_by_id(self, vod_id: int) -> Optional[Dict[str, Any]]:
        """Get VOD by ID"""
        query = "SELECT * FROM vod WHERE id = %s"
        return self.db.fetch_one(query, (vod_id,))
    
    def list_all(self, category_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """List all VOD"""
        if category_id:
            query = "SELECT * FROM vod WHERE category_id = %s AND status = 1"
            return self.db.fetch_all(query, (category_id,))
        else:
            query = "SELECT * FROM vod WHERE status = 1"
            return self.db.fetch_all(query)


class Series(BaseModel):
    """Series model"""
    
    def create(self, name: str, **kwargs) -> Optional[int]:
        """Create new series"""
        query = """
            INSERT INTO series (name, title, year, cast, description, plot,
                              rating, cover, backdrop, category_id, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            name,
            kwargs.get('title', name),
            kwargs.get('year'),
            kwargs.get('cast'),
            kwargs.get('description'),
            kwargs.get('plot'),
            kwargs.get('rating'),
            kwargs.get('cover'),
            kwargs.get('backdrop'),
            kwargs.get('category_id'),
            kwargs.get('status', 1)
        )
        
        if self.db.execute(query, params):
            return self.db.last_insert_id()
        return None
    
    def get_by_id(self, series_id: int) -> Optional[Dict[str, Any]]:
        """Get series by ID"""
        query = "SELECT * FROM series WHERE id = %s"
        return self.db.fetch_one(query, (series_id,))


class Category(BaseModel):
    """Category model"""
    
    def create(self, name: str, type: str, **kwargs) -> Optional[int]:
        """Create new category"""
        query = """
            INSERT INTO categories (name, type, parent_id, `order`)
            VALUES (%s, %s, %s, %s)
        """
        params = (
            name,
            type,
            kwargs.get('parent_id'),
            kwargs.get('order', 0)
        )
        
        if self.db.execute(query, params):
            return self.db.last_insert_id()
        return None
    
    def list_by_type(self, type: str) -> List[Dict[str, Any]]:
        """List categories by type"""
        query = "SELECT * FROM categories WHERE type = %s ORDER BY `order`"
        return self.db.fetch_all(query, (type,))
