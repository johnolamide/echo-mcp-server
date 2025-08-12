"""
Chat schemas for API validation.
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, validator


class MessageSend(BaseModel):
    """Schema for sending a chat message."""
    receiver_id: int = Field(..., gt=0, description="ID of the message receiver")
    content: str = Field(..., min_length=1, max_length=2000, description="Message content")
    
    @validator('content')
    def validate_content(cls, v):
        """Validate message content."""
        if not v.strip():
            raise ValueError('Message content cannot be empty or whitespace only')
        return v.strip()
    
    class Config:
        schema_extra = {
            "example": {
                "receiver_id": 2,
                "content": "Hello! How are you doing today?"
            }
        }


class MessageResponse(BaseModel):
    """Schema for chat message response."""
    id: int = Field(..., description="Message ID")
    sender_id: int = Field(..., description="ID of the message sender")
    receiver_id: int = Field(..., description="ID of the message receiver")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(..., description="Message timestamp")
    is_read: bool = Field(..., description="Whether message has been read")
    sender_username: Optional[str] = Field(None, description="Username of the sender")
    receiver_username: Optional[str] = Field(None, description="Username of the receiver")
    
    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "id": 1,
                "sender_id": 1,
                "receiver_id": 2,
                "content": "Hello! How are you doing today?",
                "timestamp": "2023-01-01T12:00:00Z",
                "is_read": False,
                "sender_username": "johndoe",
                "receiver_username": "janedoe"
            }
        }


class ChatHistory(BaseModel):
    """Schema for chat history response."""
    messages: List[MessageResponse] = Field(..., description="List of chat messages")
    total_messages: int = Field(..., description="Total number of messages in conversation")
    unread_count: int = Field(..., description="Number of unread messages for the requesting user")
    other_user_id: int = Field(..., description="ID of the other user in the conversation")
    other_username: Optional[str] = Field(None, description="Username of the other user")
    
    class Config:
        schema_extra = {
            "example": {
                "messages": [
                    {
                        "id": 1,
                        "sender_id": 1,
                        "receiver_id": 2,
                        "content": "Hello! How are you doing today?",
                        "timestamp": "2023-01-01T12:00:00Z",
                        "is_read": True,
                        "sender_username": "johndoe",
                        "receiver_username": "janedoe"
                    }
                ],
                "total_messages": 1,
                "unread_count": 0,
                "other_user_id": 2,
                "other_username": "janedoe"
            }
        }


class WebSocketMessage(BaseModel):
    """Schema for WebSocket message data."""
    type: str = Field(..., description="Message type (message, typing, read_receipt, etc.)")
    data: dict = Field(..., description="Message data payload")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Message timestamp")
    
    class Config:
        schema_extra = {
            "example": {
                "type": "message",
                "data": {
                    "id": 1,
                    "sender_id": 1,
                    "receiver_id": 2,
                    "content": "Hello via WebSocket!",
                    "sender_username": "johndoe"
                },
                "timestamp": "2023-01-01T12:00:00Z"
            }
        }


class WebSocketConnect(BaseModel):
    """Schema for WebSocket connection data."""
    user_id: int = Field(..., gt=0, description="ID of the connecting user")
    token: str = Field(..., description="Authentication token")
    
    class Config:
        schema_extra = {
            "example": {
                "user_id": 1,
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }


class MessageMarkRead(BaseModel):
    """Schema for marking messages as read."""
    message_ids: List[int] = Field(..., description="List of message IDs to mark as read")
    
    @validator('message_ids')
    def validate_message_ids(cls, v):
        """Validate message IDs."""
        if not v:
            raise ValueError('At least one message ID must be provided')
        if len(v) > 100:
            raise ValueError('Cannot mark more than 100 messages as read at once')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "message_ids": [1, 2, 3]
            }
        }


class MessageMarkReadResponse(BaseModel):
    """Schema for mark as read response."""
    marked_count: int = Field(..., description="Number of messages marked as read")
    message: str = Field(..., description="Success message")
    
    class Config:
        schema_extra = {
            "example": {
                "marked_count": 3,
                "message": "Messages marked as read successfully"
            }
        }


class ChatHistoryQuery(BaseModel):
    """Schema for chat history query parameters."""
    other_user_id: int = Field(..., gt=0, description="ID of the other user in conversation")
    limit: Optional[int] = Field(50, ge=1, le=200, description="Maximum number of messages to return")
    offset: Optional[int] = Field(0, ge=0, description="Number of messages to skip")
    before_timestamp: Optional[datetime] = Field(None, description="Get messages before this timestamp")
    after_timestamp: Optional[datetime] = Field(None, description="Get messages after this timestamp")
    include_read: Optional[bool] = Field(True, description="Whether to include read messages")
    
    class Config:
        schema_extra = {
            "example": {
                "other_user_id": 2,
                "limit": 50,
                "offset": 0,
                "include_read": True
            }
        }


class TypingIndicator(BaseModel):
    """Schema for typing indicator."""
    user_id: int = Field(..., gt=0, description="ID of the user who is typing")
    is_typing: bool = Field(..., description="Whether user is currently typing")
    
    class Config:
        schema_extra = {
            "example": {
                "user_id": 1,
                "is_typing": True
            }
        }


class ConversationList(BaseModel):
    """Schema for listing user conversations."""
    conversations: List[dict] = Field(..., description="List of conversations")
    total_conversations: int = Field(..., description="Total number of conversations")
    total_unread: int = Field(..., description="Total unread messages across all conversations")
    
    class Config:
        schema_extra = {
            "example": {
                "conversations": [
                    {
                        "other_user_id": 2,
                        "other_username": "janedoe",
                        "last_message": {
                            "content": "Hello! How are you?",
                            "timestamp": "2023-01-01T12:00:00Z",
                            "is_from_me": True
                        },
                        "unread_count": 0,
                        "total_messages": 5
                    }
                ],
                "total_conversations": 1,
                "total_unread": 0
            }
        }


class MessageDelete(BaseModel):
    """Schema for deleting a message."""
    message_id: int = Field(..., gt=0, description="ID of the message to delete")
    
    class Config:
        schema_extra = {
            "example": {
                "message_id": 1
            }
        }


class MessageDeleteResponse(BaseModel):
    """Schema for message deletion response."""
    message: str = Field(..., description="Deletion confirmation message")
    deleted_message_id: int = Field(..., description="ID of the deleted message")
    
    class Config:
        schema_extra = {
            "example": {
                "message": "Message deleted successfully",
                "deleted_message_id": 1
            }
        }


class WebSocketMessageType(BaseModel):
    """Schema for WebSocket message types."""
    type: str = Field(..., description="Message type")
    data: dict = Field(..., description="Message data")
    
    class Config:
        schema_extra = {
            "example": {
                "type": "send_message",
                "data": {
                    "receiver_id": 2,
                    "content": "Hello via WebSocket!"
                }
            }
        }


class OnlineStatusResponse(BaseModel):
    """Schema for online status response."""
    online_users: List[int] = Field(..., description="List of online user IDs")
    total_online: int = Field(..., description="Total number of online users")
    requesting_user: int = Field(..., description="ID of the requesting user")
    
    class Config:
        schema_extra = {
            "example": {
                "online_users": [1, 2, 3],
                "total_online": 3,
                "requesting_user": 1
            }
        }


class UserStatusResponse(BaseModel):
    """Schema for individual user status response."""
    user_id: int = Field(..., description="User ID")
    is_online: bool = Field(..., description="Whether user is online")
    connection_count: int = Field(..., description="Number of active connections")
    checked_by: int = Field(..., description="ID of user who checked the status")
    
    class Config:
        schema_extra = {
            "example": {
                "user_id": 2,
                "is_online": True,
                "connection_count": 1,
                "checked_by": 1
            }
        }