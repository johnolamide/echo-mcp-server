"""
WebSocket connection manager for real-time chat functionality.
"""
import json
import logging
from typing import Dict, List, Optional, Set
from datetime import datetime

from fastapi import WebSocket, WebSocketDisconnect
from sqlmodel import Session

from app.db.redis_client import redis_pubsub, redis_cache
from app.models.user import User
from app.models.chat import ChatMessage
from app.schemas.chat import WebSocketMessage, MessageResponse

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time chat."""
    
    def __init__(self):
        # Store active connections: user_id -> List[WebSocket]
        self.active_connections: Dict[int, List[WebSocket]] = {}
        # Store user info for connections: WebSocket -> user_id
        self.connection_users: Dict[WebSocket, int] = {}
        # Store typing indicators: user_id -> Set[user_id] (who is typing to whom)
        self.typing_indicators: Dict[int, Set[int]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: int):
        """Accept WebSocket connection and register user."""
        await websocket.accept()
        
        # Add connection to user's connection list
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        
        self.active_connections[user_id].append(websocket)
        self.connection_users[websocket] = user_id
        
        # Subscribe to user's chat channel for Redis Pub/Sub
        await self._subscribe_to_user_channel(user_id)
        
        logger.info(f"User {user_id} connected via WebSocket")
        
        # Send connection confirmation
        await self.send_personal_message({
            "type": "connection_confirmed",
            "data": {
                "user_id": user_id,
                "message": "Connected to chat server",
                "timestamp": datetime.utcnow().isoformat()
            }
        }, websocket)
    
    async def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection and cleanup."""
        user_id = self.connection_users.get(websocket)
        
        if user_id:
            # Remove from active connections
            if user_id in self.active_connections:
                self.active_connections[user_id].remove(websocket)
                
                # If no more connections for this user, cleanup
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
                    await self._unsubscribe_from_user_channel(user_id)
                    
                    # Clear typing indicators for this user
                    if user_id in self.typing_indicators:
                        del self.typing_indicators[user_id]
            
            # Remove from connection mapping
            del self.connection_users[websocket]
            
            logger.info(f"User {user_id} disconnected from WebSocket")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send message to a specific WebSocket connection."""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Error sending message to WebSocket: {e}")
            # Connection might be closed, remove it
            await self.disconnect(websocket)
    
    async def send_message_to_user(self, message: dict, user_id: int):
        """Send message to all connections of a specific user."""
        if user_id in self.active_connections:
            # Send to all user's connections
            connections_to_remove = []
            
            for websocket in self.active_connections[user_id]:
                try:
                    await websocket.send_text(json.dumps(message))
                except Exception as e:
                    logger.error(f"Error sending message to user {user_id}: {e}")
                    connections_to_remove.append(websocket)
            
            # Remove failed connections
            for websocket in connections_to_remove:
                await self.disconnect(websocket)
    
    async def broadcast_message(self, message: dict, sender_id: int, receiver_id: int):
        """Broadcast message to both sender and receiver."""
        # Send to receiver
        await self.send_message_to_user(message, receiver_id)
        
        # Send confirmation to sender
        sender_message = message.copy()
        sender_message["type"] = "message_sent"
        await self.send_message_to_user(sender_message, sender_id)
    
    async def handle_typing_indicator(self, user_id: int, target_user_id: int, is_typing: bool):
        """Handle typing indicator updates."""
        if is_typing:
            # Add typing indicator
            if user_id not in self.typing_indicators:
                self.typing_indicators[user_id] = set()
            self.typing_indicators[user_id].add(target_user_id)
        else:
            # Remove typing indicator
            if user_id in self.typing_indicators:
                self.typing_indicators[user_id].discard(target_user_id)
                if not self.typing_indicators[user_id]:
                    del self.typing_indicators[user_id]
        
        # Send typing indicator to target user
        typing_message = {
            "type": "typing_indicator",
            "data": {
                "user_id": user_id,
                "is_typing": is_typing,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        await self.send_message_to_user(typing_message, target_user_id)
    
    async def handle_read_receipt(self, user_id: int, message_id: int, sender_id: int):
        """Handle read receipt notifications."""
        read_receipt = {
            "type": "read_receipt",
            "data": {
                "message_id": message_id,
                "read_by": user_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        # Send read receipt to original sender
        await self.send_message_to_user(read_receipt, sender_id)
    
    async def get_online_users(self) -> List[int]:
        """Get list of currently online user IDs."""
        return list(self.active_connections.keys())
    
    async def is_user_online(self, user_id: int) -> bool:
        """Check if a user is currently online."""
        return user_id in self.active_connections
    
    async def get_user_connection_count(self, user_id: int) -> int:
        """Get number of active connections for a user."""
        return len(self.active_connections.get(user_id, []))
    
    async def _subscribe_to_user_channel(self, user_id: int):
        """Subscribe to Redis Pub/Sub channel for user."""
        channel = f"chat:{user_id}"
        
        async def message_handler(channel: str, message: dict):
            """Handle incoming Redis Pub/Sub messages."""
            try:
                # Forward message to user's WebSocket connections
                await self.send_message_to_user(message, user_id)
            except Exception as e:
                logger.error(f"Error handling Redis message for user {user_id}: {e}")
        
        await redis_pubsub.subscribe(channel, message_handler)
    
    async def _unsubscribe_from_user_channel(self, user_id: int):
        """Unsubscribe from Redis Pub/Sub channel for user."""
        channel = f"chat:{user_id}"
        await redis_pubsub.unsubscribe(channel)
    
    async def publish_message_to_redis(self, message: dict, receiver_id: int):
        """Publish message to Redis Pub/Sub for scalability."""
        channel = f"chat:{receiver_id}"
        await redis_pubsub.publish(channel, message)


class ChatWebSocketHandler:
    """Handles WebSocket chat operations and message processing."""
    
    def __init__(self, connection_manager: ConnectionManager):
        self.connection_manager = connection_manager
    
    async def handle_message(self, websocket: WebSocket, user: User, data: dict, db: Session):
        """Process incoming WebSocket message."""
        message_type = data.get("type")
        message_data = data.get("data", {})
        
        try:
            if message_type == "send_message":
                await self._handle_send_message(websocket, user, message_data, db)
            elif message_type == "typing_indicator":
                await self._handle_typing_indicator(user, message_data)
            elif message_type == "mark_read":
                await self._handle_mark_read(user, message_data, db)
            elif message_type == "get_online_status":
                await self._handle_online_status(websocket, message_data)
            else:
                await self.connection_manager.send_personal_message({
                    "type": "error",
                    "data": {
                        "message": f"Unknown message type: {message_type}",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }, websocket)
        
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
            await self.connection_manager.send_personal_message({
                "type": "error",
                "data": {
                    "message": "Failed to process message",
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
            }, websocket)
    
    async def _handle_send_message(self, websocket: WebSocket, user: User, data: dict, db: Session):
        """Handle sending a chat message via WebSocket."""
        receiver_id = data.get("receiver_id")
        content = data.get("content")
        
        if not receiver_id or not content:
            await self.connection_manager.send_personal_message({
                "type": "error",
                "data": {
                    "message": "receiver_id and content are required",
                    "timestamp": datetime.utcnow().isoformat()
                }
            }, websocket)
            return
        
        # Validate receiver exists
        receiver = db.query(User).filter(
            User.id == receiver_id,
            User.is_active == True,
            User.is_verified == True
        ).first()
        
        if not receiver:
            await self.connection_manager.send_personal_message({
                "type": "error",
                "data": {
                    "message": "Receiver not found or inactive",
                    "timestamp": datetime.utcnow().isoformat()
                }
            }, websocket)
            return
        
        # Create message in database
        try:
            new_message = ChatMessage(
                sender_id=user.id,
                receiver_id=receiver_id,
                content=content.strip(),
                is_read=False
            )
            
            db.add(new_message)
            db.commit()
            db.refresh(new_message)
            
            # Load relationships
            db.refresh(new_message, ['sender', 'receiver'])
            
            # Create message response
            message_response = {
                "type": "new_message",
                "data": {
                    "id": new_message.id,
                    "sender_id": new_message.sender_id,
                    "receiver_id": new_message.receiver_id,
                    "content": new_message.content,
                    "timestamp": new_message.timestamp.isoformat(),
                    "is_read": new_message.is_read,
                    "sender_username": new_message.sender.username,
                    "receiver_username": new_message.receiver.username
                }
            }
            
            # Broadcast message to both users
            await self.connection_manager.broadcast_message(
                message_response, user.id, receiver_id
            )
            
            # Also publish to Redis for scalability across multiple server instances
            await self.connection_manager.publish_message_to_redis(
                message_response, receiver_id
            )
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error saving message to database: {e}")
            await self.connection_manager.send_personal_message({
                "type": "error",
                "data": {
                    "message": "Failed to send message",
                    "timestamp": datetime.utcnow().isoformat()
                }
            }, websocket)
    
    async def _handle_typing_indicator(self, user: User, data: dict):
        """Handle typing indicator updates."""
        target_user_id = data.get("target_user_id")
        is_typing = data.get("is_typing", False)
        
        if target_user_id:
            await self.connection_manager.handle_typing_indicator(
                user.id, target_user_id, is_typing
            )
    
    async def _handle_mark_read(self, user: User, data: dict, db: Session):
        """Handle marking messages as read."""
        message_id = data.get("message_id")
        
        if not message_id:
            return
        
        try:
            # Find the message and mark as read
            message = db.query(ChatMessage).filter(
                ChatMessage.id == message_id,
                ChatMessage.receiver_id == user.id,
                ChatMessage.is_read == False
            ).first()
            
            if message:
                message.is_read = True
                db.commit()
                
                # Send read receipt to sender
                await self.connection_manager.handle_read_receipt(
                    user.id, message_id, message.sender_id
                )
        
        except Exception as e:
            db.rollback()
            logger.error(f"Error marking message as read: {e}")
    
    async def _handle_online_status(self, websocket: WebSocket, data: dict):
        """Handle online status requests."""
        user_ids = data.get("user_ids", [])
        
        online_status = {}
        for user_id in user_ids:
            online_status[user_id] = await self.connection_manager.is_user_online(user_id)
        
        await self.connection_manager.send_personal_message({
            "type": "online_status",
            "data": {
                "online_status": online_status,
                "timestamp": datetime.utcnow().isoformat()
            }
        }, websocket)


# Global connection manager instance
connection_manager = ConnectionManager()
chat_handler = ChatWebSocketHandler(connection_manager)