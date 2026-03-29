import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    APP_NAME: str = "IPTV Panel"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    SECRET_KEY: str = "change-this-secret-key-in-production"

    # Database
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "iptv"
    DB_PASSWORD: str = "iptv"
    DB_NAME: str = "iptv_panel"
    DATABASE_URL: Optional[str] = None

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None

    # Server
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000
    SERVER_PROTOCOL: str = "http"

    # JWT
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24

    # Streaming
    FFMPEG_PATH: str = "/usr/bin/ffmpeg"
    FFPROBE_PATH: str = "/usr/bin/ffprobe"
    STREAM_TIMEOUT: int = 30
    MAX_CONNECTIONS_PER_USER: int = 1

    # Paths
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    CONTENT_DIR: str = ""
    BACKUP_DIR: str = ""
    TMP_DIR: str = ""
    EPG_DIR: str = ""

    # GeoIP
    GEOIP_DB_PATH: str = ""
    # Comma-separated ISO 3166-1 alpha-2 codes; empty = no country restriction (allow all).
    STREAMING_ALLOW_COUNTRIES: str = ""

    # Restream detection (X-Restream-Detect header)
    STREAMING_LOG_RESTREAM_DETECT: bool = True
    STREAMING_BLOCK_RESTREAM_DETECT: bool = False

    # HMAC stream token validation (skew window around expiry epoch)
    STREAMING_HMAC_MAX_SKEW_SECONDS: int = 300

    # DRM provider
    DRM_PROVIDER_MODE: str = "off"  # off | static | http
    DRM_PROVIDER_URL: str = ""
    DRM_PROVIDER_TOKEN: str = ""
    DRM_PROVIDER_TIMEOUT_SECONDS: int = 5
    DRM_STATIC_KEYS_JSON: str = ""

    # Nginx
    NGINX_BIN: str = "/usr/sbin/nginx"
    NGINX_CONF_DIR: str = ""

    class Config:
        env_file = ".env"
        env_prefix = "IPTV_"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.CONTENT_DIR:
            self.CONTENT_DIR = os.path.join(self.BASE_DIR, "content")
        if not self.BACKUP_DIR:
            self.BACKUP_DIR = os.path.join(self.BASE_DIR, "backups")
        if not self.TMP_DIR:
            self.TMP_DIR = os.path.join(self.BASE_DIR, "tmp")
        if not self.EPG_DIR:
            self.EPG_DIR = os.path.join(self.CONTENT_DIR, "epg")
        if not self.DATABASE_URL:
            self.DATABASE_URL = f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


settings = Settings()
