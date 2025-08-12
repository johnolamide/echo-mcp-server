"""
Chat router for message sending and chat history functionality.
"""
import json
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, WebSocket, WebSocketDisconnect
from sqlmodel import Session, select, and_, or_, desc, func

from app.db.database import get_db
from app.models.chat import ChatMessage
from app.models.user import User
from app.schemas.chat import (
    MessageSend, MessageResponse, ChatHistory, MessageMarkRead, 
    MessageMarkReadResponse, ConversationList, OnlineStatusResponse,
    UserStatusResponse
)
from app.routers.auth import get_current_user
from app.utils.websocket_manager import connection_manager, chat_handler
from app.utils.jwt_handler import verify_token

router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger(__name__)


@router.post("/send", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    message_data: MessageSend,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Send a message to another user.
    
    - **receiver_id**: ID of the user to send the message to
    - **content**: Message content (1-2000 characters)
    
    Returns the created message with sender and receiver information.
    """
    # Validate that user is not sending message to themselves
    if message_data.receiver_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot send message to yourself"
        )
    
    # Check if receiver exists and is active
    receiver = db.exec(select(User).where(
        User.id == message_data.receiver_id,
        User.is_active == True,
        User.is_verified == True
    )).first()
    
    if not receiver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Receiver not found or inactive"
        )
    
    try:
        # Create new chat message
        new_message = ChatMessage(
            sender_id=current_user.id,
            receiver_id=message_data.receiver_id,
            content=message_data.content,
            is_read=False
        )
        
        db.add(new_message)
        db.commit()
        db.refresh(new_message)
        
        # Manually load sender and receiver for the response
        sender = db.get(User, new_message.sender_id)
        receiver = db.get(User, new_message.receiver_id)

        return MessageResponse(
            id=new_message.id,
            sender_id=new_message.sender_id,
            receiver_id=new_message.receiver_id,
            content=new_message.content,
            timestamp=new_message.timestamp,
            is_read=new_message.is_read,
            sender_username=sender.username if sender else "Unknown",
            receiver_username=receiver.username if receiver else "Unknown"
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to send message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send message"
        )


@router.get("/history/{other_user_id}", response_model=ChatHistory)
async def get_chat_history(
    other_user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=100, description="Number of messages to retrieve"),
    offset: int = Query(0, ge=0, description="Number of messages to skip")
):
    """
    Get chat history with another user.
    
    - **other_user_id**: ID of the other user in the conversation
    - **limit**: Max number of messages to return
    - **offset**: Number of messages to skip for pagination
    
    Returns paginated chat history.
    """
    # Check if the other user exists
    other_user = db.get(User, other_user_id)
    if not other_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
        
    # Query for messages between the two users
    messages_query = select(ChatMessage).where(
        or_(
            and_(ChatMessage.sender_id == current_user.id, ChatMessage.receiver_id == other_user_id),
            and_(ChatMessage.sender_id == other_user_id, ChatMessage.receiver_id == current_user.id)
        )
    ).order_by(desc(ChatMessage.timestamp)).offset(offset).limit(limit)
    
    messages = db.exec(messages_query).all()
    
    # Get total count for pagination
    total_count_query = select(func.count(ChatMessage.id)).where(
        or_(
            and_(ChatMessage.sender_id == current_user.id, ChatMessage.receiver_id == other_user_id),
            and_(ChatMessage.sender_id == other_user_id, ChatMessage.receiver_id == current_user.id)
        )
    )
    total_count = db.exec(total_count_query).one()
    
    # Format messages for response
    formatted_messages = []
    for msg in messages:
        sender = db.get(User, msg.sender_id)
        receiver = db.get(User, msg.receiver_id)
        formatted_messages.append(
            MessageResponse(
                id=msg.id,
                sender_id=msg.sender_id,
                receiver_id=msg.receiver_id,
                content=msg.content,
                timestamp=msg.timestamp,
                is_read=msg.is_read,
                sender_username=sender.username if sender else "Unknown",
                receiver_username=receiver.username if receiver else "Unknown"
            )
        )
    
    return ChatHistory(
        messages=formatted_messages,
        total=total_count,
        limit=limit,
        offset=offset
    )


@router.post("/mark-read", response_model=MessageMarkReadResponse)
async def mark_messages_as_read(
    read_data: MessageMarkRead,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Mark messages from a specific user as read.
    
    - **sender_id**: ID of the user whose messages should be marked as read
    """
    # Update messages
    statement = select(ChatMessage).where(
        ChatMessage.receiver_id == current_user.id,
        ChatMessage.sender_id == read_data.sender_id,
        ChatMessage.is_read == False
    )
    messages_to_update = db.exec(statement).all()

    if not messages_to_update:
        return MessageMarkReadResponse(
            message="No unread messages from this user.",
            updated_count=0
        )
        
    updated_count = 0
    for message in messages_to_update:
        message.is_read = True
        db.add(message)
        updated_count += 1
        
    db.commit()
    
    return MessageMarkReadResponse(
        message=f"Successfully marked {updated_count} messages as read.",
        updated_count=updated_count
    )


@router.get("/conversations", response_model=ConversationList)
async def get_user_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a list of all conversations for the current user.
    
    A conversation is defined as a unique user with whom messages have been exchanged.
    """
    # Subquery to get the latest message for each conversation partner
    subquery = select(
        ChatMessage.sender_id,
        ChatMessage.receiver_id,
        func.max(ChatMessage.timestamp).label("last_timestamp")
    ).where(
        or_(
            ChatMessage.sender_id == current_user.id,
            ChatMessage.receiver_id == current_user.id
        )
    ).group_by(ChatMessage.sender_id, ChatMessage.receiver_id).alias("sub")

    # Get the actual latest message for each conversation
    latest_messages_query = select(ChatMessage).join(
        subquery,
        and_(
            or_(
                and_(ChatMessage.sender_id == subquery.c.sender_id, ChatMessage.receiver_id == subquery.c.receiver_id),
                and_(ChatMessage.sender_id == subquery.c.receiver_id, ChatMessage.receiver_id == subquery.c.sender_id)
            ),
            ChatMessage.timestamp == subquery.c.last_timestamp
        )
    )
    
    latest_messages = db.exec(latest_messages_query).all()
    
    # Process messages to create conversation list
    conversations = {}
    for msg in latest_messages:
        other_user_id = msg.sender_id if msg.receiver_id == current_user.id else msg.receiver_id
        
        if other_user_id not in conversations or msg.timestamp > conversations[other_user_id]['last_message']['timestamp']:
            other_user = db.get(User, other_user_id)
            unread_count = db.exec(select(func.count(ChatMessage.id)).where(
                ChatMessage.sender_id == other_user_id,
                ChatMessage.receiver_id == current_user.id,
                ChatMessage.is_read == False
            )).one()
            
            conversations[other_user_id] = {
                "other_user": {
                    "id": other_user.id,
                    "username": other_user.username,
                    "is_active": other_user.is_active
                },
                "last_message": {
                    "content": msg.content,
                    "timestamp": msg.timestamp,
                    "is_read": msg.is_read
                },
                "unread_count": unread_count
            }
            
    return ConversationList(conversations=list(conversations.values()))


@router.get("/status/{user_id}", response_model=UserStatusResponse)
async def get_user_online_status(
    user_id: int,
    current_user: User = Depends(get_current_user)
):
    """
    Check if a user is currently online (connected via WebSocket).
    """
    is_online = await connection_manager.is_user_online(user_id)
    return UserStatusResponse(user_id=user_id, is_online=is_online)


@router.get("/online-users", response_model=OnlineStatusResponse)
async def get_all_online_users(
    current_user: User = Depends(get_current_user)
):
    """
    Get a list of all currently online users.
    """
    online_user_ids = await connection_manager.get_online_user_ids()
    return OnlineStatusResponse(online_users=online_user_ids)


@router.websocket("/ws/{token}")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str,
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for real-time chat.
    
    - Authenticates user via JWT token in the URL.
    - Handles incoming and outgoing messages.
    - Manages user online status.
    """
    try:
        payload = await verify_token(token, "access")
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
            
        user = db.get(User, user_id)
        if not user or not user.is_active:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
            
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await connection_manager.connect(websocket, user.id)
    
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message_data = json.loads(data)
                await chat_handler.handle_message(websocket, message_data, user, db)
            except json.JSONDecodeError:
                await connection_manager.send_personal_message(
                    {"error": "Invalid JSON format"}, user.id
                )
            except Exception as e:
                logger.error(f"Error handling message for user {user.id}: {e}")
                await connection_manager.send_personal_message(
                    {"error": "Failed to process message"}, user.id
                )
                
    except WebSocketDisconnect:
        logger.info(f"User {user.id} disconnected.")
    except Exception as e:
        logger.error(f"Unexpected error in WebSocket for user {user.id}: {e}")
    finally:
        await connection_manager.disconnect(user.id)
        logger.info(f"User {user.id} connection closed and cleaned up.")

import json
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, WebSocket, WebSocketDisconnect
from sqlmodel import Session, select
from sqlalchemy import and_, or_, desc

from app.db.database import get_db
from app.models.chat import ChatMessage
from app.models.user import User
from app.schemas.chat import (
    MessageSend, MessageResponse, ChatHistory, MessageMarkRead, 
    MessageMarkReadResponse, ConversationList, OnlineStatusResponse,
    UserStatusResponse
)
from app.routers.auth import get_current_user
from app.utils.websocket_manager import connection_manager, chat_handler
from app.utils.jwt_handler import verify_token

router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger(__name__)


@router.post("/send", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    message_data: MessageSend,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Send a message to another user.
    
    - **receiver_id**: ID of the user to send the message to
    - **content**: Message content (1-2000 characters)
    
    Returns the created message with sender and receiver information.
    """
    # Validate that user is not sending message to themselves
    if message_data.receiver_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot send message to yourself"
        )
    
    # Check if receiver exists and is active
    receiver = db.query(User).filter(
        User.id == message_data.receiver_id,
        User.is_active == True,
        User.is_verified == True
    ).first()
    
    if not receiver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Receiver not found or inactive"
        )
    
    try:
        # Create new chat message
        new_message = ChatMessage(
            sender_id=current_user.id,
            receiver_id=message_data.receiver_id,
            content=message_data.content,
            is_read=False
        )
        
        db.add(new_message)
        db.commit()
        db.refresh(new_message)
        
        # Load relationships for response
        db.refresh(new_message, ['sender', 'receiver'])
        
        return MessageResponse(
            id=new_message.id,
            sender_id=new_message.sender_id,
            receiver_id=new_message.receiver_id,
            content=new_message.content,
            timestamp=new_message.timestamp,
            is_read=new_message.is_read,
            sender_username=new_message.sender.username,
            receiver_username=new_message.receiver.username
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send message"
        )


@router.get("/history/{other_user_id}", response_model=ChatHistory)
async def get_chat_history(
    other_user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of messages to return"),
    offset: int = Query(0, ge=0, description="Number of messages to skip"),
    mark_as_read: bool = Query(True, description="Whether to mark messages as read")
):
    """
    Get chat history with another user.
    
    - **other_user_id**: ID of the other user in the conversation
    - **limit**: Maximum number of messages to return (1-200, default 50)
    - **offset**: Number of messages to skip for pagination (default 0)
    - **mark_as_read**: Whether to mark received messages as read (default true)
    
    Returns messages in descending order by timestamp (newest first).
    """
    # Validate that user is not requesting chat with themselves
    if other_user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot get chat history with yourself"
        )
    
    # Check if other user exists and is active
    other_user = db.query(User).filter(
        User.id == other_user_id,
        User.is_active == True,
        User.is_verified == True
    ).first()
    
    if not other_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found or inactive"
        )
    
    try:
        # Query messages between current user and other user
        messages_query = db.query(ChatMessage).filter(
            or_(
                and_(
                    ChatMessage.sender_id == current_user.id,
                    ChatMessage.receiver_id == other_user_id
                ),
                and_(
                    ChatMessage.sender_id == other_user_id,
                    ChatMessage.receiver_id == current_user.id
                )
            )
        ).order_by(desc(ChatMessage.timestamp))
        
        # Get total count for pagination
        total_messages = messages_query.count()
        
        # Apply pagination
        messages = messages_query.offset(offset).limit(limit).all()
        
        # Count unread messages for current user
        unread_count = db.query(ChatMessage).filter(
            ChatMessage.sender_id == other_user_id,
            ChatMessage.receiver_id == current_user.id,
            ChatMessage.is_read == False
        ).count()
        
        # Mark messages as read if requested
        if mark_as_read and unread_count > 0:
            db.query(ChatMessage).filter(
                ChatMessage.sender_id == other_user_id,
                ChatMessage.receiver_id == current_user.id,
                ChatMessage.is_read == False
            ).update({"is_read": True})
            db.commit()
            unread_count = 0  # Reset count since we just marked them as read
        
        # Convert messages to response format
        message_responses = []
        for message in messages:
            # Load relationships if not already loaded
            if not message.sender:
                db.refresh(message, ['sender', 'receiver'])
            
            message_responses.append(MessageResponse(
                id=message.id,
                sender_id=message.sender_id,
                receiver_id=message.receiver_id,
                content=message.content,
                timestamp=message.timestamp,
                is_read=message.is_read,
                sender_username=message.sender.username,
                receiver_username=message.receiver.username
            ))
        
        return ChatHistory(
            messages=message_responses,
            total_messages=total_messages,
            unread_count=unread_count,
            other_user_id=other_user_id,
            other_username=other_user.username
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chat history"
        )


@router.post("/mark-read", response_model=MessageMarkReadResponse)
async def mark_messages_as_read(
    mark_data: MessageMarkRead,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Mark specific messages as read.
    
    - **message_ids**: List of message IDs to mark as read (max 100)
    
    Only messages received by the current user can be marked as read.
    """
    try:
        # Query messages that belong to current user as receiver and are unread
        messages_to_mark = db.query(ChatMessage).filter(
            ChatMessage.id.in_(mark_data.message_ids),
            ChatMessage.receiver_id == current_user.id,
            ChatMessage.is_read == False
        ).all()
        
        if not messages_to_mark:
            return MessageMarkReadResponse(
                marked_count=0,
                message="No unread messages found to mark as read"
            )
        
        # Mark messages as read
        marked_count = 0
        for message in messages_to_mark:
            message.is_read = True
            marked_count += 1
        
        db.commit()
        
        return MessageMarkReadResponse(
            marked_count=marked_count,
            message=f"{marked_count} messages marked as read successfully"
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark messages as read"
        )


@router.get("/conversations", response_model=ConversationList)
async def get_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of conversations to return")
):
    """
    Get list of conversations for the current user.
    
    - **limit**: Maximum number of conversations to return (1-100, default 20)
    
    Returns conversations ordered by most recent message.
    """
    try:
        # Get all users that current user has exchanged messages with
        # This is a complex query that gets the latest message for each conversation
        from sqlalchemy import func, case
        
        # Subquery to get the latest message for each conversation
        latest_messages = db.query(
            ChatMessage.id,
            case(
                (ChatMessage.sender_id == current_user.id, ChatMessage.receiver_id),
                else_=ChatMessage.sender_id
            ).label('other_user_id'),
            func.max(ChatMessage.timestamp).label('latest_timestamp')
        ).filter(
            or_(
                ChatMessage.sender_id == current_user.id,
                ChatMessage.receiver_id == current_user.id
            )
        ).group_by(
            case(
                (ChatMessage.sender_id == current_user.id, ChatMessage.receiver_id),
                else_=ChatMessage.sender_id
            )
        ).subquery()
        
        # Get the actual latest messages with full details
        conversations_query = db.query(
            ChatMessage,
            User.username.label('other_username')
        ).join(
            latest_messages,
            and_(
                ChatMessage.timestamp == latest_messages.c.latest_timestamp,
                or_(
                    and_(
                        ChatMessage.sender_id == current_user.id,
                        ChatMessage.receiver_id == latest_messages.c.other_user_id
                    ),
                    and_(
                        ChatMessage.receiver_id == current_user.id,
                        ChatMessage.sender_id == latest_messages.c.other_user_id
                    )
                )
            )
        ).join(
            User,
            User.id == latest_messages.c.other_user_id
        ).order_by(desc(ChatMessage.timestamp)).limit(limit)
        
        conversations_data = conversations_query.all()
        
        # Build conversation list
        conversations = []
        total_unread = 0
        
        for message, other_username in conversations_data:
            # Determine other user ID
            other_user_id = message.receiver_id if message.sender_id == current_user.id else message.sender_id
            
            # Count unread messages in this conversation
            unread_count = db.query(ChatMessage).filter(
                ChatMessage.sender_id == other_user_id,
                ChatMessage.receiver_id == current_user.id,
                ChatMessage.is_read == False
            ).count()
            
            total_unread += unread_count
            
            # Count total messages in conversation
            total_messages_count = db.query(ChatMessage).filter(
                or_(
                    and_(
                        ChatMessage.sender_id == current_user.id,
                        ChatMessage.receiver_id == other_user_id
                    ),
                    and_(
                        ChatMessage.sender_id == other_user_id,
                        ChatMessage.receiver_id == current_user.id
                    )
                )
            ).count()
            
            conversations.append({
                "other_user_id": other_user_id,
                "other_username": other_username,
                "last_message": {
                    "content": message.content,
                    "timestamp": message.timestamp.isoformat(),
                    "is_from_me": message.sender_id == current_user.id
                },
                "unread_count": unread_count,
                "total_messages": total_messages_count
            })
        
        return ConversationList(
            conversations=conversations,
            total_conversations=len(conversations),
            total_unread=total_unread
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve conversations"
        )


@router.get("/unread-count")
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get total count of unread messages for the current user.
    
    Returns total number of unread messages across all conversations.
    """
    try:
        unread_count = db.query(ChatMessage).filter(
            ChatMessage.receiver_id == current_user.id,
            ChatMessage.is_read == False
        ).count()
        
        return {
            "unread_count": unread_count,
            "user_id": current_user.id
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get unread count"
        )


@router.websocket("/ws/{user_id}")
async def websocket_chat_endpoint(websocket: WebSocket, user_id: int, token: str):
    """
    WebSocket endpoint for real-time chat functionality.
    
    - **user_id**: ID of the user connecting to chat
    - **token**: JWT authentication token (passed as query parameter)
    
    Supports real-time messaging, typing indicators, read receipts, and online status.
    """
    # Create database session for WebSocket connection
    from app.db.database import SessionLocal
    db = SessionLocal()
    
    try:
        # Verify JWT token
        payload = verify_token(token)
        if not payload or payload.get("user_id") != user_id:
            await websocket.close(code=4001, reason="Invalid authentication token")
            return
        
        # Get user from database
        user = db.query(User).filter(
            User.id == user_id,
            User.is_active == True,
            User.is_verified == True
        ).first()
        
        if not user:
            await websocket.close(code=4004, reason="User not found or inactive")
            return
        
        # Connect user to WebSocket manager
        await connection_manager.connect(websocket, user_id)
        
        try:
            while True:
                # Receive message from WebSocket
                data = await websocket.receive_text()
                
                try:
                    # Parse JSON message
                    message_data = json.loads(data)
                    
                    # Create new DB session for each message to avoid stale connections
                    message_db = SessionLocal()
                    try:
                        # Refresh user object in new session
                        message_user = message_db.query(User).filter(User.id == user_id).first()
                        if message_user:
                            await chat_handler.handle_message(websocket, message_user, message_data, message_db)
                    finally:
                        message_db.close()
                    
                except json.JSONDecodeError:
                    from datetime import datetime
                    await connection_manager.send_personal_message({
                        "type": "error",
                        "data": {
                            "message": "Invalid JSON format",
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    }, websocket)
                
                except Exception as e:
                    from datetime import datetime
                    logger.error(f"Error processing WebSocket message: {e}")
                    await connection_manager.send_personal_message({
                        "type": "error",
                        "data": {
                            "message": "Error processing message",
                            "error": str(e),
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    }, websocket)
        
        except WebSocketDisconnect:
            logger.info(f"User {user_id} disconnected from WebSocket")
        
        except Exception as e:
            logger.error(f"WebSocket error for user {user_id}: {e}")
        
        finally:
            # Cleanup connection
            await connection_manager.disconnect(websocket)
    
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
        try:
            await websocket.close(code=4000, reason="Connection error")
        except:
            pass
    
    finally:
        db.close()


@router.get("/online-users", response_model=OnlineStatusResponse)
async def get_online_users(
    current_user: User = Depends(get_current_user)
):
    """
    Get list of currently online users.
    
    Returns list of user IDs that are currently connected via WebSocket.
    """
    try:
        online_users = await connection_manager.get_online_users()
        return OnlineStatusResponse(
            online_users=online_users,
            total_online=len(online_users),
            requesting_user=current_user.id
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get online users"
        )


@router.get("/user-status/{user_id}", response_model=UserStatusResponse)
async def get_user_online_status(
    user_id: int,
    current_user: User = Depends(get_current_user)
):
    """
    Check if a specific user is currently online.
    
    - **user_id**: ID of the user to check
    
    Returns online status and connection count for the user.
    """
    try:
        is_online = await connection_manager.is_user_online(user_id)
        connection_count = await connection_manager.get_user_connection_count(user_id)
        
        return UserStatusResponse(
            user_id=user_id,
            is_online=is_online,
            connection_count=connection_count,
            checked_by=current_user.id
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check user status"
        )