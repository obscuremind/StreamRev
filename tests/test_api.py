"""
API tests for StreamRev
"""

import pytest
from src.api.server import create_app
from src.api.auth import generate_token, verify_token


class TestAPIServer:
    """Test API server"""
    
    @pytest.fixture
    def app(self):
        """Create test app"""
        config = {
            'TESTING': True,
            'SECRET_KEY': 'test-secret-key-for-testing'
        }
        return create_app(config)
    
    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return app.test_client()
    
    def test_health_endpoint(self, client):
        """Test health check endpoint"""
        response = client.get('/health')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'ok'
        assert 'version' in data


class TestAuthentication:
    """Test authentication"""
    
    def test_generate_token(self):
        """Test token generation"""
        import os
        os.environ['SECRET_KEY'] = 'test-secret-key'
        
        token = generate_token(1, 'testuser', False)
        assert token is not None
        assert len(token) > 0
    
    def test_verify_token_valid(self):
        """Test token verification with valid token"""
        import os
        os.environ['SECRET_KEY'] = 'test-secret-key'
        
        token = generate_token(1, 'testuser', False)
        payload = verify_token(token)
        
        assert payload is not None
        assert payload['user_id'] == 1
        assert payload['username'] == 'testuser'
    
    def test_verify_token_invalid(self):
        """Test token verification with invalid token"""
        payload = verify_token('invalid-token')
        assert payload is None


class TestXtreamCodesAPI:
    """Test Xtream Codes compatible API"""
    
    @pytest.fixture
    def app(self):
        """Create test app"""
        config = {
            'TESTING': True,
            'SECRET_KEY': 'test-secret-key-for-testing'
        }
        return create_app(config)
    
    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return app.test_client()
    
    def test_player_api_missing_credentials(self, client):
        """Test player API without credentials"""
        response = client.get('/player_api.php')
        assert response.status_code == 401
