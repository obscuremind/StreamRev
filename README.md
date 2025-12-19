# StreamRev

**StreamRev** is an open-source, transparent, and community-driven IPTV backend platform. Inspired by modern IPTV management systems, StreamRev provides a complete solution for managing live TV, movies, series, and VOD content with a focus on openness, security, and performance.

## 🚀 Features

### Core Functionality
- **IPTV Panel Infrastructure**: Complete management of live TV, movies, and series
- **User & Reseller Management**: Full control over users, subscriptions, and reseller hierarchy
- **Streaming Capabilities**: Support for live streaming and Video on Demand (VOD)
- **EPG Support**: Electronic Program Guide integration
- **Load Balancing**: Built-in load balancer for distributed streaming

### Technical Features
- **FFmpeg Transcoding**: Fast, efficient media processing and transcoding
- **Xtream Codes API Compatible**: Easy migration and integration
- **Caching Layer**: High-performance caching with Redis/KeyDB support
- **Security**: Enhanced security features and regular updates
- **Scalability**: Designed for scalability from small to large deployments

### 100% Free & Open Source
- No license checks or server locks
- Community-driven development
- Full source code access
- Free to use, modify, and distribute

## 📋 Requirements

### System Requirements
- Ubuntu 22.04 LTS or 24.04 LTS (officially supported)
- Minimum 2GB RAM (4GB+ recommended)
- 20GB+ disk space

### Software Dependencies
- Python 3.10+
- MariaDB/MySQL 10.6+
- Nginx
- Redis or KeyDB
- FFmpeg 5.0+
- PHP 8.2+

## 🔧 Installation

### Quick Install

```bash
# Download and run the installer
curl -O https://raw.githubusercontent.com/obscuremind/StreamRev/main/install
chmod +x install
sudo ./install
```

### Docker Installation

```bash
# Clone repository
git clone https://github.com/obscuremind/StreamRev.git
cd StreamRev

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Start with Docker Compose
docker-compose up -d
```

### Manual Installation

See [docs/INSTALLATION.md](docs/INSTALLATION.md) for detailed installation instructions.

## 📚 Documentation

- [Installation Guide](docs/INSTALLATION.md)
- [Docker Deployment](docs/DOCKER.md)
- [API Documentation](docs/API.md)
- [User Guide](docs/USER_GUIDE.md)
- [Configuration Guide](docs/CONFIGURATION.md)
- [Scripts Documentation](scripts/README.md)

## 🏗️ Architecture

StreamRev is built with a modular architecture:

```
├── src/
│   ├── api/          # API endpoints and handlers
│   ├── core/         # Core business logic
│   ├── database/     # Database models and migrations
│   ├── streaming/    # Streaming and transcoding
│   ├── web/          # Web admin interface
│   └── utils/        # Utility functions
├── configs/          # Configuration templates
├── docs/             # Documentation
├── scripts/          # Maintenance scripts (backup, restore, monitor, update)
└── tests/            # Unit and integration tests
```

## 🎨 Web Interface

StreamRev includes a basic web admin interface accessible at `http://your-server/`:

- Dashboard with system overview
- User management
- Stream management
- VOD and series management
- Settings configuration

For full functionality, use the REST API endpoints.

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Ways to Contribute
- Report bugs and issues
- Suggest new features
- Submit pull requests
- Improve documentation
- Help other users

## 📝 License

StreamRev is released under the MIT License. See [LICENSE](LICENSE) for details.

## ⚠️ Development Status

StreamRev is currently in **active development**. While functional, you may encounter bugs or incomplete features. We appreciate your feedback and contributions!

## 🔒 Security

Security is a priority. If you discover a security vulnerability, please email security@streamrev.io (or open a private security advisory on GitHub).

## 🌟 Community

- GitHub Issues: Bug reports and feature requests
- Discussions: Community support and questions
- Contributing: See CONTRIBUTING.md

## 🙏 Acknowledgments

Inspired by the open-source IPTV community and projects like XC_VM.

## 📞 Support

- Documentation: [docs/](docs/)
- Issues: [GitHub Issues](https://github.com/obscuremind/StreamRev/issues)
- Community: [GitHub Discussions](https://github.com/obscuremind/StreamRev/discussions)

---

**Note**: This software is for legal use only. Users are responsible for ensuring compliance with all applicable laws and regulations regarding content streaming and distribution.