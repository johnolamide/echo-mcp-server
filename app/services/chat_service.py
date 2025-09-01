"""
Chat service for message management.
"""
from typing import List, Optional
from sqlmodel import Session, select
from app.models.chat import ChatMessage
from app.schemas.chat import MessageCreate

class ChatService:
    """Service for chat operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def send_message(self, sender_id: int, message_data: MessageCreate) -> ChatMessage:
        """Send a message."""
        message = ChatMessage(
            sender_id=sender_id,
            receiver_id=message_data.receiver_id,
            content=message_data.content,
            is_read=False
        )
        
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        
        return message
    
    def get_chat_history(
        self, 
        user_id: int, 
        other_user_id: int, 
        limit: int = 50, 
        offset: int = 0
    ) -> List[ChatMessage]:
        """Get chat history between two users."""
        from sqlalchemy import or_, and_
        statement = select(ChatMessage).where(
            or_(
                and_(ChatMessage.sender_id == user_id, ChatMessage.receiver_id == other_user_id),
                and_(ChatMessage.sender_id == other_user_id, ChatMessage.receiver_id == user_id)
            )
        ).order_by(ChatMessage.timestamp.desc()).offset(offset).limit(limit)
        return self.db.exec(statement).all()
    
    def get_conversations(self, user_id: int, limit: int = 20) -> List[dict]:
        """Get conversations for a user."""
        # This is a simplified implementation
        # In a real app, you'd want to get the latest message for each conversation
        from sqlalchemy import or_
        statement = select(ChatMessage).where(
            or_(ChatMessage.sender_id == user_id, ChatMessage.receiver_id == user_id)
        ).order_by(ChatMessage.timestamp.desc()).limit(limit)
        conversations = self.db.exec(statement).all()
        
        return [
            {
                "other_user_id": msg.receiver_id if msg.sender_id == user_id else msg.sender_id,
                "last_message": msg.content,
                "timestamp": msg.timestamp,
                "is_read": msg.is_read
            }
            for msg in conversations
        ]