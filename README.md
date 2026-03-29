# StreamRev - IPTV Panel

**Open-source IPTV management platform** with Xtream Codes compatible API, live/VOD streaming, admin/reseller panels, load balancing, EPG, transcoding, and more.

Built with Python (FastAPI) for high performance, modern architecture, and easy deployment.

---

## Features

- **Live Streaming** - Proxy, redirect, or transcode live TV channels via FFmpeg
- **Video on Demand (VOD)** - Movies and TV Series management with metadata
- **Xtream Codes Compatible API** - Works with TiviMate, XCIPTV, GSE Smart, VLC, and all Xtream-compatible players
- **Admin Panel** - Modern dark-themed web UI with full CRUD for all entities
- **Reseller System** - Credit-based reseller panel for user management
- **User Management** - Subscriber accounts with expiration, connection limits, IP restrictions
- **EPG (Electronic Program Guide)** - XMLTV import and per-channel program listings
- **Load Balancing** - Multi-server architecture with proxy selection
- **Categories & Bouquets** - Organize channels into categories and subscription packages
- **Transcoding** - FFmpeg-based transcoding with custom profiles
- **HLS Delivery** - HTTP Live Streaming segment generation and delivery
- **Module System** - Pluggable modules (TMDB metadata, Plex integration, etc.)
- **Connection Limiting** - Per-user max connections enforcement
- **GeoIP Support** - Geographic filtering and logging
- **Timeshift/Catchup** - TV archive support (configurable per stream)
- **CLI Tools** - Cron jobs, watchdog, monitoring, backup utilities
- **Systemd Integration** - Service management and auto-restart

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python 3.9+ / FastAPI |
| Database | MySQL/MariaDB via SQLAlchemy |
| Cache | Redis (KeyDB compatible) |
| Transcoding | FFmpeg (any version) |
| Web Server | Uvicorn (ASGI) |
| Frontend | Vanilla JS SPA (no framework dependencies) |

## Quick Install

```bash
# 1. Clone the repository
git clone https://github.com/obscuremind/StreamRev.git
cd StreamRev

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the installer
python install.py

# 4. Start the server
PYTHONPATH=$(pwd) python -m uvicorn src.main:app --host 0.0.0.0 --port 8000
```

## Configuration

Configuration is done via environment variables or a `.env` file in the project root:

| Variable | Default | Description |
|----------|---------|-------------|
| `IPTV_SECRET_KEY` | (generated) | JWT signing key |
| `IPTV_DB_HOST` | `localhost` | Database host |
| `IPTV_DB_PORT` | `3306` | Database port |
| `IPTV_DB_USER` | `iptv` | Database user |
| `IPTV_DB_PASSWORD` | `iptv` | Database password |
| `IPTV_DB_NAME` | `iptv_panel` | Database name |
| `IPTV_REDIS_HOST` | `localhost` | Redis host |
| `IPTV_REDIS_PORT` | `6379` | Redis port |
| `IPTV_SERVER_PORT` | `8000` | HTTP server port |
| `IPTV_FFMPEG_PATH` | `/usr/bin/ffmpeg` | Path to FFmpeg binary |
| `IPTV_FFPROBE_PATH` | `/usr/bin/ffprobe` | Path to FFprobe binary |

## Service Management

```bash
# Using systemd (after install)
sudo systemctl start iptv-panel
sudo systemctl stop iptv-panel
sudo systemctl restart iptv-panel
sudo systemctl status iptv-panel

# Direct
PYTHONPATH=$(pwd) uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## CLI Commands

```bash
PYTHONPATH=$(pwd) python -m src.cli.console <command>

# Service
startup              Initialize and start all services
monitor              Monitor active streams and connections
watchdog             Watch and restart failed streams

# Cron Jobs
cron:streams         Streams maintenance
cron:users           Expire/disable users
cron:epg             EPG cleanup
cron:cache           Cache refresh
cron:servers         Server health check
cron:backups         Run backup

# Admin
cmd:migrate          Run database migrations
cmd:create-admin     Create admin user
cmd:reset-admin      Reset admin password
cmd:import-epg       Import EPG from XMLTV URL
cmd:stats            Show system statistics

# XC_VM compatibility helpers
service              Show service status wrapper
update               Run update/migration wrapper
```

## API Endpoints

### Admin API (`/api/admin/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/admin/auth/login` | Admin login |
| GET | `/api/admin/dashboard/summary` | Dashboard statistics |
| CRUD | `/api/admin/streams` | Live streams management |
| CRUD | `/api/admin/users` | User management |
| CRUD | `/api/admin/vod/movies` | Movie management |
| CRUD | `/api/admin/vod/series` | Series management |
| CRUD | `/api/admin/categories` | Category management |
| CRUD | `/api/admin/bouquets` | Bouquet management |
| CRUD | `/api/admin/servers` | Server management |
| CRUD | `/api/admin/epg` | EPG management |
| CRUD | `/api/admin/resellers` | Reseller management |
| CRUD | `/api/admin/lines/packages` | Package management |
| CRUD | `/api/admin/settings` | System settings |
| GET | `/api/admin/lines` | Active connections |

### Reseller API (`/api/reseller/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/reseller/login` | Reseller login |
| GET | `/api/reseller/info` | Reseller info |
| GET | `/api/reseller/users` | List users |
| POST | `/api/reseller/users/create` | Create user (costs credits) |
| POST | `/api/reseller/users/extend` | Extend user subscription |
| GET | `/api/reseller/packages` | Available packages |

### Player API (Xtream Codes Compatible)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/player_api.php?username=X&password=Y` | Auth + server info |
| GET | `/player_api.php?...&action=get_live_categories` | Live categories |
| GET | `/player_api.php?...&action=get_live_streams` | Live streams |
| GET | `/player_api.php?...&action=get_vod_categories` | VOD categories |
| GET | `/player_api.php?...&action=get_vod_streams` | VOD streams |
| GET | `/player_api.php?...&action=get_series` | TV Series |
| GET | `/player_api.php?...&action=get_series_info` | Series info + episodes |
| GET | `/player_api.php?...&action=get_short_epg` | Short EPG for channel |
| GET | `/get.php?username=X&password=Y&type=m3u_plus` | M3U playlist |
| GET | `/xmltv.php?username=X&password=Y` | EPG in XMLTV format |

