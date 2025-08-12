"""
Chat message model for real-time messaging functionality using SQLModel.
"""
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlmodel import Field, Relationship, SQLModel, Index

if TYPE_CHECKING:
    from app.models.user import User


class ChatMessageBase(SQLModel):
    """Base chat message model."""
    content: str
    is_read: bool = Field(default=False, index=True)


class ChatMessage(ChatMessageBase, table=True):
    """
    Chat message database model.
    """
    __tablename__ = "chat_messages"
    
    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    sender_id: int = Field(foreign_key="users.id", index=True)
    receiver_id: int = Field(foreign_key="users.id", index=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    sender: "User" = Relationship(back_populates="sent_messages", sa_relationship_kwargs={"foreign_keys": "[ChatMessage.sender_id]"})
    receiver: "User" = Relationship(back_populates="received_messages", sa_relationship_kwargs={"foreign_keys": "[ChatMessage.receiver_id]"})
    
    class Config:
        table_args = (
            Index('idx_chat_conversation_timestamp', 'sender_id', 'receiver_id', 'timestamp'),
        )

    def __repr__(self) -> str:
        content_preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"<ChatMessage(id={self.id}, sender_id={self.sender_id}, receiver_id={self.receiver_id}, content='{content_preview}')>"


class ChatMessageCreate(ChatMessageBase):
    """Model for creating a new chat message."""
    receiver_id: int


class ChatMessageRead(ChatMessageBase):
    """Model for reading chat message data."""
    id: int
    sender_id: int
    receiver_id: int
    timestamp: datetime
