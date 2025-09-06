"""
Service model for managing platform services with external API integration using SQLModel.
"""
from datetime import datetime
from typing import Optional, Dict, Any, TYPE_CHECKING, List
from sqlmodel import Field, Relationship, SQLModel, Index, JSON, Column

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.agent import UserService


class ServiceBase(SQLModel):
    """Base service model."""
    name: str = Field(max_length=255, index=True)
    type: str = Field(max_length=100, index=True)
    description: Optional[str] = None
    api_base_url: str = Field(max_length=500)
    api_endpoint: str = Field(max_length=255)
    http_method: str = Field(max_length=10, default="POST")
    request_template: Dict[str, Any] = Field(sa_column=Column(JSON))
    response_mapping: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    headers_template: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    encrypted_api_key: Optional[str] = Field(default=None, max_length=500)
    api_key_header: Optional[str] = Field(default=None, max_length=100)
    timeout_seconds: int = 30
    retry_attempts: int = 3
    is_active: bool = Field(default=True, index=True)


class Service(ServiceBase, table=True):
    """
    Service database model.
    """
    __tablename__ = "services"
    
    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    created_by: int = Field(foreign_key="users.id", index=True)
    
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    
        # Relationship
    creator: "User" = Relationship(back_populates="created_services")
    user_services: List["UserService"] = Relationship(back_populates="service")
    
    class Config:
        table_args = (
            Index('idx_service_name_active', 'name', 'is_active'),
            Index('idx_service_type_active', 'type', 'is_active'),
        )

    def __repr__(self) -> str:
        return f"<Service(id={self.id}, name='{self.name}', type='{self.type}', is_active={self.is_active})>"


class ServiceCreate(ServiceBase):
    """Model for creating a new service."""
    pass


class ServiceRead(ServiceBase):
    """Model for reading service data."""
    id: int
    created_by: int
    created_at: datetime
    updated_at: datetime


class ServiceUpdate(SQLModel):
    """Model for updating a service."""
    name: Optional[str] = None
    type: Optional[str] = None
    description: Optional[str] = None
    api_base_url: Optional[str] = None
    api_endpoint: Optional[str] = None
    http_method: Optional[str] = None
    request_template: Optional[Dict[str, Any]] = None
    response_mapping: Optional[Dict[str, Any]] = None
    headers_template: Optional[Dict[str, Any]] = None
    encrypted_api_key: Optional[str] = None
    api_key_header: Optional[str] = None
    timeout_seconds: Optional[int] = None
    retry_attempts: Optional[int] = None
    is_active: Optional[bool] = None
