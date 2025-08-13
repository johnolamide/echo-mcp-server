"""
Main FastAPI application with router registration, middleware, and lifecycle events.
"""
import logging
import time
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from fastapi_mcp import FastApiMCP

from app.core.config import settings
from app.db.database import (
    db_manager, 
    create_db_and_tables, 
    check_database_connection
)
from app.db.redis_client import init_redis, close_redis, redis_manager
from app.routers import auth, chat, services, admin

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown events.
    """
    # Startup
    logger.info("Starting Echo Backend application...")

    # Retry database connection
    max_retries = 30
    retries = 0
    while retries < max_retries:
        try:
            logger.info(f"Attempting to initialize application (attempt {retries + 1}/{max_retries})...")
            
            logger.info("Creating database and tables...")
            create_db_and_tables()
            logger.info("Database and tables created successfully.")
            
            # Initialize Redis
            logger.info("Initializing Redis connection...")
            await init_redis()
            
            # Verify Redis connection
            redis_health = await redis_manager.health_check()
            if redis_health.get("redis") != "healthy":
                raise Exception(f"Redis connection unhealthy: {redis_health}")
            
            logger.info("Application startup completed successfully")
            break  # Exit loop on success
            
        except Exception as e:
            retries += 1
            logger.warning(f"Startup attempt {retries}/{max_retries} failed: {e}")
            if retries >= max_retries:
                logger.error("Application startup failed after multiple retries.")
                raise
            time.sleep(5) # Wait 5 seconds before retrying

    yield
    
    # Shutdown
    logger.info("Shutting down FastAPI Backend application...")
    
    try:
        # Close Redis connections
        await close_redis()
        logger.info("Redis connections closed")
        
        # Close database connections
        db_manager.close_all_connections()
        logger.info("Database connections closed")
        
        logger.info("Application shutdown completed successfully")
        
    except Exception as e:
        logger.error(f"Error during application shutdown: {e}")


# Create FastAPI application with lifespan manager
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="A modular FastAPI backend with authentication, chat, and service management",
    debug=settings.debug,
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

mcp = FastApiMCP(
    app,
    include_operations=[
        "register_user",
        "register_admin",
        "login",
        "refresh_token",
        "verify_email",
        "resend_verification",
        "logout",
        "request_reset_password",
        "reset_password",
        "get_info",
        "get_info",
        "update_info"
    ]
)

# MCP integration
mcp.mount_http()


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)


# Add trusted host middleware for security
if not settings.debug:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", "*.yourdomain.com"]
    )


# Global exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with consistent error format."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
                "path": str(request.url.path)
            }
        }
    )


@app.exception_handler(StarletteHTTPException)
async def starlette_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle Starlette HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
                "path": str(request.url.path)
            }
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors."""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(x) for x in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": errors,
                "path": str(request.url.path)
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    if settings.debug:
        # In debug mode, return detailed error information
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": str(exc),
                    "type": type(exc).__name__,
                    "path": str(request.url.path)
                }
            }
        )
    else:
        # In production, return generic error message
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred",
                    "path": str(request.url.path)
                }
            }
        )


# Middleware for request logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests."""
    start_time = request.state.start_time = __import__("time").time()
    
    # Log request
    logger.info(f"Request: {request.method} {request.url.path}")
    
    # Process request
    response = await call_next(request)
    
    # Log response
    process_time = __import__("time").time() - start_time
    logger.info(
        f"Response: {response.status_code} - {request.method} {request.url.path} "
        f"completed in {process_time:.4f}s"
    )
    
    # Add process time header
    response.headers["X-Process-Time"] = str(process_time)
    
    return response


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check() -> Dict[str, Any]:
    """
    Application health check endpoint.
    
    Returns:
        dict: Health status of all application components
    """
    health_status = {
        "status": "healthy",
        "version": settings.app_version,
        "components": {}
    }
    
    try:
        # Check database health
        db_health = db_manager.health_check()
        health_status["components"]["database"] = db_health
        
        # Check Redis health
        redis_health = await redis_manager.health_check()
        health_status["components"]["redis"] = redis_health
        
        # Determine overall health
        if (db_health.get("database") != "healthy" or 
            redis_health.get("redis") != "healthy"):
            health_status["status"] = "unhealthy"
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        health_status["status"] = "unhealthy"
        health_status["error"] = str(e)
    
    return health_status


# Root endpoint
@app.get("/", tags=["Root"])
async def root() -> Dict[str, str]:
    """
    Root endpoint with application information.
    
    Returns:
        dict: Basic application information
    """
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "description": "Echo MCP Server - REST API with authentication, chat, and service management",
        "docs_url": "/docs" if settings.debug else "Documentation disabled in production",
        "health_url": "/health"
    }


# Register routers (routers already have their own prefixes defined)
app.include_router(
    auth.router,
    tags=["Authentication"]
)

app.include_router(
    chat.router,
    tags=["Chat"]
)

app.include_router(
    services.router,
    tags=["Services"]
)

app.include_router(
    admin.router,
    tags=["Admin"]
)


mcp.setup_server()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info"
    )