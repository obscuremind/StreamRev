#!/usr/bin/env python3
"""
IPTV Panel Installer
Sets up the application, creates database, and configures services.
"""
import os
import sys
import subprocess
import secrets


def main():
    print("=" * 60)
    print("  IPTV Panel - Installation")
    print("=" * 60)
    print()

    base_dir = os.path.dirname(os.path.abspath(__file__))

    print("[1/6] Checking Python version...")
    if sys.version_info < (3, 9):
        print("ERROR: Python 3.9+ required")
        sys.exit(1)
    print(f"  Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro} - OK")

    print("\n[2/6] Installing Python dependencies...")
    req_file = os.path.join(base_dir, "requirements.txt")
    if os.path.exists(req_file):
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", req_file])
    else:
        print("  WARNING: requirements.txt not found")

    print("\n[3/6] Creating directory structure...")
    dirs = [
        "content/archive", "content/epg", "content/playlists",
        "content/streams", "content/vod", "content/video",
        "backups", "signals", "tmp", "logs",
    ]
    for d in dirs:
        path = os.path.join(base_dir, "src", d)
        os.makedirs(path, exist_ok=True)
        print(f"  Created: {d}")

    print("\n[4/6] Generating configuration...")
    env_file = os.path.join(base_dir, ".env")
    if not os.path.exists(env_file):
        secret = secrets.token_hex(32)
        db_pass = secrets.token_hex(16)
        config = f"""# IPTV Panel Configuration
IPTV_SECRET_KEY={secret}
IPTV_DEBUG=false
IPTV_DB_HOST=localhost
IPTV_DB_PORT=3306
IPTV_DB_USER=iptv
IPTV_DB_PASSWORD={db_pass}
IPTV_DB_NAME=iptv_panel
IPTV_REDIS_HOST=localhost
IPTV_REDIS_PORT=6379
IPTV_SERVER_HOST=0.0.0.0
IPTV_SERVER_PORT=8000
IPTV_SERVER_PROTOCOL=http
IPTV_FFMPEG_PATH=/usr/bin/ffmpeg
IPTV_FFPROBE_PATH=/usr/bin/ffprobe
"""
        with open(env_file, "w") as f:
            f.write(config)
        print(f"  Configuration saved to .env")
        print(f"  DB Password: {db_pass}")
    else:
        print("  .env already exists, skipping")

    print("\n[5/6] Initializing database...")
    try:
        sys.path.insert(0, base_dir)
        from src.core.database import Base, engine
        from src.domain import models
        Base.metadata.create_all(bind=engine)
        print("  Database tables created")

        from src.core.database import SessionLocal
        from src.domain.user.service import UserService
        db = SessionLocal()
        try:
            svc = UserService(db)
            admin = svc.get_by_username("admin")
            if not admin:
                svc.create({
                    "username": "admin", "password": "admin",
                    "is_admin": True, "enabled": True, "max_connections": 1,
                })
                print("  Default admin created: admin/admin")
            else:
                print("  Admin user already exists")
        finally:
            db.close()
    except Exception as e:
        print(f"  WARNING: Database init failed: {e}")
        print("  You can initialize the database later with: python -m src.cli.console cmd:migrate")

    print("\n[6/6] Creating systemd service file...")
    service_content = f"""[Unit]
Description=IPTV Panel
After=network.target mysql.service redis.service

[Service]
Type=simple
User=root
WorkingDirectory={base_dir}
Environment=PYTHONPATH={base_dir}
ExecStart={sys.executable} -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
"""
    service_path = os.path.join(base_dir, "iptv-panel.service")
    with open(service_path, "w") as f:
        f.write(service_content)
    print(f"  Service file created: {service_path}")
    print("  To install: sudo cp iptv-panel.service /etc/systemd/system/ && sudo systemctl enable iptv-panel")

    print("\n" + "=" * 60)
    print("  Installation Complete!")
    print("=" * 60)
    print(f"\n  Start the server:")
    print(f"    cd {base_dir}")
    print(f"    PYTHONPATH={base_dir} python -m uvicorn src.main:app --host 0.0.0.0 --port 8000")
    print(f"\n  Admin panel: http://your-server:8000/panel/")
    print(f"  Default login: admin / admin")
    print(f"\n  Player API (Xtream Codes compatible):")
    print(f"    http://your-server:8000/player_api.php?username=USER&password=PASS")
    print(f"    http://your-server:8000/get.php?username=USER&password=PASS&type=m3u_plus")


if __name__ == "__main__":
    main()
