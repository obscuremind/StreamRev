"""
API module for StreamRev
"""

from .server import create_app
from .auth import authenticate_user, generate_token

__all__ = ['create_app', 'authenticate_user', 'generate_token']
