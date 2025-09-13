"""
Simplified authentication schemas for username-only access.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, validator
import re


class UserRegistration(BaseModel):
    """Schema for user registration."""
    username: str = Field(..., min_length=3, max_length=50, description="Username for the account")
    
    @validator('username')
    def validate_username(cls, v):
        """Validate username format."""
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Username can only contain letters, numbers, underscores, and hyphens')
        return v.lower()
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "johndoe"
            }
        }


class AdminUserRegistration(BaseModel):
    """Schema for admin user registration."""
    username: str = Field(..., min_length=3, max_length=50, description="Username for the admin account")
    admin_secret: str = Field(..., description="Admin creation secret key")
    
    @validator('username')
    def validate_username(cls, v):
        """Validate username format."""
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Username can only contain letters, numbers, underscores, and hyphens')
        return v.lower()
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "admin",
                "admin_secret": "your-admin-secret-key"
            }
        }


class AdminUserResponse(BaseModel):
    """Schema for admin user creation response."""
    message: str = Field(..., description="Success message")
    user_id: str = Field(..., description="Created admin user ID")
    username: str = Field(..., description="Admin username")
    is_admin: bool = Field(..., description="Admin status")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Admin user created successfully",
                "user_id": "1",
                "username": "admin",
                "is_admin": True
            }
        }


class UserLogin(BaseModel):
    """Schema for user login."""
    username: str = Field(..., description="Username for login")
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "john"
            }
        }


class UserResponse(BaseModel):
    """Schema for user response data."""
    id: int = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    is_active: bool = Field(..., description="Whether user account is active")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Last account update timestamp")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "username": "johndoe",
                "is_active": True,
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-01-01T00:00:00Z"
            }
        }


class TokenResponse(BaseModel):
    """Schema for token response."""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    user: UserResponse = Field(..., description="User information")
    
    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwidXNlcm5hbWUiOiJqb2huZG9lIiwiZW1haWwiOiJqb2huLmRvZUBleGFtcGxlLmNvbSIsImlzX2FkbWluIjpmYWxzZSwiZXhwIjoxNjQwOTk1MjAwfQ.example_signature",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiZXhwIjoxNjQxNjAwMDAwLCJ0eXBlIjoicmVmcmVzaCJ9.example_refresh_signature",
                "token_type": "bearer",
                "expires_in": 1800,
                "user": {
                    "id": 1,
                    "username": "johndoe",
                    "email": "john.doe@example.com",
                    "is_active": True,
                    "is_verified": True,
                    "is_admin": False,
                    "created_at": "2023-01-01T00:00:00Z",
                    "updated_at": "2023-01-01T00:00:00Z"
                }
            }
        }


class TokenRefresh(BaseModel):
    """Schema for token refresh request."""
    refresh_token: str = Field(..., description="Refresh token to exchange for new access token")
    
    class Config:
        json_schema_extra = {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }


class TokenRefreshResponse(BaseModel):
    """Schema for token refresh response."""
    access_token: str = Field(..., description="New JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    
    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 3600
            }
        }


class EmailVerification(BaseModel):
    """Schema for email verification."""
    token: str = Field(..., description="Email verification token")
    
    class Config:
        json_schema_extra = {
            "example": {
                "token": "verification_token_here"
            }
        }


class EmailVerificationResponse(BaseModel):
    """Schema for email verification response."""
    message: str = Field(..., description="Verification result message")
    verified: bool = Field(..., description="Whether verification was successful")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Email verified successfully",
                "verified": True
            }
        }


class LogoutResponse(BaseModel):
    """Schema for logout response."""
    message: str = Field(..., description="Logout confirmation message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Successfully logged out"
            }
        }