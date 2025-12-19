"""
Web interface routes for StreamRev
"""

from flask import Flask, render_template, send_from_directory
import os


def register_web_routes(app: Flask):
    """Register web interface routes"""
    
    # Get template and static directories
    template_dir = os.path.join(os.path.dirname(__file__), 'templates')
    static_dir = os.path.join(os.path.dirname(__file__), 'static')
    
    # Update Flask app config
    app.template_folder = template_dir
    app.static_folder = static_dir
    
    @app.route('/')
    def index():
        """Home page"""
        return render_template('index.html')
    
    @app.route('/login')
    def login():
        """Login page"""
        return render_template('login.html')
    
    @app.route('/dashboard')
    def dashboard():
        """Dashboard page"""
        return render_template('index.html')
    
    @app.route('/static/<path:filename>')
    def serve_static(filename):
        """Serve static files"""
        return send_from_directory(static_dir, filename)
