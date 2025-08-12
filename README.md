# Echo MCP Server

A modern, scalable FastAPI backend application with real-time chat functionality, user authentication, and service management. Built with SQLModel, TiDB, Redis, and Docker for production-ready deployment.

## 🚀 Features

- **User Authentication**: JWT-based authentication with registration, login, and token refresh
- **Real-time Chat**: WebSocket-powered messaging system with unread message tracking
- **Service Management**: Admin-controlled CRUD operations for platform services
- **Admin Dashboard**: User management and oversight capabilities
- **Database**: TiDB (MySQL-compatible) with SQLModel ORM for type-safe database operations
- **Caching**: Redis for session management, caching, and real-time pub/sub messaging
- **Containerized**: Docker and Docker Compose for easy deployment
- **API Documentation**: Auto-generated OpenAPI/Swagger documentation
- **Production Ready**: Comprehensive error handling, logging, and health monitoring

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │    │   TiDB Database │    │   Redis Cache   │
│                 │    │                 │    │                 │
│ • Authentication│◄──►│ • Users         │    │ • Sessions      │
│ • Chat System   │    │ • Messages      │◄──►│ • Pub/Sub       │
│ • Service Mgmt  │    │ • Services      │    │ • Cache         │
│ • Admin Panel   │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🛠️ Tech Stack

- **Backend**: FastAPI 0.104.1
- **Database**: TiDB (MySQL-compatible) with SQLModel ORM
- **Cache**: Redis 7-alpine
- **Authentication**: JWT with bcrypt password hashing
- **WebSockets**: Real-time messaging support
- **Containerization**: Docker & Docker Compose
- **Documentation**: OpenAPI/Swagger auto-generation

## 📋 Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)
- Git

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd echo-mcp-server
```

### 2. Environment Setup

Copy the example environment file and configure as needed:

```bash
cp .env.example .env
```

### 3. Start with Docker Compose

```bash
# Start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f echo_mcp_app
```

### 4. Verify Installation

```bash
# Check application health
curl http://localhost:8000/health

# Access API documentation
open http://localhost:8000/docs
```

## 🔧 Development Setup

### Local Development

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start services (database and Redis)
docker-compose up -d tidb redis

# Run application locally
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Database Management

```bash
# Reset database (removes all data)
docker-compose down --volumes
docker-compose up -d

# View database logs
docker-compose logs tidb

# Connect to TiDB
mysql -h 127.0.0.1 -P 4000 -u root echo_mcp_tidb
```

## 📚 API Documentation

### Base URL

- **Local Development**: `http://localhost:8000`
- **API Documentation**: `http://localhost:8000/docs`

### Authentication

All protected endpoints require a Bearer token in the Authorization header:

```
Authorization: Bearer <your-jwt-token>
```

---

## 🔐 Authentication Endpoints

### Register User

**POST** `/auth/register`

Register a new user account.

**Request Body:**

```json
{
  "username": "johndoe",
  "email": "john@example.com",
  "password": "SecurePassword123!"
}
```

**Response (201):**

```json
{
  "message": "User registered successfully. Email verification disabled.",
  "user_id": "1",
  "username": "johndoe",
  "email": "john@example.com"
}
```

**Example:**

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "johndoe",
    "email": "john@example.com",
    "password": "SecurePassword123!"
  }'
```

### Login User

**POST** `/auth/login`

Authenticate user and receive JWT tokens.

**Request Body:**

```json
{
  "email": "john@example.com",
  "password": "SecurePassword123!"
}
```

**Response (200):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": 1,
    "username": "johndoe",
    "email": "john@example.com",
    "is_active": true,
    "is_verified": true,
    "is_admin": false,
    "created_at": "2025-08-12T10:30:00",
    "updated_at": "2025-08-12T10:30:00"
  }
}
```

**Example:**

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "SecurePassword123!"
  }'
```

### Refresh Token

**POST** `/auth/refresh`

Refresh access token using refresh token.

**Request Body:**

```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response (200):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### Logout User

**POST** `/auth/logout`

Logout user and invalidate tokens.

**Headers:**

```
Authorization: Bearer <access-token>
```

**Response (200):**

```json
{
  "message": "Successfully logged out"
}
```

### Create Admin User

**POST** `/auth/create-admin`

Create an admin user account with elevated privileges.

**Request Body:**

```json
{
  "username": "admin",
  "email": "admin@example.com",
  "password": "AdminSecure123!",
  "admin_secret": "your-admin-secret-key"
}
```

**Response (201):**

```json
{
  "message": "Admin user created successfully",
  "user_id": "1",
  "username": "admin",
  "email": "admin@example.com",
  "is_admin": true
}
```

**Example:**

