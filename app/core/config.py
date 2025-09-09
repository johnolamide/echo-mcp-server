"""
Core configuration module with environment-based settings.
"""
import os
from typing import Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application settings
    app_name: str = "Echo MCP Server"
    app_version: str = "1.0.0"
    debug: bool = False
    port: int = 8000
    
    # Database settings
    database_url_env: Optional[str] = os.getenv("DATABASE_URL")  # Direct DATABASE_URL override
    tidb_host: str = "localhost"
    tidb_port: int = 4000
    tidb_user: str = "root"
    tidb_password: str = ""
    tidb_database: str = "echo_mcp_tidb"
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout: int = 30
    db_pool_recycle: int = 1800

    @property
    def database_url(self) -> str:
        """Construct TiDB/MySQL connection URL using mysql-connector-python."""
        # If DATABASE_URL is provided, use it directly
        if self.database_url_env:
            return self.database_url_env
            
        # Otherwise construct from individual components
        password_part = f":{self.tidb_password}" if self.tidb_password else ""
        return f"mysql+mysqlconnector://{self.tidb_user}{password_part}@{self.tidb_host}:{self.tidb_port}/{self.tidb_database}?charset=utf8mb4"
    
    # Redis settings
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: Optional[str] = None
    redis_db: int = 0
    
    @property
    def redis_url(self) -> str:
        """Construct Redis connection URL."""
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    # JWT settings
    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7
    
    # Email settings
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    email_from: Optional[str] = None
    
    # CORS settings
    cors_origins: list = [
        "http://localhost:3000", 
        "http://localhost:8080",
        "https://echo-mcp-server.qkiu.tech",
        "http://echo-mcp-server.qkiu.tech"
    ]
    cors_allow_credentials: bool = True
    cors_allow_methods: list = ["*"]
    cors_allow_headers: list = ["*"]
    
    # Security settings
    password_min_length: int = 8
    bcrypt_rounds: int = 12
    
    # Admin settings
    admin_secret_key: str = "change-this-admin-secret-in-production"
    
    @field_validator("jwt_secret_key")
    @classmethod
    def validate_secret_key(cls, v):
        """Ensure JWT secret key is secure in production."""
        if not v or v == "your-secret-key-change-in-production":
            if os.getenv("ENVIRONMENT") == "production":
                raise ValueError("JWT secret key must be set in production")
        return v
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False
    }


# Global settings instance
settings = Settings()