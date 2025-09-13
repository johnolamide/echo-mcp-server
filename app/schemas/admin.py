"""
Admin schemas for user management API validation.
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field

from .auth import UserResponse


class UserListResponse(BaseModel):
    """Schema for user list response."""
    users: List[UserResponse] = Field(..., description="List of users")
    total: int = Field(..., description="Total number of users")
    active_count: int = Field(..., description="Number of active users")
    verified_count: int = Field(..., description="Number of verified users (always 0 in demo)")
    admin_count: int = Field(..., description="Number of admin users (always 0 in demo)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "users": [
                    {
                        "id": 1,
                        "username": "johndoe",
                        "is_active": True,
                        "created_at": "2023-01-01T00:00:00Z",
                        "updated_at": "2023-01-01T00:00:00Z"
                    }
                ],
                "total": 10,
                "active_count": 8,
                "verified_count": 0,
                "admin_count": 0
            }
        }


class UserDetailResponse(BaseModel):
    """Schema for detailed user information response."""
    id: int = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    is_active: bool = Field(..., description="Whether user account is active")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Last account update timestamp")
    
    # Additional comprehensive information
    total_messages_sent: int = Field(..., description="Total number of messages sent by user")
    total_messages_received: int = Field(..., description="Total number of messages received by user")
    services_created: int = Field(..., description="Number of services created by user")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "username": "johndoe",
                "is_active": True,
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-01-01T00:00:00Z",
                "total_messages_sent": 25,
                "total_messages_received": 30,
                "services_created": 3,
                "last_login": "2023-01-15T10:30:00Z"
            }
        }


class UserStatsResponse(BaseModel):
    """Schema for user statistics response."""
    total_users: int = Field(..., description="Total number of users")
    active_users: int = Field(..., description="Number of active users")
    verified_users: int = Field(..., description="Number of verified users (always 0 in demo)")
    admin_users: int = Field(..., description="Number of admin users (always 0 in demo)")
    recent_registrations: int = Field(..., description="Number of recent registrations (last 30 days)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_users": 100,
                "active_users": 85,
                "verified_users": 80,
                "admin_users": 5,
                "recent_registrations": 15
            }
        }