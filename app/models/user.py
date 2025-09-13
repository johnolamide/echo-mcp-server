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
    username: str = Field(unique=True, index=True, max_length=50)
    is_active: bool = Field(default=True)
    is_admin: bool = Field(default=False)


class User(UserBase, table=True):
    """
    User database model.
    """
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    
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
            Index('idx_user_username_active', 'username', 'is_active'),
        )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}')>"


class UserCreate(UserBase):
    """Model for creating a new user."""
    pass


class UserRead(UserBase):
    """Model for reading user data (e.g., in API responses)."""
    id: int
    created_at: datetime
    updated_at: datetime


class UserUpdate(SQLModel):
    """Model for updating user data."""
    username: Optional[str] = None
    is_active: Optional[bool] = None
