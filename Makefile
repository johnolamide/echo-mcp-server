# FastAPI MCP Backend - Docker Management

.PHONY: help build up down logs clean dev test prod restart health

# Default target
help:
	@echo "FastAPI MCP Backend - Docker Commands"
	@echo "====================================="
	@echo "build     - Build all Docker images"
	@echo "up        - Start all services"
	@echo "down      - Stop all services"
	@echo "logs      - Show logs from all services"
	@echo "clean     - Remove all containers, images, and volumes"
	@echo "dev       - Start development environment with hot reload"
	@echo "test      - Run tests in Docker container"
	@echo "prod      - Start production environment"
	@echo "restart   - Restart all services"
	@echo "health    - Check health of all services"
	@echo "shell     - Open shell in FastAPI container"
	@echo "db-shell  - Open TiDB shell"
	@echo "redis-cli - Open Redis CLI"

# Build Docker images
build:
	docker-compose build

# Start all services
up:
	docker-compose up -d

# Stop all services
down:
	docker-compose down

# Show logs
logs:
	docker-compose logs -f

# Clean up everything
clean:
	docker-compose down -v --rmi all --remove-orphans
	docker system prune -f

# Development environment
dev:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
	@echo "Development environment started!"
	@echo "FastAPI: http://localhost:8000"
	@echo "Docs: http://localhost:8000/docs"
	@echo "Adminer: http://localhost:8080 (if admin profile enabled)"
	@echo "Redis Commander: http://localhost:8081 (if admin profile enabled)"

# Start with admin tools
dev-admin:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml --profile admin up -d

# Run tests
test:
	docker-compose exec fastapi_app python -m pytest tests/ -v

# Production environment
prod:
	docker-compose -f docker-compose.yml up -d --build

# Restart services
restart:
	docker-compose restart

# Health check
health:
	@echo "Checking service health..."
	@docker-compose ps
	@echo "\nFastAPI Health:"
	@curl -s http://localhost:8000/health | python -m json.tool || echo "FastAPI not responding"
	@echo "\nTiDB Health:"
	@docker-compose exec tidb mysql -h localhost -P 4000 -u root -e "SELECT 'TiDB is healthy' as status;" || echo "TiDB not responding"
	@echo "\nRedis Health:"
	@docker-compose exec redis redis-cli ping || echo "Redis not responding"

# Open shell in FastAPI container
shell:
	docker-compose exec fastapi_app /bin/bash

# Open TiDB shell
db-shell:
	docker-compose exec tidb mysql -h localhost -P 4000 -u root

# Open Redis CLI
redis-cli:
	docker-compose exec redis redis-cli

# View container logs
logs-app:
	docker-compose logs -f fastapi_app

logs-db:
	docker-compose logs -f tidb

logs-redis:
	docker-compose logs -f redis

# Database operations
db-reset:
	docker-compose exec tidb mysql -h localhost -P 4000 -u root -e "DROP DATABASE IF EXISTS fastapi_mcp; CREATE DATABASE fastapi_mcp;"
	docker-compose restart fastapi_app

# Backup database
db-backup:
	docker-compose exec tidb mysqldump -h localhost -P 4000 -u root fastapi_mcp > backup_$(shell date +%Y%m%d_%H%M%S).sql

# Monitor resources
monitor:
	docker stats
# Py
thon dependency management
install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt

install-prod:
	pip install -r requirements-prod.txt

# Pip-tools dependency compilation
compile-deps:
	pip-compile requirements.in
	pip-compile requirements-dev.in

update-deps:
	pip-compile --upgrade requirements.in
	pip-compile --upgrade requirements-dev.in

# Package installation
install-package:
	pip install -e .

install-package-dev:
	pip install -e ".[dev]"

# Dependency security check
security-check:
	safety check -r requirements.txt

# Virtual environment setup
venv:
	python -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements-dev.txt

# Clean up
clean-deps:
	pip freeze | grep -v "^-e" | xargs pip uninstall -y