from enum import Enum


class ErrorCode(Enum):
    AUTH_FAILED = ("AUTH_001", "Authentication failed")
    AUTH_TOKEN_EXPIRED = ("AUTH_002", "Token expired")
    AUTH_PERMISSION_DENIED = ("AUTH_003", "Permission denied")
    USER_NOT_FOUND = ("USER_001", "User not found")
    USER_DISABLED = ("USER_002", "User account is disabled")
    USER_EXPIRED = ("USER_003", "User account has expired")
    USER_MAX_CONNECTIONS = ("USER_004", "Maximum connections reached")
    STREAM_NOT_FOUND = ("STREAM_001", "Stream not found")
    STREAM_OFFLINE = ("STREAM_002", "Stream is offline")
    STREAM_ERROR = ("STREAM_003", "Stream error")
    VOD_NOT_FOUND = ("VOD_001", "VOD content not found")
    SERVER_ERROR = ("SERVER_001", "Internal server error")
    RATE_LIMITED = ("SERVER_002", "Rate limit exceeded")
    INVALID_INPUT = ("INPUT_001", "Invalid input")

    def __init__(self, code: str, message: str):
        self.error_code = code
        self.error_message = message
