"""
API routes for StreamRev - Xtream Codes compatible
"""

from flask import Flask, request, jsonify, Response
from .auth import token_required, admin_required, authenticate_user
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


def register_routes(app: Flask):
    """Register all API routes"""
    
    # Xtream Codes compatible authentication endpoint
    @app.route('/player_api.php', methods=['GET'])
    def player_api():
        """
        Xtream Codes API compatibility endpoint
        Supports: get_user_info, get_live_streams, get_vod_streams, get_series, etc.
        """
        action = request.args.get('action', '')
        username = request.args.get('username', '')
        password = request.args.get('password', '')
        
        # Authentication required for all actions
        if not username or not password:
            return jsonify({'error': 'Missing credentials'}), 401
        
        # Handle different actions
        if action == 'get_user_info':
            return get_user_info(username, password)
        elif action == 'get_live_streams':
            return get_live_streams(username, password)
        elif action == 'get_vod_streams':
            return get_vod_streams(username, password)
        elif action == 'get_series':
            return get_series(username, password)
        elif action == 'get_live_categories':
            return get_live_categories()
        elif action == 'get_vod_categories':
            return get_vod_categories()
        elif action == 'get_series_categories':
            return get_series_categories()
        else:
            return jsonify({'error': 'Invalid action'}), 400
    
    # Modern REST API endpoints
    @app.route('/api/v1/auth/login', methods=['POST'])
    def login():
        """User login endpoint"""
        data = request.get_json()
        
        if not data or 'username' not in data or 'password' not in data:
            return jsonify({'error': 'Missing credentials'}), 400
        
        # TODO: Authenticate against database
        auth_result = {
            'user_id': 1,
            'username': data['username'],
            'token': 'sample-token-123',
            'exp_date': '2025-12-31 23:59:59'
        }
        
        return jsonify(auth_result)
    
    @app.route('/api/v1/streams', methods=['GET'])
    @token_required
    def list_streams():
        """List all live streams"""
        category_id = request.args.get('category_id', type=int)
        
        # TODO: Fetch from database
        streams = [
            {
                'id': 1,
                'name': 'Sample Channel 1',
                'stream_icon': 'http://example.com/icon1.png',
                'category_id': 1
            }
        ]
        
        return jsonify(streams)
    
    @app.route('/api/v1/streams/<int:stream_id>', methods=['GET'])
    @token_required
    def get_stream(stream_id):
        """Get specific stream details"""
        # TODO: Fetch from database
        stream = {
            'id': stream_id,
            'name': 'Sample Channel',
            'stream_icon': 'http://example.com/icon.png',
            'stream_source': 'http://example.com/stream.m3u8'
        }
        
        return jsonify(stream)
    
    @app.route('/api/v1/vod', methods=['GET'])
    @token_required
    def list_vod():
        """List all VOD content"""
        category_id = request.args.get('category_id', type=int)
        
        # TODO: Fetch from database
        vod_list = [
            {
                'id': 1,
                'name': 'Sample Movie',
                'year': '2024',
                'rating': '8.5',
                'cover': 'http://example.com/cover.jpg'
            }
        ]
        
        return jsonify(vod_list)
    
    @app.route('/api/v1/series', methods=['GET'])
    @token_required
    def list_series():
        """List all series"""
        # TODO: Fetch from database
        series_list = [
            {
                'id': 1,
                'name': 'Sample Series',
                'year': '2024',
                'rating': '9.0',
                'cover': 'http://example.com/series.jpg'
            }
        ]
        
        return jsonify(series_list)
    
    # Admin endpoints
    @app.route('/api/v1/admin/users', methods=['GET', 'POST'])
    @admin_required
    def manage_users():
        """List or create users (admin only)"""
        if request.method == 'GET':
            # TODO: Fetch users from database
            users = [
                {
                    'id': 1,
                    'username': 'user1',
                    'status': 1,
                    'exp_date': '2025-12-31'
                }
            ]
            return jsonify(users)
        
        elif request.method == 'POST':
            data = request.get_json()
            # TODO: Create user in database
            return jsonify({'id': 1, 'username': data.get('username')}), 201
    
    @app.route('/api/v1/admin/streams', methods=['POST'])
    @admin_required
    def create_stream():
        """Create new stream (admin only)"""
        data = request.get_json()
        # TODO: Create stream in database
        return jsonify({'id': 1, 'name': data.get('name')}), 201
    
    @app.route('/api/v1/admin/vod', methods=['POST'])
    @admin_required
    def create_vod():
        """Create new VOD content (admin only)"""
        data = request.get_json()
        # TODO: Create VOD in database
        return jsonify({'id': 1, 'name': data.get('name')}), 201


def get_user_info(username: str, password: str) -> Response:
    """Get user information (Xtream Codes compatible)"""
    # TODO: Authenticate and fetch user info
    user_info = {
        'user_info': {
            'username': username,
            'password': password,
            'message': '',
            'auth': 1,
            'status': 'Active',
            'exp_date': '1735689599',
            'is_trial': '0',
            'active_cons': '0',
            'created_at': '1640995200',
            'max_connections': '1',
            'allowed_output_formats': ['m3u8', 'ts']
        },
        'server_info': {
            'url': 'http://streamrev.local',
            'port': '80',
            'https_port': '443',
            'server_protocol': 'http',
            'rtmp_port': '1935',
            'timezone': 'UTC',
            'timestamp_now': 1640995200
        }
    }
    
    return jsonify(user_info)


def get_live_streams(username: str, password: str) -> Response:
    """Get live streams list (Xtream Codes compatible)"""
    # TODO: Fetch from database
    streams = []
    return jsonify(streams)


def get_vod_streams(username: str, password: str) -> Response:
    """Get VOD streams list (Xtream Codes compatible)"""
    # TODO: Fetch from database
    vod_list = []
    return jsonify(vod_list)


def get_series(username: str, password: str) -> Response:
    """Get series list (Xtream Codes compatible)"""
    # TODO: Fetch from database
    series = []
    return jsonify(series)


def get_live_categories() -> Response:
    """Get live categories (Xtream Codes compatible)"""
    # TODO: Fetch from database
    categories = []
    return jsonify(categories)


def get_vod_categories() -> Response:
    """Get VOD categories (Xtream Codes compatible)"""
    # TODO: Fetch from database
    categories = []
    return jsonify(categories)


def get_series_categories() -> Response:
    """Get series categories (Xtream Codes compatible)"""
    # TODO: Fetch from database
    categories = []
    return jsonify(categories)
