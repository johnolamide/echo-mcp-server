"""
Agent model for managing user AI agents with service integrations.
"""
from datetime import datetime
from typing import Optional, Dict, Any, List, TYPE_CHECKING
from sqlmodel import Field, Relationship, SQLModel, JSON, Column

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.service import Service


class AgentBase(SQLModel):
    """Base agent model."""
    user_id: int = Field(foreign_key="users.id", index=True)
    name: str = Field(max_length=255, default="My Agent")
    description: Optional[str] = None
    config: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    is_active: bool = Field(default=True)


class Agent(AgentBase, table=True):
    """
    Agent database model.
    """
    __tablename__ = "agents"
    
    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    user: "User" = Relationship(back_populates="agents")
    services: List["UserService"] = Relationship(back_populates="agent")


class UserService(SQLModel, table=True):
    """
    Association table for user-service relationships (plug-and-play).
    """
    __tablename__ = "user_services"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    service_id: int = Field(foreign_key="services.id", index=True)
    agent_id: Optional[int] = Field(default=None, foreign_key="agents.id", index=True)
    added_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)
    
    # Relationships
    user: "User" = Relationship(back_populates="user_services")
    service: "Service" = Relationship(back_populates="user_services")
    agent: Optional["Agent"] = Relationship(back_populates="services")