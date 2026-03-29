"""SQLAlchemy 2.0 domain models for an IPTV panel (XC_VM / Xtream Codes–style)."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database.connection import Base


def _utcnow() -> datetime:
    return datetime.utcnow()


class StreamCategory(Base):
    """Channel / VOD categories with optional hierarchy."""

    __tablename__ = "stream_categories"
    __table_args__ = (
        Index("ix_stream_categories_parent_id", "parent_id"),
        Index("ix_stream_categories_category_type", "category_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    category_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="live"
    )  # live / movie / series / radio
    parent_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("stream_categories.id", ondelete="SET NULL"), nullable=True
    )
    order: Mapped[int] = mapped_column("order", Integer, nullable=False, default=0)

    parent: Mapped[Optional["StreamCategory"]] = relationship(
        "StreamCategory",
        remote_side="StreamCategory.id",
        back_populates="children",
    )
    children: Mapped[List["StreamCategory"]] = relationship(
        "StreamCategory",
        back_populates="parent",
        foreign_keys=[parent_id],
    )
    streams: Mapped[List["Stream"]] = relationship(
        "Stream", back_populates="category", foreign_keys="Stream.category_id"
    )
    movies: Mapped[List["Movie"]] = relationship("Movie", back_populates="category")
    series_list: Mapped[List["Series"]] = relationship(
        "Series", back_populates="category"
    )


class Server(Base):
    """Streaming / panel server nodes (load-balanced hierarchy)."""

    __tablename__ = "servers"
    __table_args__ = (
        Index("ix_servers_parent_id", "parent_id"),
        Index("ix_servers_status", "status"),
        Index("ix_servers_is_main", "is_main"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    server_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    server_ip: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    server_hardware_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    domain_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    http_port: Mapped[int] = mapped_column(Integer, nullable=False, default=80)
    https_port: Mapped[int] = mapped_column(Integer, nullable=False, default=443)
    rtmp_port: Mapped[int] = mapped_column(Integer, nullable=False, default=1935)
    server_protocol: Mapped[str] = mapped_column(
        String(16), nullable=False, default="http"
    )  # http / https
    vpn_ip: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    total_clients: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_main: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )  # 0 offline, 1 online
    parent_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("servers.id", ondelete="SET NULL"), nullable=True
    )
    network_guaranteed_speed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_bandwidth_usage: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ssh_port: Mapped[int] = mapped_column(Integer, nullable=False, default=22)
    ssh_user: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    ssh_password: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    server_key: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timeshift_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rtmp_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    enable_geoip: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    parent: Mapped[Optional["Server"]] = relationship(
        "Server",
        remote_side="Server.id",
        back_populates="children",
    )
    children: Mapped[List["Server"]] = relationship(
        "Server",
        back_populates="parent",
        foreign_keys=[parent_id],
    )
    server_streams: Mapped[List["ServerStream"]] = relationship(
        "ServerStream", back_populates="server", cascade="all, delete-orphan"
    )
    lines: Mapped[List["Line"]] = relationship(
        "Line", back_populates="server", foreign_keys="Line.server_id"
    )
    user_activities: Mapped[List["UserActivity"]] = relationship(
        "UserActivity", back_populates="server"
    )
    stream_logs: Mapped[List["StreamLog"]] = relationship(
        "StreamLog", back_populates="server"
    )
    forced_users: Mapped[List["User"]] = relationship(
        "User",
        back_populates="force_server",
        foreign_keys="User.force_server_id",
    )
    packages_forced: Mapped[List["Package"]] = relationship(
        "Package",
        back_populates="force_server",
        foreign_keys="Package.force_server_id",
    )
    proxies: Mapped[List["Proxy"]] = relationship(
        "Proxy",
        back_populates="server",
        foreign_keys="Proxy.server_id",
    )


class Stream(Base):
    """Live / created live / movie / radio stream definitions."""

    __tablename__ = "streams"
    __table_args__ = (
        Index("ix_streams_category_id", "category_id"),
        Index("ix_streams_enabled", "enabled"),
        Index("ix_streams_stream_type", "type"),
        Index("ix_streams_tv_archive_server_id", "tv_archive_server_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stream_display_name: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    stream_source: Mapped[str] = mapped_column(
        Text, nullable=False, default="[]"
    )  # JSON array of URLs
    stream_icon: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    epg_channel_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    added: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow
    )
    category_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("stream_categories.id", ondelete="SET NULL"), nullable=True
    )
    custom_ffmpeg: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    custom_sid: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    stream_all: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    stream_type: Mapped[int] = mapped_column(
        "type",
        Integer,
        nullable=False,
        default=1,
    )  # 1 live, 2 created_live, 3 movie, 4 radio, 5 created_vod
    target_container: Mapped[str] = mapped_column(
        String(16), nullable=False, default="ts"
    )  # ts / m3u8 / rtmp
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    direct_source: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    read_native: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    allow_record: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    probed_resolution: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    current_source: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tv_archive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    tv_archive_duration: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )  # days
    tv_archive_server_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("servers.id", ondelete="SET NULL"), nullable=True
    )
    transcode_profile_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("profiles.profile_id", ondelete="SET NULL"), nullable=True
    )
    order: Mapped[int] = mapped_column("order", Integer, nullable=False, default=0)

    category: Mapped[Optional["StreamCategory"]] = relationship(
        "StreamCategory", back_populates="streams"
    )
    tv_archive_server: Mapped[Optional["Server"]] = relationship(
        "Server",
        foreign_keys=[tv_archive_server_id],
    )
    transcode_profile: Mapped[Optional["TranscodeProfile"]] = relationship(
        "TranscodeProfile",
        back_populates="streams",
    )
    server_streams: Mapped[List["ServerStream"]] = relationship(
        "ServerStream", back_populates="stream", cascade="all, delete-orphan"
    )
    lines: Mapped[List["Line"]] = relationship(
        "Line", back_populates="stream", foreign_keys="Line.stream_id"
    )
    user_activities: Mapped[List["UserActivity"]] = relationship(
        "UserActivity", back_populates="stream"
    )
    stream_logs: Mapped[List["StreamLog"]] = relationship(
        "StreamLog", back_populates="stream", cascade="all, delete-orphan"
    )
    epg_programs: Mapped[List["EpgData"]] = relationship(
        "EpgData",
        back_populates="channel",
        foreign_keys="EpgData.channel_id",
    )


class User(Base):
    """IPTV end users / subscribers."""

    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_enabled", "enabled"),
        Index("ix_users_force_server_id", "force_server_id"),
        Index("ix_users_member_group_id", "member_group_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password: Mapped[str] = mapped_column(Text, nullable=False, default="")
    player_api_token: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True, unique=True
    )
    exp_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    max_connections: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_trial: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    admin_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reseller_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow
    )
    allowed_ips: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    allowed_user_agents: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_restreamer: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    force_server_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("servers.id", ondelete="SET NULL"), nullable=True
    )
    bouquet: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # comma-separated bouquet IDs
    allowed_output_ids: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_stalker: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_mag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by_reseller_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("resellers.id", ondelete="SET NULL"), nullable=True
    )
    member_group_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users_groups.group_id", ondelete="SET NULL"), nullable=True
    )

    force_server: Mapped[Optional["Server"]] = relationship(
        "Server",
        back_populates="forced_users",
        foreign_keys=[force_server_id],
    )
    lines: Mapped[List["Line"]] = relationship(
        "Line", back_populates="user", cascade="all, delete-orphan"
    )
    activities: Mapped[List["UserActivity"]] = relationship(
        "UserActivity",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    member_group: Mapped[Optional["UserGroup"]] = relationship(
        "UserGroup",
        back_populates="users",
        foreign_keys=[member_group_id],
    )
    enigma2_devices: Mapped[List["Enigma2Device"]] = relationship(
        "Enigma2Device",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    mag_devices: Mapped[List["MagDevice"]] = relationship(
        "MagDevice",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    tickets: Mapped[List["Ticket"]] = relationship(
        "Ticket",
        back_populates="user",
    )


class Line(Base):
    """Active subscriber lines / connections."""

    __tablename__ = "lines"
    __table_args__ = (
        Index("ix_lines_user_id", "user_id"),
        Index("ix_lines_server_id", "server_id"),
        Index("ix_lines_stream_id", "stream_id"),
        Index("ix_lines_date", "date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    server_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("servers.id", ondelete="CASCADE"), nullable=False
    )
    stream_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("streams.id", ondelete="CASCADE"), nullable=False
    )
    container: Mapped[str] = mapped_column(
        String(16), nullable=False, default="ts"
    )  # ts / m3u8 / rtmp
    pid: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    user_ip: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    geoip_country_code: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    bitrate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    external_device: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="lines")
    server: Mapped["Server"] = relationship("Server", back_populates="lines")
    stream: Mapped["Stream"] = relationship("Stream", back_populates="lines")


class Bouquet(Base):
    """Channel / VOD packages."""

    __tablename__ = "bouquets"
    __table_args__ = (Index("ix_bouquets_bouquet_order", "bouquet_order"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bouquet_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    bouquet_channels: Mapped[str] = mapped_column(
        Text, nullable=False, default="[]"
    )  # JSON stream IDs
    bouquet_movies: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    bouquet_radios: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    bouquet_series: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    bouquet_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class ServerStream(Base):
    """Per-server stream state (many-to-many with attributes)."""

    __tablename__ = "server_streams"
    __table_args__ = (
        UniqueConstraint("server_id", "stream_id", name="uq_server_streams_server_stream"),
        Index("ix_server_streams_server_id", "server_id"),
        Index("ix_server_streams_stream_id", "stream_id"),
        Index("ix_server_streams_stream_status", "stream_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    server_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("servers.id", ondelete="CASCADE"), nullable=False
    )
    stream_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("streams.id", ondelete="CASCADE"), nullable=False
    )
    pid: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    on_demand: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    stream_status: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )  # 0 off, 1 on, 2 starting, 3 stopping
    bitrate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    current_source: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    server: Mapped["Server"] = relationship("Server", back_populates="server_streams")
    stream: Mapped["Stream"] = relationship("Stream", back_populates="server_streams")


class EpgData(Base):
    """Electronic program guide rows."""

    __tablename__ = "epg_data"
    __table_args__ = (
        Index("ix_epg_data_epg_id", "epg_id"),
        Index("ix_epg_data_channel_id", "channel_id"),
        Index("ix_epg_data_start_end", "start", "end"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    epg_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    lang: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    channel_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("streams.id", ondelete="CASCADE"), nullable=True
    )

    channel: Mapped[Optional["Stream"]] = relationship(
        "Stream",
        back_populates="epg_programs",
        foreign_keys=[channel_id],
    )


class Movie(Base):
    """Video on demand (movies)."""

    __tablename__ = "movies"
    __table_args__ = (Index("ix_movies_category_id", "category_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stream_display_name: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    stream_source: Mapped[str] = mapped_column(Text, nullable=False, default="")
    stream_icon: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rating: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    rating_5based: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    category_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("stream_categories.id", ondelete="SET NULL"), nullable=True
    )
    container_extension: Mapped[str] = mapped_column(
        String(16), nullable=False, default="mkv"
    )  # mkv / mp4 / avi
    custom_sid: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    added: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow
    )
    direct_source: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    target_container: Mapped[str] = mapped_column(
        String(16), nullable=False, default="ts"
    )
    tmdb_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    plot: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cast: Mapped[Optional[str]] = mapped_column("cast", Text, nullable=True)
    director: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    genre: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    release_date: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    episode_run_time: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    youtube_trailer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    backdrop_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    category: Mapped[Optional["StreamCategory"]] = relationship(
        "StreamCategory", back_populates="movies"
    )


class Series(Base):
    """TV series metadata."""

    __tablename__ = "series"
    __table_args__ = (Index("ix_series_category_id", "category_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    category_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("stream_categories.id", ondelete="SET NULL"), nullable=True
    )
    cover: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    plot: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cast: Mapped[Optional[str]] = mapped_column("cast", Text, nullable=True)
    director: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    genre: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    release_date: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    rating: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    rating_5based: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    backdrop_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    youtube_trailer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tmdb_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    last_modified: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow, onupdate=_utcnow
    )

    category: Mapped[Optional["StreamCategory"]] = relationship(
        "StreamCategory", back_populates="series_list"
    )
    episodes: Mapped[List["SeriesEpisode"]] = relationship(
        "SeriesEpisode",
        back_populates="series",
        cascade="all, delete-orphan",
    )


class SeriesEpisode(Base):
    """Episodes belonging to a series."""

    __tablename__ = "series_episodes"
    __table_args__ = (
        Index("ix_series_episodes_series_id", "series_id"),
        Index("ix_series_episodes_season_episode", "series_id", "season_number", "episode_number"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    series_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("series.id", ondelete="CASCADE"), nullable=False
    )
    season_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    episode_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    stream_display_name: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    stream_source: Mapped[str] = mapped_column(Text, nullable=False, default="")
    container_extension: Mapped[str] = mapped_column(
        String(16), nullable=False, default="mkv"
    )
    custom_sid: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    added: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow
    )
    direct_source: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    tmdb_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    plot: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    rating: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    movie_image: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    bitrate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    series: Mapped["Series"] = relationship("Series", back_populates="episodes")


class Package(Base):
    """Reseller subscription packages."""

    __tablename__ = "packages"
    __table_args__ = (Index("ix_packages_force_server_id", "force_server_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    package_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    is_trial: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_official: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    trial_credits: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    official_credits: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    trial_duration: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    official_duration: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_connections: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    allowed_bouquets: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    allowed_output_types: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    can_general_edit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    activity_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    only_mag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    only_enigma: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    force_server_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("servers.id", ondelete="SET NULL"), nullable=True
    )
    max_sub_resellers: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    only_stalker: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    force_server: Mapped[Optional["Server"]] = relationship(
        "Server",
        back_populates="packages_forced",
        foreign_keys=[force_server_id],
    )


class Reseller(Base):
    """Reseller panel accounts."""

    __tablename__ = "resellers"
    __table_args__ = (
        Index("ix_resellers_owner_id", "owner_id"),
        Index("ix_resellers_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password: Mapped[str] = mapped_column(Text, nullable=False, default="")
    owner_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("resellers.id", ondelete="SET NULL"), nullable=True
    )
    credits: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1
    )  # 0 disabled, 1 enabled
    allowed_ips: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    max_credits: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    allowed_packages: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    owner: Mapped[Optional["Reseller"]] = relationship(
        "Reseller",
        remote_side="Reseller.id",
        back_populates="sub_resellers",
        foreign_keys=[owner_id],
    )
    sub_resellers: Mapped[List["Reseller"]] = relationship(
        "Reseller",
        back_populates="owner",
        foreign_keys=[owner_id],
    )


class UserActivity(Base):
    """Historical user playback / connection activity."""

    __tablename__ = "user_activity"
    __table_args__ = (
        Index("ix_user_activity_user_id", "user_id"),
        Index("ix_user_activity_stream_id", "stream_id"),
        Index("ix_user_activity_server_id", "server_id"),
        Index("ix_user_activity_date_start", "date_start"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    stream_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("streams.id", ondelete="CASCADE"), nullable=False
    )
    server_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("servers.id", ondelete="CASCADE"), nullable=False
    )
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    user_ip: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    container: Mapped[str] = mapped_column(
        String(16), nullable=False, default="ts"
    )
    date_start: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow
    )
    date_stop: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    geoip_country_code: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="activities")
    stream: Mapped["Stream"] = relationship("Stream", back_populates="user_activities")
    server: Mapped["Server"] = relationship("Server", back_populates="user_activities")


class StreamLog(Base):
    """Per-stream operational logs on a server."""

    __tablename__ = "stream_logs"
    __table_args__ = (
        Index("ix_stream_logs_stream_id", "stream_id"),
        Index("ix_stream_logs_server_id", "server_id"),
        Index("ix_stream_logs_date", "date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stream_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("streams.id", ondelete="CASCADE"), nullable=False
    )
    server_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("servers.id", ondelete="CASCADE"), nullable=False
    )
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)
    info: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    log_type: Mapped[Optional[str]] = mapped_column("type", String(64), nullable=True)

    stream: Mapped["Stream"] = relationship("Stream", back_populates="stream_logs")
    server: Mapped["Server"] = relationship("Server", back_populates="stream_logs")


class Setting(Base):
    """Key-value system settings."""

    __tablename__ = "settings"
    __table_args__ = ()

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    value_type: Mapped[str] = mapped_column(
        "type",
        String(16),
        nullable=False,
        default="string",
    )  # string / int / bool / json


class AccessCode(Base):
    """Alternative authentication codes (XC_VM access_codes)."""

    __tablename__ = "access_codes"
    __table_args__ = (
        Index("ix_access_codes_enabled", "enabled"),
        Index("ix_access_codes_type", "type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    code_type: Mapped[int] = mapped_column("type", Integer, nullable=False, default=1)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    max_connections: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    allowed_ips: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    allowed_uas: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    allowed_countries: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)


class HmacKey(Base):
    """HMAC keys for API token authentication."""

    __tablename__ = "hmac_keys"
    __table_args__ = (Index("ix_hmac_keys_enabled", "enabled"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    allowed_ips: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)


class UserGroup(Base):
    """Subscriber groups (users_groups)."""

    __tablename__ = "users_groups"

    group_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    can_delete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    packages: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    users: Mapped[List["User"]] = relationship(
        "User",
        back_populates="member_group",
        foreign_keys="User.member_group_id",
    )


class Enigma2Device(Base):
    """Enigma2 device registry (token, MAC, status)."""

    __tablename__ = "enigma2_devices"
    __table_args__ = (
        Index("ix_enigma2_devices_user_id", "user_id"),
        Index("ix_enigma2_devices_mac", "mac"),
        Index("ix_enigma2_devices_enabled", "enabled"),
    )

    device_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    mac: Mapped[str] = mapped_column(String(32), nullable=False)
    original_mac: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    modem_mac: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    key_auth: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    local_ip: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    public_ip: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    enigma_version: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    cpu: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    lversion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    dns: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    lock_device: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    watchdog_timeout: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    last_updated: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    rc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    user: Mapped["User"] = relationship("User", back_populates="enigma2_devices")
    actions: Mapped[List["Enigma2Action"]] = relationship(
        "Enigma2Action",
        back_populates="device",
        cascade="all, delete-orphan",
    )


class Enigma2Action(Base):
    """Pending command queue for Enigma2 devices."""

    __tablename__ = "enigma2_actions"
    __table_args__ = (Index("ix_enigma2_actions_device_id", "device_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("enigma2_devices.device_id", ondelete="CASCADE"), nullable=False
    )
    key: Mapped[str] = mapped_column(String(64), nullable=False)
    command: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    command2: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    action_type: Mapped[Optional[str]] = mapped_column("type", String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)

    device: Mapped["Enigma2Device"] = relationship("Enigma2Device", back_populates="actions")


class StreamType(Base):
    """Stream type definitions (live / movie / radio, etc.)."""

    __tablename__ = "stream_types"
    __table_args__ = (Index("ix_stream_types_type_key", "type_key"),)

    type_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    type_name: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    type_key: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    type_output: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    live: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Proxy(Base):
    """HTTP proxies for upstream stream fetching."""

    __tablename__ = "proxies"
    __table_args__ = (
        Index("ix_proxies_server_id", "server_id"),
        Index("ix_proxies_enabled", "enabled"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    proxy_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    proxy_url: Mapped[str] = mapped_column(Text, nullable=False, default="")
    proxy_type: Mapped[str] = mapped_column(String(32), nullable=False, default="http")
    proxy_username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    proxy_password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    server_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("servers.id", ondelete="SET NULL"), nullable=True
    )

    server: Mapped[Optional["Server"]] = relationship(
        "Server",
        back_populates="proxies",
        foreign_keys=[server_id],
    )


class BlockedUserAgent(Base):
    """Blocked user-agent patterns."""

    __tablename__ = "blocked_uas"
    __table_args__ = (Index("ix_blocked_uas_enabled", "enabled"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pattern: Mapped[str] = mapped_column(String(512), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)


class BlockedIP(Base):
    """Persistent DB-backed blocked IPs."""

    __tablename__ = "blocked_ips"
    __table_args__ = (
        Index("ix_blocked_ips_ip", "ip"),
        Index("ix_blocked_ips_enabled", "enabled"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ip: Mapped[str] = mapped_column(String(64), nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)


class MagDevice(Base):
    """MAG STB device registry (hardware separate from user account)."""

    __tablename__ = "mag_devices"

    mag_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    mac: Mapped[str] = mapped_column(String(32), nullable=False)
    sn: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    ip: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    ver: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    stb_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    lock_device: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_updated: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    user: Mapped["User"] = relationship("User", back_populates="mag_devices")


class TranscodeProfile(Base):
    """Transcoding profiles for streams."""

    __tablename__ = "profiles"
    __table_args__ = (Index("ix_profiles_enabled", "enabled"),)

    profile_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    profile_command: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    profile_type: Mapped[str] = mapped_column(String(32), nullable=False, default="live")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    streams: Mapped[List["Stream"]] = relationship(
        "Stream",
        back_populates="transcode_profile",
    )


class ClientLog(Base):
    """Client-side event logs."""

    __tablename__ = "client_logs"
    __table_args__ = (
        Index("ix_client_logs_user_id", "user_id"),
        Index("ix_client_logs_date", "date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    stream_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    event: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    ip: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)


class Ticket(Base):
    """Support tickets."""

    __tablename__ = "tickets"
    __table_args__ = (
        Index("ix_tickets_status", "status"),
        Index("ix_tickets_user_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    admin_reply: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    priority: Mapped[str] = mapped_column(String(32), nullable=False, default="normal")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, onupdate=_utcnow
    )

    user: Mapped[Optional["User"]] = relationship("User", back_populates="tickets")


class BlockedASN(Base):
    """ASN database for ISP/hosting detection."""

    __tablename__ = "blocked_asns"
    __table_args__ = (Index("ix_blocked_asns_blocked", "blocked"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asn: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    isp: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    domain: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    num_ips: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    asn_type: Mapped[Optional[str]] = mapped_column("type", String(64), nullable=True)
    blocked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class BlockedISP(Base):
    """Blocked ISP patterns."""

    __tablename__ = "blocked_isps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    isp_name: Mapped[str] = mapped_column(String(512), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)


class RegisteredUser(Base):
    """Pending/registered users awaiting activation."""

    __tablename__ = "reg_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    password: Mapped[str] = mapped_column(Text, nullable=False, default="")
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ip: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)


class Migration(Base):
    """Database migration tracking."""

    __tablename__ = "migrations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    migration: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    applied_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)


class StreamQueue(Base):
    """Stream processing queue entries."""

    __tablename__ = "stream_queue"
    __table_args__ = (
        Index("ix_stream_queue_status", "status"),
        Index("ix_stream_queue_stream_id", "stream_id"),
        Index("ix_stream_queue_server_id", "server_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stream_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("streams.id", ondelete="CASCADE"), nullable=False
    )
    server_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("servers.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending"
    )  # pending / processing / completed / failed
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    stream: Mapped["Stream"] = relationship("Stream", foreign_keys=[stream_id])
    server: Mapped["Server"] = relationship("Server", foreign_keys=[server_id])


class AuditLog(Base):
    """Admin action audit log."""

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_admin_id", "admin_id"),
        Index("ix_audit_logs_action", "action"),
        Index("ix_audit_logs_entity", "entity_type", "entity_id"),
        Index("ix_audit_logs_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    admin_id: Mapped[int] = mapped_column(Integer, nullable=False)
    admin_username: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    action: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    entity_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)


class ScheduledRecording(Base):
    """Scheduled stream recordings."""

    __tablename__ = "scheduled_recordings"
    __table_args__ = (
        Index("ix_scheduled_recordings_stream_id", "stream_id"),
        Index("ix_scheduled_recordings_status", "status"),
        Index("ix_scheduled_recordings_start_time", "start_time"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stream_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("streams.id", ondelete="CASCADE"), nullable=False
    )
    start_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="scheduled"
    )  # scheduled / recording / completed / failed / archived
    output_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)

    stream: Mapped["Stream"] = relationship("Stream", foreign_keys=[stream_id])


class QueueJob(Base):
    """XC_VM-compatible queue table."""

    __tablename__ = "queue"
    __table_args__ = (Index("ix_queue_server_id", "server_id"), Index("ix_queue_stream_id", "stream_id"))

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    queue_type: Mapped[Optional[str]] = mapped_column("type", String(32), nullable=True)
    server_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    stream_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    pid: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    added: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class Signal(Base):
    """XC_VM-compatible process signal/event table."""

    __tablename__ = "signals"
    __table_args__ = (Index("ix_signals_server_id", "server_id"), Index("ix_signals_time", "time"))

    id: Mapped[int] = mapped_column("signal_id", Integer, primary_key=True, autoincrement=True)
    pid: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    server_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    rtmp: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    time: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    custom_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cache: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class LoginLog(Base):
    """XC_VM-compatible auth/login attempts log."""

    __tablename__ = "login_logs"
    __table_args__ = (
        Index("ix_login_logs_user_id", "user_id"),
        Index("ix_login_logs_date", "date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    log_type: Mapped[Optional[str]] = mapped_column("type", String(50), nullable=True)
    access_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    login_ip: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    date: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class PanelLog(Base):
    """XC_VM-compatible panel audit/activity log."""

    __tablename__ = "panel_logs"
    __table_args__ = (Index("ix_panel_logs_date", "date"), Index("ix_panel_logs_server_id", "server_id"))

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    log_type: Mapped[str] = mapped_column("type", String(50), nullable=False, default="pdo")
    log_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    log_extra: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    line: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    date: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    server_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    unique_tag: Mapped[Optional[str]] = mapped_column("unique", String(32), nullable=True)
    file: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    env: Mapped[str] = mapped_column(String(32), nullable=False, default="cli")


class StreamServerMap(Base):
    """XC_VM-compatible stream-to-server mapping state."""

    __tablename__ = "streams_servers"
    __table_args__ = (Index("ix_streams_servers_stream_id", "stream_id"), Index("ix_streams_servers_server_id", "server_id"))

    id: Mapped[int] = mapped_column("server_stream_id", Integer, primary_key=True, autoincrement=True)
    stream_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    server_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    parent_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    pid: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    to_analyze: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stream_status: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stream_started: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    stream_info: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    monitor_pid: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    aes_pid: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    current_source: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    bitrate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    progress_info: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cc_info: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    on_demand: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    delay_pid: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    delay_available_at: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ondemand_check: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    pids_create_channel: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cchannel_rsources: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, onupdate=_utcnow)
    compatible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    audio_codec: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    video_codec: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    resolution: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class StreamStat(Base):
    """XC_VM-compatible stream stats snapshots."""

    __tablename__ = "streams_stats"
    __table_args__ = (Index("ix_streams_stats_stream_id", "stream_id"), Index("ix_streams_stats_time", "time"))

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stream_id: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rank: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    time: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    connections: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    users: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stat_type: Mapped[Optional[str]] = mapped_column("type", String(16), nullable=True)
    dateadded: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)


class ServerStat(Base):
    """XC_VM-compatible server stats snapshots."""

    __tablename__ = "servers_stats"
    __table_args__ = (Index("ix_servers_stats_server_id", "server_id"), Index("ix_servers_stats_time", "time"))

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    server_id: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    connections: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    streams: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    users: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cpu: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    cpu_cores: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cpu_avg: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    total_mem: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_mem_free: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_mem_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_mem_used_percent: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    total_disk_space: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    uptime: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    total_running_streams: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    bytes_sent: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    bytes_received: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    bytes_sent_total: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    bytes_received_total: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    cpu_load_average: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    gpu_info: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    iostat_info: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    time: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_users: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
