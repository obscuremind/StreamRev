"""
Main API server using Flask
"""

from flask import Flask, jsonify, request
from typing import Dict, Any
import logging
from .auth import authenticate_user, token_required
from .routes import register_routes

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
    
    # Default configuration
    app.config.update({
        'SECRET_KEY': 'your-secret-key-change-this',
        'JSON_SORT_KEYS': False,
        'JSONIFY_PRETTYPRINT_REGULAR': False
    })
    
    # Update with provided config
    if config:
        app.config.update(config)
    
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
    
    logger.info("Flask application created successfully")
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
