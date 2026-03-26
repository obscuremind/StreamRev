import socket
import struct
from typing import Optional


def get_server_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def ip_to_int(ip: str) -> int:
    return struct.unpack("!I", socket.inet_aton(ip))[0]


def int_to_ip(num: int) -> str:
    return socket.inet_ntoa(struct.pack("!I", num))


def is_valid_ip(ip: str) -> bool:
    try:
        socket.inet_aton(ip)
        return True
    except socket.error:
        return False


def resolve_hostname(hostname: str) -> Optional[str]:
    try:
        return socket.gethostbyname(hostname)
    except socket.gaierror:
        return None