### Streaming

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/live/{user}/{pass}/{stream_id}.ts` | Live stream (TS) |
| GET | `/live/{user}/{pass}/{stream_id}.m3u8` | Live stream (HLS) |
| GET | `/movie/{user}/{pass}/{movie_id}.mp4` | VOD playback |
| GET | `/series/{user}/{pass}/{episode_id}.mp4` | Series playback |
| GET | `/hls/{stream_id}/index.m3u8` | HLS playlist |
| GET | `/hls/{stream_id}/{segment}.ts` | HLS segment |

## Feature Maturity

- **Implemented:** Core admin/player APIs, authentication, base stream delivery, module loading, diagnostics.
- **Implemented (baseline):** DRM key-provider modes (`off`, `static`, `http`) and orchestrated worker scaffolding (`queue`, `scheduler`, `migrations`).
- **Partial:** XC_VM service parity, bootstrap semantic parity, and full provisioning/installer equivalence.

## XC_VM Compatibility

StreamRev now ships XC_VM-aligned runtime directories and entrypoints to simplify migration:

- Runtime dirs under `src/`: `backups`, `content`, `signals`, `tmp`, `www`
- Compatibility dirs: `includes`, `infrastructure`, `migrations`, `bin`, `ministra`
- Compatibility entrypoints: `python -m src.bootstrap`, `python -m src.service`, `python -m src.update`

This keeps StreamRev architecture in Python while preserving XC_VM-like operational layout.

**DRM scope note:** `/live/.../key` now supports provider modes `off`, `static`, and `http` via environment configuration.

## Project Structure

```
StreamRev/
├── src/
│   ├── main.py                    # FastAPI application entry point
│   ├── core/                      # Core infrastructure
│   │   ├── auth/                  # JWT, password hashing
│   │   ├── cache/                 # Redis cache layer
│   │   ├── config/                # Application settings
│   │   ├── database/              # SQLAlchemy setup
│   │   ├── events/                # Event dispatcher
│   │   ├── logging/               # Logging setup
│   │   ├── module/                # Module loader
│   │   ├── process/               # Process management
│   │   ├── util/                  # Utilities (network, encryption, time)
│   │   └── validation/            # Input validation
│   ├── domain/                    # Business logic
│   │   ├── models.py              # All SQLAlchemy models
│   │   ├── stream/                # Stream service
│   │   ├── user/                  # User service
│   │   ├── vod/                   # Movie/Series service
│   │   ├── epg/                   # EPG service
│   │   ├── bouquet/               # Bouquet service
│   │   ├── category/              # Category service
│   │   ├── server/                # Server + settings service
│   │   └── line/                  # Lines, packages, resellers
│   ├── streaming/                 # Streaming engine
│   │   ├── engine.py              # FFmpeg process management
│   │   ├── auth/                  # Stream authentication
│   │   ├── balancer/              # Load balancer / proxy selector
│   │   ├── delivery/              # HLS handler
│   │   └── protection/            # Connection limiter
│   ├── public/                    # HTTP layer
│   │   ├── controllers/
│   │   │   ├── admin/             # Admin API routes
│   │   │   ├── api/               # Player API + streaming routes
│   │   │   └── reseller/          # Reseller API routes
│   │   ├── views/admin/           # Admin SPA (HTML/CSS/JS)
│   │   └── static/                # Static assets
│   ├── cli/                       # CLI tools
│   │   └── console.py             # Command runner
│   ├── modules/                   # Optional modules
│   │   ├── tmdb/                  # TMDB metadata fetcher
│   │   └── plex/                  # Plex integration
│   ├── content/                   # Media content storage
│   ├── backups/                   # Backup storage
│   └── config/                    # Runtime configuration
├── install.py                     # Installation script
├── requirements.txt               # Python dependencies
└── .env                           # Configuration (generated by installer)
```

## Server Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 4 cores | 6+ cores (Xeon/Ryzen) |
| RAM | 8 GB | 16-32 GB |
| Disk | 100 GB SSD | 480+ GB NVMe |
| Network | 100 Mbps | 1 Gbps dedicated |
| OS | Ubuntu 22.04+ | Ubuntu 24.04 LTS |
| Python | 3.9+ | 3.11+ |

## Modules

StreamRev supports a pluggable module system. Modules are placed in `src/modules/` and auto-discovered.

| Module | Description | Status |
|--------|-------------|--------|
| TMDB | Movie/Series metadata from TheMovieDB | Included |
| Plex | Plex library integration | Stub |

Create custom modules by implementing `ModuleInterface` from `src.core.module.loader`.

## License

AGPL v3.0

## Disclaimer

This software is for educational and legitimate streaming purposes only. You are solely responsible for how it is used.