```bash
curl -X POST http://localhost:8000/auth/create-admin \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "email": "admin@example.com",
    "password": "AdminSecure123!",
    "admin_secret": "change-this-admin-secret-in-production"
  }'
```

**Security Notes:**

- Requires a valid `admin_secret` key configured in environment variables
- Admin users are automatically verified and have `is_admin: true`
- Admin users can access all admin endpoints and manage other users
- The admin secret should be kept secure and changed in production

---

## 💬 Chat Endpoints

### Send Message

**POST** `/chat/send`

Send a message to another user.

**Headers:**

```
Authorization: Bearer <access-token>
```

**Request Body:**

```json
{
  "receiver_id": 2,
  "content": "Hello! How are you doing today?"
}
```

**Response (201):**

```json
{
  "id": 1,
  "sender_id": 1,
  "receiver_id": 2,
  "content": "Hello! How are you doing today?",
  "timestamp": "2025-08-12T10:30:00",
  "is_read": false,
  "sender_username": "johndoe",
  "receiver_username": "janedoe"
}
```

**Example:**

```bash
curl -X POST http://localhost:8000/chat/send \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-token>" \
  -d '{
    "receiver_id": 2,
    "content": "Hello! How are you doing today?"
  }'
```

### Get Chat History

**GET** `/chat/history/{user_id}`

Retrieve chat history with a specific user.

**Headers:**

```
Authorization: Bearer <access-token>
```

**Query Parameters:**

- `limit` (optional): Number of messages to retrieve (default: 50)
- `offset` (optional): Number of messages to skip (default: 0)
- `mark_as_read` (optional): Mark messages as read (default: true)

**Response (200):**

```json
{
  "messages": [
    {
      "id": 2,
      "sender_id": 2,
      "receiver_id": 1,
      "content": "I'm doing great, thanks for asking!",
      "timestamp": "2025-08-12T10:35:00",
      "is_read": true,
      "sender_username": "janedoe",
      "receiver_username": "johndoe"
    },
    {
      "id": 1,
      "sender_id": 1,
      "receiver_id": 2,
      "content": "Hello! How are you doing today?",
      "timestamp": "2025-08-12T10:30:00",
      "is_read": true,
      "sender_username": "johndoe",
      "receiver_username": "janedoe"
    }
  ],
  "total_messages": 2,
  "unread_count": 0,
  "other_user_id": 2,
  "other_username": "janedoe"
}
```

**Example:**

```bash
curl -X GET "http://localhost:8000/chat/history/2?limit=10&mark_as_read=true" \
  -H "Authorization: Bearer <your-token>"
```

### Get Unread Message Count

**GET** `/chat/unread-count`

Get the total number of unread messages for the current user.

**Headers:**

```
Authorization: Bearer <access-token>
```

**Response (200):**

```json
{
  "unread_count": 3,
  "user_id": 1
}
```

**Example:**

```bash
curl -X GET http://localhost:8000/chat/unread-count \
  -H "Authorization: Bearer <your-token>"
```

### Mark Messages as Read

**POST** `/chat/mark-read`

Mark specific messages as read.

**Headers:**

```
Authorization: Bearer <access-token>
```

**Request Body:**

```json
{
  "message_ids": [1, 2, 3]
}
```

**Response (200):**

```json
{
  "marked_count": 3,
  "message": "3 messages marked as read successfully"
}
```

**Example:**

```bash
curl -X POST http://localhost:8000/chat/mark-read \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-token>" \
  -d '{
    "message_ids": [1, 2, 3]
  }'
```

### Get Conversations

**GET** `/chat/conversations`

Get list of conversations for the current user.

**Headers:**

```
Authorization: Bearer <access-token>
```

**Query Parameters:**

- `limit` (optional): Number of conversations to retrieve (default: 20)

**Response (200):**

```json
{
  "conversations": [
    {
      "other_user_id": 2,
      "other_username": "janedoe",
      "last_message": "I'm doing great, thanks for asking!",
      "last_message_timestamp": "2025-08-12T10:35:00",
      "unread_count": 0,
      "total_messages": 5
    }
  ],
  "total_conversations": 1
}
```

---

## 🛠️ Service Management Endpoints

### List Services

**GET** `/services/list`

Get list of all active services (public endpoint).

**Query Parameters:**

- `limit` (optional): Number of services to retrieve (default: 50)
- `offset` (optional): Number of services to skip (default: 0)
- `type` (optional): Filter by service type
- `active_only` (optional): Show only active services (default: true)

**Response (200):**

```json
{
  "services": [
    {
      "id": 1,
      "name": "Weather Service",
      "type": "weather",
      "description": "Get current weather information",
      "is_active": true,
      "created_at": "2025-08-12T10:00:00",
      "updated_at": "2025-08-12T10:00:00"
    }
  ],
  "total_services": 1,
  "active_services": 1
}
```

