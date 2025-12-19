# StreamRev Installation Guide

This guide provides detailed instructions for installing StreamRev on Ubuntu 22.04 LTS or 24.04 LTS.

## Prerequisites

### System Requirements
- Ubuntu 22.04 LTS or 24.04 LTS (recommended)
- Minimum 2GB RAM (4GB+ recommended for production)
- 20GB+ free disk space
- Root or sudo access

### Software Requirements
The installation script will install all required dependencies:
- Python 3.10+
- MariaDB 10.6+
- Nginx
- Redis or KeyDB
- FFmpeg 5.0+

## Quick Installation

The easiest way to install StreamRev is using the automated installation script:

```bash
# Download the installation script
curl -O https://raw.githubusercontent.com/obscuremind/StreamRev/main/install

# Make it executable
chmod +x install

# Run the installer as root
sudo ./install
```

The installation script will:
1. Update system packages
2. Install all dependencies
3. Set up MariaDB database
4. Configure Redis cache
5. Install StreamRev application
6. Configure Nginx web server
7. Create systemd service
8. Start all services

## Manual Installation

If you prefer manual installation or need to customize the setup:

### 1. Update System

```bash
sudo apt update
sudo apt upgrade -y
```

### 2. Install Dependencies

```bash
sudo apt install -y python3 python3-pip python3-venv nginx \
    mariadb-server redis-server ffmpeg git curl wget unzip
```

### 3. Set Up Database

```bash
# Start MariaDB
sudo systemctl start mariadb
sudo systemctl enable mariadb

# Secure MariaDB installation
sudo mysql_secure_installation

# Create database and user
sudo mysql <<EOF
CREATE DATABASE streamrev;
CREATE USER 'streamrev'@'localhost' IDENTIFIED BY 'your_secure_password';
GRANT ALL PRIVILEGES ON streamrev.* TO 'streamrev'@'localhost';
FLUSH PRIVILEGES;
EOF
```

### 4. Install StreamRev

```bash
# Create installation directory
sudo mkdir -p /opt/streamrev

# Clone repository
cd /opt/streamrev
sudo git clone https://github.com/obscuremind/StreamRev.git .

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Set Up Database Schema

```bash
mysql -u streamrev -p streamrev < src/database/schema.sql
```

### 6. Configure StreamRev

```bash
# Copy configuration template
cp configs/config.json.example config.json

# Edit configuration
nano config.json
```

Update the following fields:
- Database credentials
- Redis connection
- API secret key
- Streaming URLs

### 7. Create Required Directories

```bash
sudo mkdir -p /var/streams/live
sudo mkdir -p /var/streams/vod
sudo mkdir -p /var/log/streamrev
sudo chown -R www-data:www-data /var/streams
sudo chown -R www-data:www-data /var/log/streamrev
```

### 8. Configure Nginx

```bash
# Copy Nginx configuration
sudo cp configs/nginx.conf.example /etc/nginx/sites-available/streamrev

# Enable site
sudo ln -s /etc/nginx/sites-available/streamrev /etc/nginx/sites-enabled/

# Remove default site
sudo rm /etc/nginx/sites-enabled/default

# Test configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
```

### 9. Set Up Systemd Service

```bash
# Create service file
sudo nano /etc/systemd/system/streamrev.service
```

Add the following content:

```ini
[Unit]
Description=StreamRev IPTV Backend
After=network.target mariadb.service redis-server.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/streamrev
Environment="PATH=/opt/streamrev/venv/bin"
ExecStart=/opt/streamrev/venv/bin/python -m src.api.server
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable streamrev
sudo systemctl start streamrev
```

## Verify Installation

Check that all services are running:

```bash
sudo systemctl status mariadb
sudo systemctl status redis-server
sudo systemctl status nginx
sudo systemctl status streamrev
```

Test the API:

```bash
curl http://localhost:5000/health
```

You should receive a response like:
```json
{"status": "ok", "version": "1.0.0"}
```

## Post-Installation

### 1. Change Default Password

The default admin credentials are:
- Username: `admin`
- Password: `admin123`

**⚠️ CHANGE THIS IMMEDIATELY!**

### 2. Configure Domain

Edit `/etc/nginx/sites-available/streamrev` and update `server_name` with your domain.

### 3. Set Up SSL (Recommended)

For production environments, set up SSL using Let's Encrypt:

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### 4. Configure Firewall

```bash
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

## Troubleshooting

### Service Not Starting

Check logs:
```bash
sudo journalctl -u streamrev -f
```

### Database Connection Issues

Verify database credentials in `config.json` and test connection:
```bash
mysql -u streamrev -p streamrev
```

### Nginx Errors

Check Nginx logs:
```bash
sudo tail -f /var/log/nginx/streamrev-error.log
```

### FFmpeg Issues

Verify FFmpeg installation:
```bash
ffmpeg -version
```

## Updating StreamRev

To update to the latest version:

```bash
cd /opt/streamrev
sudo -u www-data git pull
source venv/bin/activate
pip install -r requirements.txt --upgrade
sudo systemctl restart streamrev
```

## Uninstallation

To completely remove StreamRev:

```bash
sudo systemctl stop streamrev
sudo systemctl disable streamrev
sudo rm /etc/systemd/system/streamrev.service
sudo systemctl daemon-reload

# Remove installation directory
sudo rm -rf /opt/streamrev

# Remove database (optional)
sudo mysql -e "DROP DATABASE streamrev;"
sudo mysql -e "DROP USER 'streamrev'@'localhost';"

# Remove Nginx configuration
sudo rm /etc/nginx/sites-enabled/streamrev
sudo rm /etc/nginx/sites-available/streamrev
sudo systemctl restart nginx
```

## Next Steps

- [API Documentation](API.md)
- [User Guide](USER_GUIDE.md)
- [Configuration Guide](CONFIGURATION.md)

## Support

- GitHub Issues: https://github.com/obscuremind/StreamRev/issues
- Documentation: https://github.com/obscuremind/StreamRev/docs
