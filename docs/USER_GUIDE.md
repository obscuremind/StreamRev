# StreamRev User Guide

This guide provides instructions for using StreamRev IPTV backend platform.

## Table of Contents

- [Getting Started](#getting-started)
- [User Management](#user-management)
- [Stream Management](#stream-management)
- [VOD Management](#vod-management)
- [Series Management](#series-management)
- [Categories](#categories)
- [EPG Configuration](#epg-configuration)

## Getting Started

### Accessing StreamRev

After installation, access StreamRev through:
- Web Interface: `http://your-server-ip/`
- API: `http://your-server-ip/api/v1/`
- Xtream Codes API: `http://your-server-ip/player_api.php`

### Default Credentials

**⚠️ Security Warning**: Change these immediately after first login!

- Username: `admin`
- Password: `admin123`

### First Login

1. Navigate to the login page
2. Enter your credentials
3. You'll receive a JWT token for API access
4. Change your password immediately

## User Management

### Creating Users

Users are the end-customers who will consume your IPTV content.

#### Via API

```bash
curl -X POST http://your-server/api/v1/admin/users \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "customer1",
    "password": "secure_password",
    "email": "customer@example.com",
    "exp_date": "2025-12-31",
    "max_connections": 1,
    "is_trial": false
  }'
```

### User Properties

- **Username**: Unique identifier for the user
- **Password**: User's password
- **Expiration Date**: When the subscription expires
- **Max Connections**: Number of simultaneous connections allowed
- **Status**: Active (1) or Inactive (0)
- **Is Trial**: Whether this is a trial account

### Managing User Connections

Monitor active user connections:
- Check current active connections
- Enforce maximum connection limits
- Disconnect users if needed

## Stream Management

### Adding Live TV Channels

Live streams are continuous broadcasts (TV channels).

#### Required Information

- Stream Name
- Stream Source URL (m3u8, rtmp, rtsp, etc.)
- Stream Icon (optional)
- Category
- Transcode Profile (optional)

#### Via API

```bash
curl -X POST http://your-server/api/v1/admin/streams \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "News Channel",
    "stream_source": "http://source.com/stream.m3u8",
    "stream_icon": "http://example.com/icon.png",
    "category_id": 1,
    "transcode_profile": "medium"
  }'
```

### Transcoding Profiles

StreamRev supports multiple transcoding profiles:

- **Low**: 800kbps video, 64kbps audio (mobile)
- **Medium**: 2000kbps video, 128kbps audio (default)
- **High**: 4000kbps video, 192kbps audio (HD)

### Stream Sources

Supported input formats:
- HLS (m3u8)
- RTMP
- RTSP
- HTTP/HTTPS
- Local files

## VOD Management

### Adding Movies

VOD (Video on Demand) content includes movies and standalone videos.

#### Required Information

- Title
- Video Source URL
- Year (optional)
- Rating (optional)
- Cover Image (optional)
- Description (optional)
- Category

#### Via API

```bash
curl -X POST http://your-server/api/v1/admin/vod \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Action Movie",
    "title": "Action Movie 2024",
    "year": "2024",
    "stream_source": "http://source.com/movie.mp4",
    "cover": "http://example.com/cover.jpg",
    "rating": "8.5",
    "category_id": 2
  }'
```

### VOD Categories

Organize movies by genre:
- Action
- Comedy
- Drama
- Horror
- Sci-Fi
- etc.

## Series Management

### Adding TV Series

Series contain multiple seasons and episodes.

#### Steps

1. Create the series
2. Add seasons
3. Add episodes to each season

#### Creating a Series

```bash
curl -X POST http://your-server/api/v1/admin/series \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Popular Series",
    "title": "Popular Series",
    "year": "2024",
    "cover": "http://example.com/series.jpg",
    "rating": "9.0",
    "category_id": 3
  }'
```

#### Adding Episodes

```bash
curl -X POST http://your-server/api/v1/admin/series/1/episodes \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "season": 1,
    "episode_num": 1,
    "title": "Pilot",
    "stream_source": "http://source.com/s01e01.mp4"
  }'
```

## Categories

### Category Types

- **live**: For live TV channels
- **vod**: For movies
- **series**: For TV series

### Creating Categories

```bash
curl -X POST http://your-server/api/v1/admin/categories \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "News",
    "type": "live",
    "order": 1
  }'
```

### Organizing Content

Use categories to:
- Group similar content
- Create hierarchies (parent/child categories)
- Control display order
- Improve navigation

## EPG Configuration

### Electronic Program Guide

EPG provides TV schedule information for live channels.

#### EPG Sources

StreamRev supports:
- XMLTV format
- JSON EPG
- Custom EPG sources

#### Configuring EPG

1. Upload EPG file or configure EPG URL
2. Map EPG channels to your streams
3. Set update interval

#### EPG API

View EPG data:
```bash
curl http://your-server/api/v1/epg/stream/1 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Load Balancing

### Server Nodes

Add multiple server nodes for load balancing:

```bash
curl -X POST http://your-server/api/v1/admin/servers \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Server 2",
    "hostname": "server2.example.com",
    "port": 80,
    "max_clients": 1000
  }'
```

### Load Distribution

StreamRev automatically:
- Distributes new connections across servers
- Monitors server load
- Routes users to least loaded server

## Reseller Management

### Creating Resellers

Resellers can create and manage their own users:

```bash
curl -X POST http://your-server/api/v1/admin/resellers \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "reseller1",
    "password": "secure_password",
    "email": "reseller@example.com",
    "credits": 100.00
  }'
```

### Reseller Permissions

Configure what resellers can do:
- Create users
- View statistics
- Manage own users only
- Access specific content

## Monitoring and Statistics

### View Statistics

```bash
# User activity
curl http://your-server/api/v1/admin/stats/users \
  -H "Authorization: Bearer YOUR_TOKEN"

# Stream statistics
curl http://your-server/api/v1/admin/stats/streams \
  -H "Authorization: Bearer YOUR_TOKEN"

# Server load
curl http://your-server/api/v1/admin/stats/servers \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Best Practices

### Security

1. Change default passwords immediately
2. Use strong passwords
3. Enable HTTPS
4. Restrict admin access
5. Regular backups

### Performance

1. Use transcoding profiles appropriately
2. Enable Redis caching
3. Configure load balancing
4. Monitor server resources
5. Regular maintenance

### Content Organization

1. Use meaningful category names
2. Maintain consistent naming
3. Add metadata (covers, descriptions)
4. Regular content updates
5. Remove expired content

## Troubleshooting

### Common Issues

#### User Can't Connect
- Check expiration date
- Verify max connections
- Check user status

#### Stream Not Playing
- Verify stream source is valid
- Check transcoding settings
- Review server logs

#### Slow Performance
- Check server load
- Review database performance
- Monitor network bandwidth

## Support

For support:
- Documentation: [GitHub Docs](https://github.com/obscuremind/StreamRev/docs)
- Issues: [GitHub Issues](https://github.com/obscuremind/StreamRev/issues)
- Community: [GitHub Discussions](https://github.com/obscuremind/StreamRev/discussions)
