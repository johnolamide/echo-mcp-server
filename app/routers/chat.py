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
    MessageMarkReadBySender, MessageMarkReadResponse, ConversationList, OnlineStatusResponse,
    UserStatusResponse, UserBasicInfo, UsersListResponse
)
from app.routers.auth import get_current_user
from app.utils.websocket_manager import connection_manager, chat_handler
from app.utils.jwt_handler import verify_token
from app.utils import success_response, error_response

router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger(__name__)


@router.post("/send", response_model=MessageResponse, status_code=status.HTTP_201_CREATED, operation_id="send_message")
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
    # Allow sending messages to yourself for testing purposes
    # if message_data.receiver_id == current_user.id:
    #     raise HTTPException(
    #         status_code=status.HTTP_400_BAD_REQUEST,
    #         detail="Cannot send message to yourself"
    #     )
    
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

        return success_response(
            message="Message sent successfully",
            data=MessageResponse(
                id=new_message.id,
                sender_id=new_message.sender_id,
                receiver_id=new_message.receiver_id,
                content=new_message.content,
                timestamp=new_message.timestamp.isoformat(),
                is_read=new_message.is_read,
                sender_username=sender.username if sender else "Unknown",
                receiver_username=receiver.username if receiver else "Unknown"
            ).dict()
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to send message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send message"
        )


@router.get("/history/{other_user_id}", response_model=ChatHistory, operation_id="get_chat_history")
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
    
    # Count unread messages from the other user to current user
    unread_count_query = select(func.count(ChatMessage.id)).where(
        ChatMessage.sender_id == other_user_id,
        ChatMessage.receiver_id == current_user.id,
        ChatMessage.is_read == False
    )
    unread_count = db.exec(unread_count_query).one()
    
    return success_response(
        message="Chat history retrieved successfully",
        data=ChatHistory(
            messages=formatted_messages,
            total_messages=total_count,
            unread_count=unread_count,
            other_user_id=other_user_id,
            other_username=other_user.username
        )
    )


@router.post("/mark-read", response_model=MessageMarkReadResponse, operation_id="mark_messages_as_read")
async def mark_messages_as_read(
    read_data: MessageMarkReadBySender,
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
        return success_response(
            message="No unread messages from this user",
            data=MessageMarkReadResponse(
                message="No unread messages from this user.",
                marked_count=0
            ).dict()
        )
        
    updated_count = 0
    for message in messages_to_update:
        message.is_read = True
        db.add(message)
        updated_count += 1
        
    db.commit()
    
    return success_response(
        message=f"Successfully marked {updated_count} messages as read",
        data=MessageMarkReadResponse(
            message=f"Successfully marked {updated_count} messages as read.",
            marked_count=updated_count
        ).dict()
    )


@router.get("/conversations", response_model=ConversationList, operation_id="get_user_conversations")
async def get_user_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of conversations to return")
):
    """
    Get a list of all conversations for the current user.
    
    A conversation is defined as a unique user with whom messages have been exchanged.
    """
    # Get all messages involving the current user, ordered by timestamp desc
    all_messages = db.exec(select(ChatMessage).where(
        or_(
            ChatMessage.sender_id == current_user.id,
            ChatMessage.receiver_id == current_user.id
        )
    ).order_by(ChatMessage.timestamp.desc())).all()
    
    # Build conversations dictionary
    conversations_dict = {}
    total_unread = 0
    
    for msg in all_messages:
        # Determine the other user in the conversation
        other_user_id = msg.receiver_id if msg.sender_id == current_user.id else msg.sender_id
        
        # Skip if we already have this conversation (we want the latest message)
        if other_user_id in conversations_dict:
            continue
            
        # Get the other user details
        other_user = db.get(User, other_user_id)
        if not other_user:
            continue
            
        # Count unread messages from this user
        unread_count = db.exec(select(func.count(ChatMessage.id)).where(
            ChatMessage.sender_id == other_user_id,
            ChatMessage.receiver_id == current_user.id,
            ChatMessage.is_read == False
        )).one()
        
        total_unread += unread_count
        
        # Count total messages in this conversation
        total_messages = db.exec(select(func.count(ChatMessage.id)).where(
            or_(
                and_(ChatMessage.sender_id == current_user.id, ChatMessage.receiver_id == other_user_id),
                and_(ChatMessage.sender_id == other_user_id, ChatMessage.receiver_id == current_user.id)
            )
        )).one()
        
        conversations_dict[other_user_id] = {
            "other_user_id": other_user_id,
            "other_username": other_user.username,
            "last_message": {
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
                "is_from_me": msg.sender_id == current_user.id
            },
            "unread_count": unread_count,
            "total_messages": total_messages
        }
        
        # Limit the number of conversations
        if len(conversations_dict) >= limit:
            break
    
    conversations_list = list(conversations_dict.values())
    
    return success_response(
        message="Conversations retrieved successfully",
        data=ConversationList(
            conversations=conversations_list,
            total_conversations=len(conversations_list),
            total_unread=total_unread
        ).dict()
    )


@router.get("/status/{user_id}", response_model=UserStatusResponse, operation_id="get_user_online_status")
async def get_user_online_status(
    user_id: int,
    current_user: User = Depends(get_current_user)
):
    """
    Check if a user is currently online (connected via WebSocket).
    """
    is_online = await connection_manager.is_user_online(user_id)
    return success_response(
        message="User online status retrieved successfully",
        data=UserStatusResponse(user_id=user_id, is_online=is_online).dict()
    )


@router.get("/online-users", response_model=OnlineStatusResponse, operation_id="get_all_online_users")
async def get_all_online_users(
    current_user: User = Depends(get_current_user)
):
    """
    Get a list of all currently online users.
    """
    online_user_ids = await connection_manager.get_online_users()
    return success_response(
        message="Online users retrieved successfully",
        data=OnlineStatusResponse(
            online_users=online_user_ids,
            total_online=len(online_user_ids),
            requesting_user=current_user.id
        ).dict()
    )


@router.get("/users", response_model=UsersListResponse, operation_id="get_chat_users")
async def get_chat_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a list of all active and verified users for chat purposes.
    
    This endpoint returns basic user information (ID, username, online status)
    for all active and verified users except the current user.
    """
    # Get all active and verified users except the current user
    users = db.exec(select(User).where(
        User.id != current_user.id,
        User.is_active == True,
        User.is_verified == True
    ).order_by(User.username)).all()
    
    # Get online user IDs
    online_user_ids = await connection_manager.get_online_users()
    online_user_ids_set = set(online_user_ids)
    
    # Build user list with online status
    users_list = []
    online_count = 0
    
    for user in users:
        is_online = user.id in online_user_ids_set
        if is_online:
            online_count += 1
            
        users_list.append(UserBasicInfo(
            id=user.id,
            username=user.username,
            is_online=is_online
        ))
    
    return success_response(
        message="Chat users retrieved successfully",
        data=UsersListResponse(
            users=users_list,
            total_users=len(users_list),
            online_count=online_count
        ).dict()
    )


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
        payload = verify_token(token)
        if not payload:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

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

