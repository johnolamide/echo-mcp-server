"""
User model for authentication and user management using SQLModel.
"""
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlmodel import Field, Relationship, SQLModel, Index

if TYPE_CHECKING:
    from app.models.chat import ChatMessage
    from app.models.service import Service
    from app.models.agent import Agent, UserService


class UserBase(SQLModel):
    """Base user model with common fields."""
    username: str = Field(max_length=50, unique=True, index=True)
    email: str = Field(max_length=255, unique=True, index=True)
    is_active: bool = Field(default=True)
    is_verified: bool = Field(default=False)
    is_admin: bool = Field(default=False)


class User(UserBase, table=True):
    """
    User database model.
    """
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    hashed_password: str = Field(max_length=255)
    
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    
    # Relationships
    sent_messages: List["ChatMessage"] = Relationship(
        back_populates="sender",
        sa_relationship_kwargs={"foreign_keys": "ChatMessage.sender_id"}
    )
    received_messages: List["ChatMessage"] = Relationship(
        back_populates="receiver", 
        sa_relationship_kwargs={"foreign_keys": "ChatMessage.receiver_id"}
    )
    created_services: List["Service"] = Relationship(back_populates="creator")
    agents: List["Agent"] = Relationship(back_populates="user")
    user_services: List["UserService"] = Relationship(back_populates="user")
    
    class Config:
        table_args = (
            Index('idx_user_email_active', 'email', 'is_active'),
            Index('idx_user_username_active', 'username', 'is_active'),
        )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}', is_admin={self.is_admin})>"


class UserCreate(UserBase):
    """Model for creating a new user."""
    password: str


class UserRead(UserBase):
    """Model for reading user data (e.g., in API responses)."""
    id: int
    created_at: datetime
    updated_at: datetime


class UserUpdate(SQLModel):
    """Model for updating user data."""
    username: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    is_admin: Optional[bool] = None
