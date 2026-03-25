from datetime import datetime, timezone


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def timestamp() -> int:
    return int(datetime.now(timezone.utc).timestamp())


def from_timestamp(ts: int) -> datetime:
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def format_duration(seconds: int) -> str:
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"
