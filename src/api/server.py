"""
Main API server using Flask
"""

from flask import Flask, jsonify, request
from typing import Dict, Any
import logging
import os
from .auth import authenticate_user, token_required
from .routes import register_routes
from ..utils.config import load_config
from ..web.routes import register_web_routes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app(config: Dict[str, Any] = None) -> Flask:
    """
    Create and configure Flask application
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Configured Flask application
    """
    app = Flask(__name__)
    
    # Load configuration from environment/file
    app_config = load_config()
    
    # Default configuration
    app.config.update({
        'SECRET_KEY': app_config.get('secret_key'),
        'JSON_SORT_KEYS': False,
        'JSONIFY_PRETTYPRINT_REGULAR': False
    })
    
    # Update with provided config
    if config:
        app.config.update(config)
    
    # Validate that SECRET_KEY is set
    if not app.config.get('SECRET_KEY'):
        logger.error("SECRET_KEY not configured! This is a critical security issue.")
        raise ValueError("SECRET_KEY must be configured")
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal error: {str(error)}")
        return jsonify({'error': 'Internal server error'}), 500
    
    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({'error': 'Unauthorized'}), 401
    
    # Health check endpoint
    @app.route('/health', methods=['GET'])
    def health_check():
        return jsonify({'status': 'ok', 'version': '1.0.0'})
    
    # Register API routes
    register_routes(app)
    
    # Register web interface routes
    register_web_routes(app)
    
    logger.info("Flask application created successfully")
    return app


if __name__ == '__main__':
    app = create_app()
    # Debug mode should only be enabled in development
    debug_mode = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=5000, debug=debug_mode)
