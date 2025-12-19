# StreamRev API Documentation

StreamRev provides a comprehensive REST API and Xtream Codes compatible API for managing IPTV services.

## Table of Contents

- [Authentication](#authentication)
- [Xtream Codes API](#xtream-codes-api)
- [REST API v1](#rest-api-v1)
- [Error Handling](#error-handling)

## Authentication

### JWT Token Authentication

Most endpoints require authentication using JWT tokens.

#### Login

**Endpoint:** `POST /api/v1/auth/login`

**Request:**
```json
{
  "username": "your_username",
  "password": "your_password"
}
```

**Response:**
```json
{
  "user_id": 1,
  "username": "your_username",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "exp_date": "2025-12-31 23:59:59",
  "status": 1
}
```

#### Using the Token

Include the token in the Authorization header:
```
Authorization: Bearer YOUR_TOKEN_HERE
```

Or as a query parameter:
```
?token=YOUR_TOKEN_HERE
```

## Xtream Codes API

StreamRev is compatible with the Xtream Codes API format for easy migration.

### Base Endpoint

```
http://your-server.com/player_api.php
```

### Get User Info

**Endpoint:** `/player_api.php?action=get_user_info&username=USER&password=PASS`

**Response:**
```json
{
  "user_info": {
    "username": "user1",
    "password": "pass1",
    "message": "",
    "auth": 1,
    "status": "Active",
    "exp_date": "1735689599",
    "is_trial": "0",
    "active_cons": "0",
    "created_at": "1640995200",
    "max_connections": "1",
    "allowed_output_formats": ["m3u8", "ts"]
  },
  "server_info": {
    "url": "http://your-server.com",
    "port": "80",
    "https_port": "443",
    "server_protocol": "http",
    "rtmp_port": "1935",
    "timezone": "UTC",
    "timestamp_now": 1640995200
  }
}
```

### Get Live Streams

**Endpoint:** `/player_api.php?action=get_live_streams&username=USER&password=PASS`

**Response:**
```json
[
  {
    "num": 1,
    "name": "Channel Name",
    "stream_type": "live",
    "stream_id": 1,
    "stream_icon": "http://example.com/icon.png",
    "epg_channel_id": "channel1",
    "added": "1640995200",
    "category_id": "1",
    "custom_sid": "",
    "tv_archive": 0,
    "direct_source": "",
    "tv_archive_duration": 0
  }
]
```

### Get VOD Streams

**Endpoint:** `/player_api.php?action=get_vod_streams&username=USER&password=PASS`

**Response:**
```json
[
  {
    "num": 1,
    "name": "Movie Name",
    "stream_type": "movie",
    "stream_id": 1,
    "stream_icon": "http://example.com/cover.jpg",
    "rating": "8.5",
    "rating_5based": 4.25,
    "added": "1640995200",
    "category_id": "1",
    "container_extension": "mp4",
    "custom_sid": "",
    "direct_source": ""
  }
]
```

### Get Series

**Endpoint:** `/player_api.php?action=get_series&username=USER&password=PASS`

**Response:**
```json
[
  {
    "num": 1,
    "name": "Series Name",
    "series_id": 1,
    "cover": "http://example.com/series.jpg",
    "plot": "Series description",
    "cast": "Actor1, Actor2",
    "director": "Director Name",
    "genre": "Action",
    "releaseDate": "2024",
    "last_modified": "1640995200",
    "rating": "9.0",
    "rating_5based": 4.5,
    "backdrop_path": ["http://example.com/backdrop.jpg"],
    "youtube_trailer": "",
    "episode_run_time": "45",
    "category_id": "1"
  }
]
```

### Get Categories

**Endpoints:**
- Live: `/player_api.php?action=get_live_categories`
- VOD: `/player_api.php?action=get_vod_categories`
- Series: `/player_api.php?action=get_series_categories`

**Response:**
```json
[
  {
    "category_id": "1",
    "category_name": "Movies",
    "parent_id": 0
  }
]
```

## REST API v1

### Streams

#### List Streams

**Endpoint:** `GET /api/v1/streams`

**Headers:** `Authorization: Bearer TOKEN`

**Query Parameters:**
- `category_id` (optional): Filter by category

**Response:**
```json
[
  {
    "id": 1,
    "name": "Channel Name",
    "stream_icon": "http://example.com/icon.png",
    "category_id": 1
  }
]
```

#### Get Stream

**Endpoint:** `GET /api/v1/streams/:id`

**Headers:** `Authorization: Bearer TOKEN`

**Response:**
```json
{
  "id": 1,
  "name": "Channel Name",
  "stream_icon": "http://example.com/icon.png",
  "stream_source": "http://example.com/stream.m3u8",
  "category_id": 1
}
```

### VOD

#### List VOD

**Endpoint:** `GET /api/v1/vod`

**Headers:** `Authorization: Bearer TOKEN`

**Query Parameters:**
- `category_id` (optional): Filter by category

**Response:**
```json
[
  {
    "id": 1,
    "name": "Movie Name",
    "year": "2024",
    "rating": "8.5",
    "cover": "http://example.com/cover.jpg"
  }
]
```

### Series

#### List Series

**Endpoint:** `GET /api/v1/series`

**Headers:** `Authorization: Bearer TOKEN`

**Response:**
```json
[
  {
    "id": 1,
    "name": "Series Name",
    "year": "2024",
    "rating": "9.0",
    "cover": "http://example.com/series.jpg"
  }
]
```

## Admin API

Admin endpoints require admin privileges.

### User Management

#### List Users

**Endpoint:** `GET /api/v1/admin/users`

**Headers:** `Authorization: Bearer ADMIN_TOKEN`

**Response:**
```json
[
  {
    "id": 1,
    "username": "user1",
    "status": 1,
    "exp_date": "2025-12-31"
  }
]
```

#### Create User

**Endpoint:** `POST /api/v1/admin/users`

**Headers:** `Authorization: Bearer ADMIN_TOKEN`

**Request:**
```json
{
  "username": "newuser",
  "password": "secure_password",
  "email": "user@example.com",
  "exp_date": "2025-12-31",
  "max_connections": 1
}
```

**Response:**
```json
{
  "id": 2,
  "username": "newuser"
}
```

### Stream Management

#### Create Stream

**Endpoint:** `POST /api/v1/admin/streams`

**Headers:** `Authorization: Bearer ADMIN_TOKEN`

**Request:**
```json
{
  "name": "New Channel",
  "stream_source": "http://example.com/stream.m3u8",
  "stream_icon": "http://example.com/icon.png",
  "category_id": 1
}
```

**Response:**
```json
{
  "id": 2,
  "name": "New Channel"
}
```

#### Create VOD

**Endpoint:** `POST /api/v1/admin/vod`

**Headers:** `Authorization: Bearer ADMIN_TOKEN`

**Request:**
```json
{
  "name": "New Movie",
  "title": "New Movie Title",
  "year": "2024",
  "stream_source": "http://example.com/movie.mp4",
  "category_id": 1
}
```

**Response:**
```json
{
  "id": 2,
  "name": "New Movie"
}
```

## Error Handling

### Error Response Format

```json
{
  "error": "Error message description"
}
```

### HTTP Status Codes

- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `500` - Internal Server Error

### Common Errors

#### Invalid Credentials
```json
{
  "error": "Invalid credentials"
}
```

#### Token Expired
```json
{
  "error": "Invalid or expired token"
}
```

#### Missing Token
```json
{
  "error": "Token is missing"
}
```

#### Admin Required
```json
{
  "error": "Admin privileges required"
}
```

## Rate Limiting

API requests are rate-limited to prevent abuse:
- Default: 60 requests per minute per IP
- Admin endpoints: 120 requests per minute

Rate limit headers are included in responses:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 59
X-RateLimit-Reset: 1640995200
```

## Examples

### Python Example

```python
import requests

# Login
response = requests.post('http://your-server.com/api/v1/auth/login', json={
    'username': 'admin',
    'password': 'admin123'
})
token = response.json()['token']

# Get streams
headers = {'Authorization': f'Bearer {token}'}
streams = requests.get('http://your-server.com/api/v1/streams', headers=headers)
print(streams.json())
```

### cURL Example

```bash
# Login
TOKEN=$(curl -s -X POST http://your-server.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' \
  | jq -r '.token')

# Get streams
curl -H "Authorization: Bearer $TOKEN" \
  http://your-server.com/api/v1/streams
```

## Support

For API support and questions:
- GitHub Issues: https://github.com/obscuremind/StreamRev/issues
- Documentation: https://github.com/obscuremind/StreamRev/docs
