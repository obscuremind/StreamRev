import hashlib
import secrets
import base64
from typing import Optional


def generate_token(length: int = 32) -> str:
    return secrets.token_hex(length)


def md5_hash(value: str) -> str:
    return hashlib.md5(value.encode()).hexdigest()


def sha256_hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def generate_api_key() -> str:
    return secrets.token_urlsafe(48)


def base64_encode(value: str) -> str:
    return base64.b64encode(value.encode()).decode()


def base64_decode(value: str) -> Optional[str]:
    try:
        return base64.b64decode(value.encode()).decode()
    except Exception:
        return None