**Example:**

```bash
curl -X GET "http://localhost:8000/services/list?limit=10&type=weather"
```

### Get Service Details

**GET** `/services/{service_id}`

Get detailed information about a specific service.

**Response (200):**

```json
{
  "id": 1,
  "name": "Weather Service",
  "type": "weather",
  "description": "Get current weather information",
  "api_base_url": "https://api.weather.com",
  "api_endpoint": "/current",
  "http_method": "GET",
  "is_active": true,
  "created_by": 1,
  "creator_username": "admin",
  "created_at": "2025-08-12T10:00:00",
  "updated_at": "2025-08-12T10:00:00"
}
```

### Create Service (Admin Only)

**POST** `/services/create`

Create a new service (requires admin privileges).

**Headers:**

```
Authorization: Bearer <admin-access-token>
```

**Request Body:**

```json
{
  "name": "Weather Service",
  "type": "weather",
  "description": "Get current weather information",
  "api_base_url": "https://api.weather.com",
  "api_endpoint": "/current",
  "http_method": "GET",
  "request_template": {
    "city": "{{city}}",
    "units": "metric"
  },
  "response_mapping": {
    "temperature": "{{response.main.temp}}",
    "description": "{{response.weather[0].description}}"
  },
  "timeout_seconds": 30,
  "retry_attempts": 3
}
```

**Response (201):**

```json
{
  "id": 1,
  "name": "Weather Service",
  "type": "weather",
  "description": "Get current weather information",
  "is_active": true,
  "created_by": 1,
  "created_at": "2025-08-12T10:00:00",
  "updated_at": "2025-08-12T10:00:00"
}
```

---

## 👑 Admin Endpoints

### Get All Users

**GET** `/admin/users`

Get list of all users (admin only).

**Headers:**

```
Authorization: Bearer <admin-access-token>
```

**Query Parameters:**

- `limit` (optional): Number of users to retrieve (default: 50)
- `offset` (optional): Number of users to skip (default: 0)
- `active_only` (optional): Show only active users (default: false)
- `search` (optional): Search by username or email

**Response (200):**

```json
{
  "users": [
    {
      "id": 1,
      "username": "johndoe",
      "email": "john@example.com",
      "is_active": true,
      "is_verified": true,
      "is_admin": false,
      "created_at": "2025-08-12T10:00:00",
      "updated_at": "2025-08-12T10:00:00"
    }
  ],
  "total_users": 1,
  "active_users": 1
}
```

**Example:**

```bash
curl -X GET "http://localhost:8000/admin/users?limit=10&search=john" \
  -H "Authorization: Bearer <admin-token>"
```

### Get User Details

**GET** `/admin/users/{user_id}`

Get detailed information about a specific user (admin only).

**Headers:**

```
Authorization: Bearer <admin-access-token>
```

**Response (200):**

```json
{
  "id": 1,
  "username": "johndoe",
  "email": "john@example.com",
  "is_active": true,
  "is_verified": true,
  "is_admin": false,
  "created_at": "2025-08-12T10:00:00",
  "updated_at": "2025-08-12T10:00:00",
  "stats": {
    "messages_sent": 15,
    "messages_received": 12,
    "last_login": "2025-08-12T10:30:00"
  }
}
```

---

## 🏥 Health & Utility Endpoints

### Health Check

**GET** `/health`

Check application and service health.

**Response (200):**

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "components": {
    "database": {
      "database": "healthy",
      "details": {
        "pool_size": 10,
        "checked_in_connections": 1,
        "checked_out_connections": 0,
        "overflow_connections": -9
      }
    },
    "redis": {
      "redis": "healthy",
      "connection_pool": "healthy",
      "details": {
        "redis_version": "7.4.5",
        "connected_clients": 1,
        "used_memory_human": "1.03M"
      }
    }
  }
}
```

### Root Endpoint

**GET** `/`

Get basic application information.

**Response (200):**

```json
{
  "name": "Echo MCP Server",
  "version": "1.0.0",
  "description": "Echo MCP Server - REST API with authentication, chat, and service management",
  "docs_url": "/docs",
  "health_url": "/health"
}
```

---

## 🔌 WebSocket Endpoints

### Chat WebSocket

**WebSocket** `/ws/chat/{user_id}`

Real-time chat connection for live messaging.

**Connection:**

```javascript
const ws = new WebSocket(
  "ws://localhost:8000/ws/chat/1?token=<your-jwt-token>"
);

ws.onmessage = function (event) {
  const message = JSON.parse(event.data);
  console.log("Received:", message);
};

