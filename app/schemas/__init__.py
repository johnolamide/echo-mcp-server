"""
Pydantic schemas for API validation.
"""

# Authentication schemas
from .auth import (
    UserRegistration,
    UserLogin,
    UserResponse,
    AdminUserResponse,
)

# Service schemas
from .service import (
    ServiceCreate,
    ServiceUpdate,
    ServiceResponse,
    ServiceDetailResponse,
    ServiceList,
    ServiceDeleteResponse,
    ServiceStatusUpdate,
    ServiceSearchQuery,
)

# Chat schemas
from .chat import (
    MessageSend,
    MessageResponse,
    ChatHistory,
    WebSocketMessage,
    WebSocketConnect,
    MessageMarkRead,
    MessageMarkReadResponse,
    ChatHistoryQuery,
    TypingIndicator,
    ConversationList,
    MessageDelete,
    MessageDeleteResponse,
)

# Admin schemas
from .admin import (
    UserListResponse,
    UserDetailResponse,
    UserStatsResponse,
)

__all__ = [
    # Auth schemas
    "UserRegistration",
    "UserLogin", 
    "UserResponse",
    "AdminUserResponse",
    # Service schemas
    "ServiceCreate",
    "ServiceUpdate",
    "ServiceResponse",
    "ServiceDetailResponse",
    "ServiceList",
    "ServiceDeleteResponse",
    "ServiceStatusUpdate",
    "ServiceSearchQuery",
    # Chat schemas
    "MessageSend",
    "MessageResponse",
    "ChatHistory",
    "WebSocketMessage",
    "WebSocketConnect",
    "MessageMarkRead",
    "MessageMarkReadResponse",
    "ChatHistoryQuery",
    "TypingIndicator",
    "ConversationList",
    "MessageDelete",
    "MessageDeleteResponse",
    # Admin schemas
    "UserListResponse",
    "UserDetailResponse",
    "UserStatsResponse",
]