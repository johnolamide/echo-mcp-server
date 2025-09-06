"""
Admin router for user management endpoints.
Provides admin-only endpoints for user oversight and management.
"""
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, select, func
from sqlalchemy import or_

from app.db.database import get_db
from app.models.user import User
from app.models.chat import ChatMessage
from app.models.service import Service
from app.schemas.admin import UserListResponse, UserDetailResponse, UserStatsResponse
from app.schemas.auth import UserResponse
from app.core.security import require_admin
from app.utils import success_response, error_response

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=UserListResponse, operation_id="get_all_users")
async def get_all_users(
    active_only: bool = Query(False, description="Filter to show only active users"),
    verified_only: bool = Query(False, description="Filter to show only verified users"),
    admin_only: bool = Query(False, description="Filter to show only admin users"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of users to return"),
    offset: int = Query(0, ge=0, description="Number of users to skip"),
    search: Optional[str] = Query(None, description="Search query for username or email"),
    db: Session = Depends(get_db),
    current_user_token: dict = Depends(require_admin)
):
    """
    Get all users with admin role validation.
    
    Requirements: 6.1 - Admin can request all users and get list with basic information
    """
    # Build query
    query = select(User)
    
    # Apply filters
    if active_only:
        query = query.where(User.is_active == True)
    
    if verified_only:
        query = query.where(User.is_verified == True)
    
    if admin_only:
        query = query.where(User.is_admin == True)
    
    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                User.username.ilike(search_term),
                User.email.ilike(search_term)
            )
        )
    
    # Get total count before pagination
    total_count_statement = select(func.count()).select_from(query.alias("subquery"))
    total_count = db.exec(total_count_statement).one()
    
    # Get various counts for statistics
    active_count = db.exec(select(func.count(User.id)).where(User.is_active == True)).one()
    verified_count = db.exec(select(func.count(User.id)).where(User.is_verified == True)).one()
    admin_count = db.exec(select(func.count(User.id)).where(User.is_admin == True)).one()
    
    # Apply pagination and ordering
    users = db.exec(query.order_by(User.created_at.desc()).offset(offset).limit(limit)).all()
    
    return success_response(
        message="Users retrieved successfully",
        data=UserListResponse(
            users=users,
            total=total_count,
            active_count=active_count,
            verified_count=verified_count,
            admin_count=admin_count
        ).dict()
    )


@router.get("/users/{user_id}", response_model=UserDetailResponse, operation_id="get_user_details")
async def get_user_details(
    user_id: int,
    db: Session = Depends(get_db),
    current_user_token: dict = Depends(require_admin)
):
    """
    Get detailed information for a specific user with comprehensive information.
    
    Requirements: 6.2 - Admin can request details for specific user and get comprehensive information including activity history
    """
    # Get user
    user = db.get(User, user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get comprehensive user statistics
    total_messages_sent = db.exec(select(func.count(ChatMessage.id)).where(ChatMessage.sender_id == user_id)).one()
    total_messages_received = db.exec(select(func.count(ChatMessage.id)).where(ChatMessage.receiver_id == user_id)).one()
    services_created_count = db.exec(select(func.count(Service.id)).where(Service.created_by == user_id)).one()
    
    # For now, we don't have a last_login field in the User model
    # In a real implementation, you would track this in the authentication system
    last_login = None
    
    # Create detailed response
    user_detail = UserDetailResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        is_verified=user.is_verified,
        is_admin=user.is_admin,
        created_at=user.created_at,
        updated_at=user.updated_at,
        total_messages_sent=total_messages_sent,
        total_messages_received=total_messages_received,
        services_created=services_created_count,
        last_login=last_login
    )
    
    return success_response(
        message="User details retrieved successfully",
        data=user_detail
    )


@router.get("/users/stats/summary", response_model=UserStatsResponse, operation_id="get_user_statistics_summary")
async def get_user_statistics(
    db: Session = Depends(get_db),
    current_user_token: dict = Depends(require_admin)
):
    """
    Get user statistics summary (Admin only).
    
    Requirements: 6.3 - Admin can access user management with appropriate authorization
    """
    # Get various user statistics
    total_users = db.exec(select(func.count(User.id))).one()
    active_users = db.exec(select(func.count(User.id)).where(User.is_active == True)).one()
    verified_users = db.exec(select(func.count(User.id)).where(User.is_verified == True)).one()
    admin_users = db.exec(select(func.count(User.id)).where(User.is_admin == True)).one()
    
    # Get recent registrations (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_registrations = db.exec(
        select(func.count(User.id)).where(User.created_at >= thirty_days_ago)
    ).one()
    
    return success_response(
        message="User statistics retrieved successfully",
        data=UserStatsResponse(
            total_users=total_users,
            active_users=active_users,
            verified_users=verified_users,
            admin_users=admin_users,
            recent_registrations=recent_registrations
        ).dict()
    )


