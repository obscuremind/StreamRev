"""
Authentication and authorization module
"""

import jwt
import datetime
import os
from functools import wraps
from flask import request, jsonify, current_app
from typing import Optional, Dict, Any, Callable
import logging

logger = logging.getLogger(__name__)


def get_secret_key() -> str:
    """Get JWT secret key from app config or environment"""
    try:
        return current_app.config.get('SECRET_KEY')
    except RuntimeError:
        # Outside application context
        secret = os.getenv('SECRET_KEY')
        if not secret:
            logger.error("SECRET_KEY not configured! This is a critical security issue.")
            raise ValueError("SECRET_KEY must be configured in environment or config")
        return secret


def generate_token(user_id: int, username: str, is_admin: bool = False) -> str:
    """
    Generate JWT token
    
    Args:
        user_id: User ID
        username: Username
        is_admin: Whether user is admin
        
    Returns:
        JWT token string
    """
    secret = get_secret_key()
    
    payload = {
        'user_id': user_id,
        'username': username,
        'is_admin': is_admin,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7),
        'iat': datetime.datetime.utcnow()
    }
    
    return jwt.encode(payload, secret, algorithm='HS256')


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify JWT token
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded payload or None if invalid
    """
    try:
        secret = get_secret_key()
        payload = jwt.decode(token, secret, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token expired")
        return None
    except jwt.InvalidTokenError:
        logger.warning("Invalid token")
        return None


def token_required(f: Callable) -> Callable:
    """
    Decorator to require valid JWT token
    
    Args:
        f: Function to wrap
        
    Returns:
        Wrapped function
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Get token from header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(' ')[1]
            except IndexError:
                return jsonify({'error': 'Invalid authorization header'}), 401
        
        # Get token from query parameter (for Xtream Codes compatibility)
        elif 'token' in request.args:
            token = request.args.get('token')
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        # Verify token
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        # Add user info to request
        request.user_id = payload['user_id']
        request.username = payload['username']
        request.is_admin = payload.get('is_admin', False)
        
        return f(*args, **kwargs)
    
    return decorated


def admin_required(f: Callable) -> Callable:
    """
    Decorator to require admin privileges
    
    Args:
        f: Function to wrap
        
    Returns:
        Wrapped function
    """
    @wraps(f)
    @token_required
    def decorated(*args, **kwargs):
        if not request.is_admin:
            return jsonify({'error': 'Admin privileges required'}), 403
        return f(*args, **kwargs)
    
    return decorated


def authenticate_user(username: str, password: str, db) -> Optional[Dict[str, Any]]:
    """
    Authenticate user credentials
    
    Args:
        username: Username
        password: Password
        db: Database instance
        
    Returns:
        User info with token or None if authentication fails
    """
    from src.database.models import User
    
    user_model = User(db)
    user = user_model.authenticate(username, password)
    
    if user:
        token = generate_token(
            user['id'],
            user['username'],
            bool(user.get('admin_enabled', 0))
        )
        
        return {
            'user_id': user['id'],
            'username': user['username'],
            'token': token,
            'exp_date': user.get('exp_date'),
            'status': user.get('status')
        }
    
    return None
