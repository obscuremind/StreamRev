import re
from typing import Optional


def validate_url(url: str) -> bool:
    pattern = re.compile(
        r'^https?://'
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return bool(pattern.match(url))


def validate_stream_url(url: str) -> bool:
    if not url:
        return False
    allowed_schemes = ('http://', 'https://', 'rtmp://', 'rtsp://', 'rtp://', 'udp://', 'mmsh://')
    return any(url.startswith(s) for s in allowed_schemes)


def validate_username(username: str) -> Optional[str]:
    if not username or len(username) < 3:
        return "Username must be at least 3 characters"
    if len(username) > 50:
        return "Username must be at most 50 characters"
    if not re.match(r'^[a-zA-Z0-9_.-]+$', username):
        return "Username can only contain letters, numbers, dots, dashes and underscores"
    return None


def validate_password(password: str) -> Optional[str]:
    if not password or len(password) < 6:
        return "Password must be at least 6 characters"
    return None


def sanitize_string(value: str) -> str:
    return re.sub(r'[<>"\'&;]', '', value).strip()
