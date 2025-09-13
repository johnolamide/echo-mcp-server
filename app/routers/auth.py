"""
Authentication router with simplified username-only registration and login.
"""
import logging
from datetime import timedelta
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.db.database import get_db
from app.models.user import User, UserCreate
from app.schemas.auth import (
    UserRegistration, UserLogin, UserResponse, TokenResponse,
    TokenRefresh, TokenRefreshResponse, AdminUserRegistration, AdminUserResponse
)
from app.utils.jwt_handler import jwt_handler
from app.utils import success_response, error_response

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Dependency to get current authenticated user."""
    token = credentials.credentials
    payload = await jwt_handler.verify_token(token, "access")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )

    user = db.exec(select(User).where(User.id == user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive"
        )

    return user


@router.post("/register", response_model=Dict[str, str], status_code=status.HTTP_201_CREATED, operation_id="register_user")
async def register_user(
    user_data: UserRegistration,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Register a new user with username only.

    - **username**: Unique username (3-50 characters, alphanumeric, underscore, hyphen)

    Creates a user account that can immediately access the application.
    """
    try:
        # Check if username already exists
        existing_user = db.exec(select(User).where(User.username == user_data.username.lower())).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already registered"
            )

        # Create new user
        new_user = User(
            username=user_data.username.lower(),
            is_active=True
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        return success_response(
            message="User registered successfully",
            data={"user_id": new_user.id, "username": new_user.username}
        )

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists."
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {e}"
        )


@router.post("/register-admin", status_code=status.HTTP_201_CREATED, operation_id="register_admin")
async def register_admin_user(
    admin_data: AdminUserRegistration,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Register a new admin user with admin secret key.

    - **username**: Unique username (3-50 characters, alphanumeric, underscore, hyphen)
    - **admin_secret**: Admin creation secret key

    Creates an admin user with elevated privileges.
    """
    from app.core.config import settings

    try:
        # Verify admin secret
        if admin_data.admin_secret != settings.admin_secret_key:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid admin secret key"
            )

        # Check if username already exists
        existing_user = db.exec(select(User).where(User.username == admin_data.username.lower())).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already registered"
            )

        # Create new admin user
        new_admin = User(
            username=admin_data.username.lower(),
            is_active=True,
            is_admin=True
        )

        db.add(new_admin)
        db.commit()
        db.refresh(new_admin)

        return {
            "message": "Admin user created successfully",
            "user_id": str(new_admin.id),
            "username": new_admin.username,
            "is_admin": True
        }

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists."
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {e}"
        )


@router.post("/login", response_model=TokenResponse, operation_id="login")
async def login_user(
    user_data: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Authenticate user and return access and refresh tokens.

    - **username**: Registered username
    """
    user = db.exec(select(User).where(User.username == user_data.username.lower())).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username not found"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive. Please contact support."
        )

    # Generate tokens
    access_token = jwt_handler.create_access_token(
        {"sub": str(user.id), "is_admin": user.is_admin}, timedelta(minutes=settings.jwt_access_token_expire_minutes)
    )
    refresh_token = jwt_handler.create_refresh_token(
        {"sub": str(user.id), "is_admin": user.is_admin }
    )

    user_data = UserResponse.from_orm(user).dict()
    # Convert datetime fields to ISO format strings
    if user_data.get('created_at'):
        user_data['created_at'] = user_data['created_at'].isoformat()
    if user_data.get('updated_at'):
        user_data['updated_at'] = user_data['updated_at'].isoformat()

    return success_response(
        message="Login successful",
        data={
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.jwt_access_token_expire_minutes * 60,
            "user": user_data
        }
    )


@router.post("/refresh", response_model=TokenRefreshResponse, operation_id="refresh_token")
async def refresh_access_token(
    refresh_data: TokenRefresh,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using a valid refresh token.
    """
    payload = await jwt_handler.verify_token(refresh_data.refresh_token, "refresh")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    user = db.exec(select(User).where(User.id == user_id)).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )

    # Generate new access token
    new_access_token = jwt_handler.create_access_token(
        {"sub": str(user.id), "is_admin": user.is_admin}, timedelta(minutes=settings.jwt_access_token_expire_minutes)
    )

    return success_response(
        message="Token refreshed successfully",
        data={"access_token": new_access_token, "token_type": "bearer"}
    )