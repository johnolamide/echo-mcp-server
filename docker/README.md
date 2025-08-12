# Docker Setup for FastAPI MCP Backend

This directory contains Docker configuration files for running the FastAPI MCP Backend application with TiDB and Redis.

## Quick Start

### Development Environment

```bash
# Start development environment with hot reload
make dev

# Or manually:
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

### Production Environment

```bash
# Start production environment
make prod

# Or manually:
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Services

### FastAPI Application
- **Port**: 8000
- **Health Check**: http://localhost:8000/health
- **API Docs**: http://localhost:8000/docs (development only)

### TiDB Database
- **Port**: 4000 (MySQL protocol)
- **Admin Port**: 10080
- **User**: root
- **Password**: (empty)
- **Database**: fastapi_mcp

### Redis
- **Port**: 6379
- **Persistence**: Enabled with AOF

### Optional Services (Development)
- **Adminer**: http://localhost:8080 (Database admin interface)
- **Redis Commander**: http://localhost:8081 (Redis admin interface)

## Docker Commands

### Using Makefile (Recommended)

```bash
make help          # Show all available commands
make build         # Build all images
make up            # Start all services
make down          # Stop all services
make logs          # Show logs
make clean         # Clean up everything
make dev           # Start development environment
make prod          # Start production environment
make health        # Check service health
make shell         # Open shell in FastAPI container
make db-shell      # Open TiDB shell
make redis-cli     # Open Redis CLI
```

### Manual Docker Compose Commands

```bash
# Development
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Production
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# With admin tools
docker-compose -f docker-compose.yml -f docker-compose.dev.yml --profile admin up -d

# View logs
docker-compose logs -f fastapi_app

# Stop services
docker-compose down
```

## Environment Configuration

### Development
Copy `.env.docker` to `.env` and modify as needed:

```bash
cp .env.docker .env
```

### Production
Set the following environment variables:

```bash
export JWT_SECRET_KEY="your-secure-secret-key"
export TIDB_PASSWORD="secure-database-password"
export REDIS_PASSWORD="secure-redis-password"
```

## File Structure

```
docker/
├── README.md                 # This file
├── nginx/
│   └── nginx.conf           # Nginx reverse proxy configuration
└── tidb/
    └── init/
        └── 01-init-database.sql  # Database initialization script
```

## Volumes

- `tidb_data`: TiDB database files
- `redis_data`: Redis persistence files

## Networks

- `fastapi_mcp_network`: Bridge network for all services

## Health Checks

All services include health checks:

- **FastAPI**: HTTP GET to `/health`
- **TiDB**: MySQL connection test
- **Redis**: Redis PING command

## Troubleshooting

### Service Won't Start

1. Check logs: `make logs` or `docker-compose logs [service_name]`
2. Check health: `make health`
3. Restart services: `make restart`

### Database Connection Issues

1. Ensure TiDB is healthy: `docker-compose exec tidb mysql -h localhost -P 4000 -u root -e "SELECT 1"`
2. Check database exists: `make db-shell` then `SHOW DATABASES;`
3. Reset database: `make db-reset`

### Redis Connection Issues

1. Test Redis: `make redis-cli` then `ping`
2. Check Redis logs: `docker-compose logs redis`

### Port Conflicts

If ports are already in use, modify the port mappings in `docker-compose.yml`:

```yaml
services:
  fastapi_app:
    ports:
      - "8001:8000"  # Change host port
```

## Performance Tuning

### Production Optimizations

1. **Resource Limits**: Configured in `docker-compose.prod.yml`
2. **Redis Memory**: Limited with LRU eviction policy
3. **TiDB**: Optimized session variables in init script
4. **Nginx**: Rate limiting and caching configured

### Monitoring

```bash
# Monitor resource usage
make monitor

# Or manually:
docker stats
```

## Security Considerations

1. **Non-root User**: FastAPI runs as non-root user
2. **Secret Management**: Use environment variables for secrets
3. **Network Isolation**: Services communicate via internal network
4. **SSL/TLS**: Configure nginx with SSL certificates for production
5. **Rate Limiting**: Nginx includes rate limiting configuration

## Backup and Recovery

### Database Backup

```bash
# Create backup
make db-backup

# Or manually:
docker-compose exec tidb mysqldump -h localhost -P 4000 -u root fastapi_mcp > backup.sql
```

### Volume Backup

```bash
# Backup volumes
docker run --rm -v fastapi_mcp_tidb_data:/data -v $(pwd):/backup alpine tar czf /backup/tidb_backup.tar.gz -C /data .
docker run --rm -v fastapi_mcp_redis_data:/data -v $(pwd):/backup alpine tar czf /backup/redis_backup.tar.gz -C /data .
```

## Development Workflow

1. **Start Development Environment**: `make dev`
2. **Make Code Changes**: Files are mounted for hot reload
3. **Run Tests**: `make test`
4. **Check Health**: `make health`
5. **View Logs**: `make logs`
6. **Clean Up**: `make clean`