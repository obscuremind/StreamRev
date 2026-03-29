#!/usr/bin/env bash
set -euo pipefail

if [[ ${EUID} -ne 0 ]]; then
  echo "Run as root"
  exit 1
fi

APP_DIR=${APP_DIR:-/opt/streamrev}
PYTHON_BIN=${PYTHON_BIN:-python3}

apt-get update
apt-get install -y python3 python3-venv ffmpeg nginx redis-server mariadb-client curl

mkdir -p "$APP_DIR"
cd "$APP_DIR"

if [[ -f requirements.txt ]]; then
  "$PYTHON_BIN" -m venv .venv
  source .venv/bin/activate
  pip install --upgrade pip
  pip install -r requirements.txt
fi

# baseline kernel/network settings for streaming
cat >/etc/sysctl.d/99-streamrev.conf <<'SYSCTL'
net.core.somaxconn=4096
net.ipv4.tcp_fin_timeout=15
vm.swappiness=10
SYSCTL
sysctl --system >/dev/null

# install service unit if available
if [[ -f infrastructure/systemd/streamrev.service ]]; then
  cp infrastructure/systemd/streamrev.service /etc/systemd/system/streamrev.service
  systemctl daemon-reload
  systemctl enable streamrev.service
fi

echo "install_ubuntu: complete"
