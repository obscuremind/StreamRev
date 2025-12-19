"""
Configuration management
"""

import os
import json
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from file or environment
    
    Args:
        config_path: Path to config file
        
    Returns:
        Configuration dictionary
    """
    config = {
        # Database
        'db_host': os.getenv('DB_HOST', '127.0.0.1'),
        'db_port': int(os.getenv('DB_PORT', 3306)),
        'db_user': os.getenv('DB_USER', 'streamrev'),
        'db_password': os.getenv('DB_PASSWORD', ''),
        'db_name': os.getenv('DB_NAME', 'streamrev'),
        
        # Redis
        'redis_host': os.getenv('REDIS_HOST', '127.0.0.1'),
        'redis_port': int(os.getenv('REDIS_PORT', 6379)),
        'redis_password': os.getenv('REDIS_PASSWORD', None),
        
        # API
        'api_host': os.getenv('API_HOST', '0.0.0.0'),
        'api_port': int(os.getenv('API_PORT', 5000)),
        'secret_key': os.getenv('SECRET_KEY', 'change-this-secret-key'),
        
        # FFmpeg
        'ffmpeg_path': os.getenv('FFMPEG_PATH', '/usr/bin/ffmpeg'),
        
        # Streaming
        'stream_base_url': os.getenv('STREAM_BASE_URL', 'http://localhost'),
        'max_connections_per_user': int(os.getenv('MAX_CONNECTIONS_PER_USER', 1)),
        
        # System
        'log_level': os.getenv('LOG_LEVEL', 'INFO'),
        'debug': os.getenv('DEBUG', 'false').lower() == 'true',
    }
    
    # Load from file if provided
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                file_config = json.load(f)
                config.update(file_config)
            logger.info(f"Loaded config from: {config_path}")
        except Exception as e:
            logger.error(f"Failed to load config file: {str(e)}")
    
    return config


def save_config(config: Dict[str, Any], config_path: str) -> bool:
    """
    Save configuration to file
    
    Args:
        config: Configuration dictionary
        config_path: Path to config file
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        logger.info(f"Saved config to: {config_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to save config: {str(e)}")
        return False
