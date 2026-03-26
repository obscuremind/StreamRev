import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any, Dict, Mapping, Optional, Tuple

from cryptography.fernet import Fernet
from sqlalchemy.orm import Session

from src.core.config import settings
from src.core.auth.password import verify_password
from src.domain.models import Bouquet, User, Stream
from src.domain.user.service import UserService

_fernet_singleton: Optional[Fernet] = None


def _stream_fernet() -> Fernet:
    global _fernet_singleton
    if _fernet_singleton is None:
        key = base64.urlsafe_b64encode(
            hashlib.sha256(settings.SECRET_KEY.encode()).digest()
        )
        _fernet_singleton = Fernet(key)
    return _fernet_singleton


def _geoip_country_code(client_ip: Optional[str]) -> Optional[str]:
    """Resolve client IP to ISO country code when GeoIP DB is configured."""
    if not client_ip or client_ip in ("127.0.0.1", "::1", "unknown"):
        return None
    path = (settings.GEOIP_DB_PATH or "").strip()
    if not path or not os.path.isfile(path):
        return None
    try:
        import geoip2.database

        with geoip2.database.Reader(path) as reader:
            return reader.country(client_ip).country.iso_code
    except Exception:
        return None


class StreamAuth:
    def __init__(self, db: Session):
        self.db = db

    def authenticate(self, username: str, password: str) -> Tuple[bool, Optional[User], Optional[str]]:
        user = self.db.query(User).filter(User.username == username).first()
        if not user:
            return False, None, "User not found"
        if not verify_password(password, user.password):
            return False, None, "Invalid password"
        if not user.enabled:
            return False, None, "Account disabled"
        svc = UserService(self.db)
        if svc.is_expired(user):
            return False, None, "Account expired"
        return True, user, None

    def authenticate_by_token(self, token: str) -> Tuple[bool, Optional[User], Optional[str]]:
        """Look up user by player_api_token (XC-style token auth)."""
        t = (token or "").strip()
        if not t:
            return False, None, "Missing token"
        user = self.db.query(User).filter(User.player_api_token == t).first()
        if not user:
            return False, None, "Invalid token"
        if not user.enabled:
            return False, None, "Account disabled"
        svc = UserService(self.db)
        if svc.is_expired(user):
            return False, None, "Account expired"
        return True, user, None

    def validate_hmac(
        self,
        hmac_hash: str,
        expiry: str,
        stream_id: int,
        extension: str,
        client_ip: str,
    ) -> bool:
        """HMAC-SHA256 over expiry|stream_id|extension|client_ip using server secret."""
        try:
            exp_ts = int(expiry)
        except (TypeError, ValueError):
            return False
        now = int(time.time())
        skew = int(getattr(settings, "STREAMING_HMAC_MAX_SKEW_SECONDS", 300) or 300)
        if exp_ts < now - skew:
            return False
        secret = (settings.SECRET_KEY or "").encode()
        msg = f"{expiry}|{stream_id}|{extension}|{client_ip}".encode()
        expected = hmac.new(secret, msg, hashlib.sha256).hexdigest()
        return hmac.compare_digest(
            expected.lower(), (hmac_hash or "").strip().lower()
        )

    def check_output_format_allowed(self, user: User, extension: str) -> bool:
        """
        If allowed_output_ids is set, require format to match.
        Supports XC-style numeric IDs (1=ts, 2=m3u8/hls, 3=rtmp) or names.
        """
        ext = (extension or "ts").lower().strip().lstrip(".")
        if ext == "hls":
            ext = "m3u8"
        if ext not in ("ts", "m3u8", "rtmp"):
            return False
        raw = (user.allowed_output_ids or "").strip()
        if not raw:
            return True
        tokens = [x.strip().lower() for x in raw.split(",") if x.strip()]
        if not tokens:
            return True
        numeric = {"ts": "1", "m3u8": "2", "rtmp": "3"}[ext]
        names = {"ts": ("ts", "mpegts"), "m3u8": ("m3u8", "hls"), "rtmp": ("rtmp",)}[
            ext
        ]
        for t in tokens:
            if t == numeric:
                return True
            if t in names:
                return True
        return False

    @staticmethod
    def check_restream_detection(headers: Mapping[str, str]) -> Optional[str]:
        """Return header value if X-Restream-Detect is present."""
        try:
            v = headers.get("X-Restream-Detect")
            if v is not None and str(v).strip() != "":
                return str(v).strip()
            v = headers.get("x-restream-detect")
            if v is not None and str(v).strip() != "":
                return str(v).strip()
        except Exception:
            pass
        return None

    def check_geoip_allowed(
        self, user: User, client_ip: Optional[str]
    ) -> Tuple[bool, Optional[str]]:
        """Country allowlist from STREAMING_ALLOW_COUNTRIES; GeoIP lookup when DB path set."""
        _ = user
        allow_raw = (getattr(settings, "STREAMING_ALLOW_COUNTRIES", "") or "").strip()
        if not allow_raw:
            return True, None
        codes = {c.strip().upper() for c in allow_raw.split(",") if c.strip()}
        if not codes:
            return True, None
        cc = _geoip_country_code(client_ip)
        if not cc:
            return True, None
        if cc.upper() in codes:
            return True, None
        return False, "GeoIP country not allowed"

    def check_isp_blocked(
        self, user: User, client_ip: Optional[str]
    ) -> Tuple[bool, Optional[str]]:
        """Placeholder for ISP/ASN block rules (e.g. datacenter ASNs)."""
        _ = (user, client_ip)
        return True, None

    def generate_stream_token(
        self,
        user_info: Dict[str, Any],
        stream_info: Dict[str, Any],
        channel_info: Dict[str, Any],
        ttl_seconds: int = 3600,
    ) -> str:
        """Encrypted JSON token for server-to-server handoff."""
        payload = {
            "user": user_info,
            "stream": stream_info,
            "channel": channel_info,
            "iat": int(time.time()),
            "exp": int(time.time()) + int(ttl_seconds),
        }
        raw = json.dumps(payload, separators=(",", ":")).encode()
        return _stream_fernet().encrypt(raw).decode()

    def validate_stream_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Decrypt stream token; return payload or None if invalid/expired."""
        if not token or not str(token).strip():
            return None
        try:
            raw = _stream_fernet().decrypt(token.strip().encode())
            data = json.loads(raw.decode())
            if not isinstance(data, dict):
                return None
            exp = data.get("exp")
            if exp is not None and int(exp) < int(time.time()):
                return None
            return data
        except Exception:
            return None

    def check_bouquet_access(self, user: User, stream_id: int) -> bool:
        """Return True if user may access stream_id based on bouquet channel lists."""
        if user.is_admin:
            return True
        raw = (user.bouquet or "").strip()
        if not raw:
            return True
        bouquet_ids: list[int] = []
        for part in raw.split(","):
            p = part.strip()
            if p.isdigit():
                bouquet_ids.append(int(p))
        if not bouquet_ids:
            return True
        for bid in bouquet_ids:
            b = self.db.query(Bouquet).filter(Bouquet.id == bid).first()
            if not b:
                continue
            try:
                channels = json.loads(b.bouquet_channels or "[]")
            except (json.JSONDecodeError, TypeError):
                continue
            if not isinstance(channels, list):
                continue
            for c in channels:
                try:
                    if int(c) == stream_id:
                        return True
                except (TypeError, ValueError):
                    if c == stream_id:
                        return True
        return False

    def authorize_stream(
        self,
        user: User,
        stream_id: int,
        user_agent: Optional[str] = None,
        client_ip: Optional[str] = None,
        allow_disabled_stream: bool = False,
    ) -> Tuple[bool, Optional[Stream], Optional[str]]:
        stream = self.db.query(Stream).filter(Stream.id == stream_id).first()
        if not stream:
            return False, None, "Stream not found"
        if not stream.enabled and not allow_disabled_stream:
            return False, None, "Stream offline"
        svc = UserService(self.db)
        if not svc.can_connect(user):
            return False, None, "Max connections reached"
        if not self.check_bouquet_access(user, stream_id):
            return False, None, "Stream not in allowed bouquets"
        if user.allowed_user_agents:
            ua = user_agent or ""
            if not self.check_user_agent_allowed(user, ua):
                return False, None, "User-Agent not allowed"
        ok_geo, geo_err = self.check_geoip_allowed(user, client_ip)
        if not ok_geo:
            return False, None, geo_err or "GeoIP not allowed"
        ok_isp, isp_err = self.check_isp_blocked(user, client_ip)
        if not ok_isp:
            return False, None, isp_err or "ISP blocked"
        return True, stream, None

    def check_ip_allowed(self, user: User, ip: str) -> bool:
        if not user.allowed_ips:
            return True
        allowed = [x.strip() for x in user.allowed_ips.split(",") if x.strip()]
        if not allowed:
            return True
        return ip in allowed

    def check_user_agent_allowed(self, user: User, ua: str) -> bool:
        if not user.allowed_user_agents:
            return True
        allowed = [x.strip() for x in user.allowed_user_agents.split(",") if x.strip()]
        if not allowed:
            return True
        return any(a in ua for a in allowed)