// Send message
ws.send(
  JSON.stringify({
    type: "message",
    receiver_id: 2,
    content: "Hello via WebSocket!",
  })
);
```

**Message Format:**

```json
{
  "type": "message",
  "id": 1,
  "sender_id": 1,
  "receiver_id": 2,
  "content": "Hello via WebSocket!",
  "timestamp": "2025-08-12T10:30:00",
  "sender_username": "johndoe"
}
```

---

## 🚨 Error Responses

All endpoints return consistent error responses:

**Error Response Format:**

```json
{
  "error": {
    "code": "HTTP_400",
    "message": "Validation error description",
    "path": "/api/endpoint",
    "details": {
      "field": "email",
      "issue": "Email already exists"
    }
  }
}
```

**Common HTTP Status Codes:**

- `200` - Success
- `201` - Created
- `400` - Bad Request (validation errors)
- `401` - Unauthorized (authentication required)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found
- `409` - Conflict (duplicate data)
- `422` - Unprocessable Entity
- `500` - Internal Server Error

---

## 🧪 Testing

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_auth.py

# Run integration tests
pytest tests/test_integration.py
```

### Manual Testing Examples

```bash
# 1. Register two users
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "email": "alice@example.com", "password": "AlicePass123!"}'

curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "bob", "email": "bob@example.com", "password": "BobPass123!"}'

# 2. Login and get tokens
ALICE_TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@example.com", "password": "AlicePass123!"}' | \
  python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

BOB_TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "bob@example.com", "password": "BobPass123!"}' | \
  python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# 3. Send messages
curl -X POST http://localhost:8000/chat/send \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ALICE_TOKEN" \
  -d '{"receiver_id": 2, "content": "Hello Bob!"}'

curl -X POST http://localhost:8000/chat/send \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $BOB_TOKEN" \
  -d '{"receiver_id": 1, "content": "Hi Alice! How are you?"}'

# 4. Get chat history
curl -X GET "http://localhost:8000/chat/history/2" \
  -H "Authorization: Bearer $ALICE_TOKEN"
```

---

## 🔧 Configuration

### Environment Variables

Create a `.env` file based on `.env.example`:

```bash
# Application settings
APP_NAME=Echo MCP Server
APP_VERSION=1.0.0
DEBUG=false
PORT=8000

# Database settings (TiDB)
TIDB_HOST=localhost
TIDB_PORT=4000
TIDB_USER=root
TIDB_PASSWORD=
TIDB_DATABASE=echo_mcp_tidb

# Redis settings
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# JWT settings
JWT_SECRET_KEY=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Email settings (optional)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=your-email@gmail.com

# CORS settings
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8080"]
CORS_ALLOW_CREDENTIALS=true
```

### Docker Compose Services

The application consists of three main services:

1. **echo_mcp_app**: FastAPI application
2. **tidb**: TiDB database server
3. **redis**: Redis cache and pub/sub server

---

## 📊 Monitoring

### Health Monitoring

```bash
# Check overall health
curl http://localhost:8000/health

# Check individual service logs
docker-compose logs echo_mcp_app
docker-compose logs tidb
docker-compose logs redis
```

### Database Monitoring

```bash
# Connect to TiDB
mysql -h 127.0.0.1 -P 4000 -u root echo_mcp_tidb

# Check tables
SHOW TABLES;

# Check user count
SELECT COUNT(*) FROM users;

# Check message count
SELECT COUNT(*) FROM chat_messages;
```

### Redis Monitoring

```bash
# Connect to Redis
redis-cli -h localhost -p 6379

# Check Redis info
INFO

# Monitor commands
MONITOR
```

---

## 🚀 Deployment

### Production Deployment

1. **Update Environment Variables**:

   ```bash
   # Set production values
   DEBUG=false
   JWT_SECRET_KEY=<secure-random-key>
   TIDB_PASSWORD=<secure-password>
   REDIS_PASSWORD=<secure-password>
   ```

2. **Use Production Docker Compose**:

   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

3. **Set up Reverse Proxy** (nginx example):

   ```nginx
   server {
       listen 80;
       server_name your-domain.com;

       location / {
           proxy_pass http://localhost:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }

       location /ws/ {
           proxy_pass http://localhost:8000;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection "upgrade";
       }
   }
   ```

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🆘 Support

- **Documentation**: [API Docs](http://localhost:8000/docs)
- **Issues**: [GitHub Issues](https://github.com/your-org/echo-mcp-server/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/echo-mcp-server/discussions)

---

## 📝 Changelog

### v1.0.0 (2025-08-12)

- Initial release
- User authentication system
- Real-time chat functionality
- Service management
- Admin dashboard
- Docker containerization
- Comprehensive API documentation
