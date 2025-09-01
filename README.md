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

## 🔗 Bolt API Integration

The Echo MCP Server now includes comprehensive integration with Bolt Food and Bolt Stores APIs, enabling restaurant ordering and retail purchasing capabilities.

### Features

- **Bolt Food Integration**: Restaurant menu browsing, order placement, and status tracking
- **Bolt Stores Integration**: Retail product catalog, shopping cart, and order management
- **HMAC Authentication**: Secure API communication with Bolt services
- **Webhook Support**: Real-time order status updates
- **Demo Endpoints**: Test Bolt integrations without affecting production

### API Endpoints

#### Bolt Food
- `GET /bolt/food/menu/{provider_id}` - Get restaurant menu
- `POST /bolt/food/order` - Create food order
- `GET /bolt/food/order/{order_id}` - Get order status
- `POST /bolt/food/webhook` - Handle Bolt webhooks

#### Bolt Stores
- `GET /bolt/stores/menu/{provider_id}` - Get store products
- `POST /bolt/stores/order` - Create store order
- `GET /bolt/stores/order/{order_id}` - Get order status
- `POST /bolt/stores/webhook` - Handle Bolt webhooks

### Configuration

Add the following environment variables for Bolt API integration:

```bash
# Bolt Food API
BOLT_FOOD_API_KEY=your_bolt_food_api_key
BOLT_FOOD_API_SECRET=your_bolt_food_api_secret
BOLT_FOOD_WEBHOOK_SECRET=your_webhook_secret

# Bolt Stores API
BOLT_STORES_API_KEY=your_bolt_stores_api_key
BOLT_STORES_API_SECRET=your_bolt_stores_api_secret
BOLT_STORES_WEBHOOK_SECRET=your_webhook_secret
```

## ☁️ AWS Production Deployment

The Echo MCP Server includes automated CI/CD deployment to AWS using CloudFormation, CodePipeline, and ECS Fargate.

### Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   GitHub    │───►│ CodePipeline│───►│ CodeBuild   │
│  (Source)   │    │             │    │             │
└─────────────┘    └─────────────┘    └─────────────┘
                                                        │
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    │
│   ECR       │◄───┤  Docker     │◄───┤  Build &    │◄───┘
│ Repository  │    │  Image      │    │  Test       │
└─────────────┘    └─────────────┘    └─────────────┘
                                                        │
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    │
│   ALB       │───►│   ECS       │───►│   Fargate   │◄───┘
│ Load Balancer│    │  Service   │    │  Tasks      │
└─────────────┘    └─────────────┘    └─────────────┘
```

### Prerequisites

1. **AWS Account** with appropriate permissions
2. **GitHub Repository** with your code
3. **GitHub Personal Access Token** with `repo` permissions
4. **AWS CLI** configured with your credentials

### Automated Deployment

1. **Configure AWS CLI:**
   ```bash
   aws configure
   ```

2. **Set environment variables:**
   ```bash
   export GITHUB_TOKEN=your_github_token_here
   ```

3. **Run deployment script:**
   ```bash
   ./deploy.sh
   ```

   The script will automatically:
   - Validate CloudFormation template
   - Create ECR repository for Docker images
   - Set up CodeBuild project for building and testing
   - Create ECS cluster and Fargate services
   - Configure Application Load Balancer
   - Set up CodePipeline with GitHub integration

### Manual Deployment

If you prefer manual deployment:

1. **Create CloudFormation stack:**
   ```bash
   aws cloudformation create-stack \
     --stack-name echo-mcp-server \
     --template-body file://pipeline.yml \
     --parameters ParameterKey=GitHubOwner,ParameterValue=your-github-username \
                 ParameterKey=GitHubRepo,ParameterValue=echo-mcp-server \
                 ParameterKey=GitHubBranch,ParameterValue=main \
                 ParameterKey=GitHubToken,ParameterValue=your-github-token \
                 ParameterKey=EnvironmentName,ParameterValue=dev \
     --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM
   ```

2. **Monitor stack creation:**
   ```bash
   aws cloudformation describe-stack-events --stack-name echo-mcp-server
   ```

3. **Get stack outputs:**
   ```bash
   aws cloudformation describe-stacks --stack-name echo-mcp-server --query 'Stacks[0].Outputs'
   ```

### Post-Deployment Configuration

1. **Set up GitHub webhook** (optional for automatic builds):
   - Go to your GitHub repository settings
   - Add webhook pointing to the CodePipeline webhook URL
   - Configure webhook to trigger on push events

2. **Update DNS** (optional):
   - Point your domain to the ALB DNS name
   - Configure SSL certificate if needed

3. **Configure Bolt API credentials** in AWS Systems Manager Parameter Store or environment variables

### Monitoring and Logs

#### CloudWatch Logs
- **Application Logs**: `/ecs/echo-mcp-server`
- **CodeBuild Logs**: `/aws/codebuild/echo-mcp-server-build`
- **ECS Events**: Available in ECS cluster events

#### Health Checks
- **Application Health**: `GET /health`
- **Database Health**: Included in health check
- **Redis Health**: Included in health check

### Troubleshooting

#### Common Issues

1. **Build Failures:**
   - Check CodeBuild logs
   - Verify environment variables
   - Ensure all dependencies are in requirements.txt

2. **Deployment Failures:**
   - Check CloudFormation events
   - Verify IAM permissions
   - Ensure VPC and subnet configuration

3. **API Issues:**
   - Check application logs
   - Verify database connectivity
   - Check Bolt API credentials

#### Useful Commands

```bash
# View application logs
aws logs tail /ecs/echo-mcp-server --follow

# View CodeBuild logs
aws logs tail /aws/codebuild/echo-mcp-server-build --follow

# Check ECS service status
aws ecs describe-services --cluster echo-mcp-server-cluster --services echo-mcp-server-service

# Update service with new task definition
aws ecs update-service --cluster echo-mcp-server-cluster --service echo-mcp-server-service --force-new-deployment
```

## 🧪 Testing

### Unit Tests
```bash
python -m pytest tests/ -v
```

### Integration Tests
```bash
python -m pytest tests/test_final_integration.py -v
```

### E2E Tests
```bash
python comprehensive_e2e_test.py
```

### Bolt API Tests
```bash
python test_bolt_integration.py
```

## 📊 API Documentation

Once the application is running, you can access:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For support and questions:
- Create an issue in the GitHub repository
- Check the documentation in the `docs/` directory
- Review the API documentation at `/docs` endpoint

## 🔄 Recent Updates

- ✅ **Bolt API Integration**: Full integration with Bolt Food and Stores APIs
- ✅ **AWS Deployment**: Automated CI/CD with CloudFormation and CodePipeline
- ✅ **Enhanced Testing**: Comprehensive test suite with 90%+ coverage
- ✅ **Production Ready**: Health checks, monitoring, and error handling
- ✅ **MCP Support**: Model Context Protocol integration for AI assistants