@router.get("/users/search/advanced", response_model=UserListResponse, operation_id="advanced_user_search")
async def advanced_user_search(
    query: Optional[str] = Query(None, description="Search query for username or email"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    is_verified: Optional[bool] = Query(None, description="Filter by verified status"),
    is_admin: Optional[bool] = Query(None, description="Filter by admin status"),
    created_after: Optional[datetime] = Query(None, description="Filter users created after this date"),
    created_before: Optional[datetime] = Query(None, description="Filter users created before this date"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db),
    current_user_token: dict = Depends(require_admin)
):
    """
    Advanced user search with multiple filters (Admin only).
    
    Requirements: 6.1, 6.2 - Enhanced admin user management capabilities
    """
    # Build query
    db_query = select(User)
    
    # Apply filters
    if query:
        search_term = f"%{query}%"
        db_query = db_query.where(
            or_(
                User.username.ilike(search_term),
                User.email.ilike(search_term)
            )
        )
    
    if is_active is not None:
        db_query = db_query.where(User.is_active == is_active)
    
    if is_verified is not None:
        db_query = db_query.where(User.is_verified == is_verified)
    
    if is_admin is not None:
        db_query = db_query.where(User.is_admin == is_admin)
    
    if created_after:
        db_query = db_query.where(User.created_at >= created_after)
    
    if created_before:
        db_query = db_query.where(User.created_at <= created_before)
    
    # Get total count before pagination
    total_count_statement = select(func.count()).select_from(db_query.alias("subquery"))
    total_count = db.exec(total_count_statement).one()
    
    # Get various counts for statistics
    active_count = db.exec(select(func.count(User.id)).where(User.is_active == True)).one()
    verified_count = db.exec(select(func.count(User.id)).where(User.is_verified == True)).one()
    admin_count = db.exec(select(func.count(User.id)).where(User.is_admin == True)).one()
    
    # Apply pagination and ordering
    users = db.exec(db_query.order_by(User.created_at.desc()).offset(offset).limit(limit)).all()
    
    return success_response(
        message="Advanced user search completed successfully",
        data=UserListResponse(
            users=users,
            total=total_count,
            active_count=active_count,
            verified_count=verified_count,
            admin_count=admin_count
        ).dict()
    )


@router.get("/users/{user_id}/activity", response_model=dict, operation_id="get_user_activity")
async def get_user_activity(
    user_id: int,
    days: int = Query(30, ge=1, le=365, description="Number of days to look back for activity"),
    db: Session = Depends(get_db),
    current_user_token: dict = Depends(require_admin)
):
    """
    Get detailed user activity information (Admin only).
    
    Requirements: 6.2 - Admin can get comprehensive user information including activity history
    """
    # Verify user exists
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Get activity statistics
    messages_sent_period = db.exec(select(func.count(ChatMessage.id)).where(
        ChatMessage.sender_id == user_id,
        ChatMessage.timestamp >= start_date,
        ChatMessage.timestamp <= end_date
    )).one()
    
    messages_received_period = db.exec(select(func.count(ChatMessage.id)).where(
        ChatMessage.receiver_id == user_id,
        ChatMessage.timestamp >= start_date,
        ChatMessage.timestamp <= end_date
    )).one()
    
    services_created_period = db.exec(select(func.count(Service.id)).where(
        Service.created_by == user_id,
        Service.created_at >= start_date,
        Service.created_at <= end_date
    )).one()
    
    # Get recent messages (last 10)
    recent_messages = db.exec(select(ChatMessage).where(
        ChatMessage.sender_id == user_id
    ).order_by(ChatMessage.timestamp.desc()).limit(10)).all()
    
    # Get created services
    created_services = db.exec(select(Service).where(
        Service.created_by == user_id
    ).order_by(Service.created_at.desc())).all()
    
    return success_response(
        message="User activity report generated successfully",
        data={
            "user_id": user_id,
            "username": user.username,
            "period_days": days,
            "activity_summary": {
                "messages_sent": messages_sent_period,
                "messages_received": messages_received_period,
                "services_created": services_created_period
            },
            "recent_messages": [
                {
                    "id": msg.id,
                    "receiver_id": msg.receiver_id,
                    "content": msg.content[:100] + "..." if len(msg.content) > 100 else msg.content,
                    "timestamp": msg.timestamp
                }
                for msg in recent_messages
            ],
            "created_services": [
                {
                    "id": service.id,
                    "name": service.name,
                    "description": service.description,
                    "is_active": service.is_active,
                    "created_at": service.created_at
                }
                for service in created_services
            ]
        }
    )