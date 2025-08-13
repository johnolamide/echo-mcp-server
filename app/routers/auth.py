"""
Authentication router with registration, login, token refresh, and email verification.
"""
import logging
from datetime import timedelta
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.security import PasswordHandler
from app.db.database import get_db
from app.models.user import User, UserCreate
from app.schemas.auth import (
    UserRegistration, UserLogin, UserResponse, TokenResponse, 
    TokenRefresh, TokenRefreshResponse, EmailVerificationResponse,
    LogoutResponse, PasswordReset, PasswordResetConfirm,
    AdminUserRegistration, AdminUserResponse
)
from app.utils.jwt_handler import jwt_handler
from app.utils.email_sender import email_sender

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


@router.post("/register", response_model=Dict[str, str], status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserRegistration,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Register a new user with username, email, and password.
    
    - **username**: Unique username (3-50 characters, alphanumeric, underscore, hyphen)
    - **email**: Valid email address (must be unique)
    - **password**: Strong password (min 8 chars, uppercase, lowercase, digit)
    
    Sends verification email after successful registration.
    """
    try:
        # Check if username already exists
        existing_user = db.exec(select(User).where(User.username == user_data.username.lower())).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already registered"
            )
        
        # Check if email already exists
        existing_email = db.exec(select(User).where(User.email == user_data.email.lower())).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )
        
        # Validate password strength
        if not PasswordHandler.validate_password_strength(user_data.password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password does not meet strength requirements"
            )
        
        # Hash password
        hashed_password = PasswordHandler.hash_password(user_data.password)
        
        # Create new user directly with hashed password
        new_user = User(
            username=user_data.username.lower(),
            email=user_data.email.lower(),
            hashed_password=hashed_password,
            is_active=True,
            is_verified=False,
            is_admin=False
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # Send verification email
        await send_verification_email(new_user, background_tasks)
        
        return {"message": "User registered successfully. Please check your email for verification."}
    
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this username or email already exists."
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {e}"
        )


@router.post("/register-admin", response_model=AdminUserResponse, status_code=status.HTTP_201_CREATED)
async def register_admin_user(
    admin_data: AdminUserRegistration,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Register a new admin user with admin secret key.
    
    - **username**: Unique username (3-50 characters, alphanumeric, underscore, hyphen)
    - **email**: Valid email address (must be unique)
    - **password**: Strong password (min 8 chars, uppercase, lowercase, digit, special char)
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
        
        # Check if email already exists
        existing_email = db.exec(select(User).where(User.email == admin_data.email.lower())).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )
        
        # Validate password strength (admin passwords have stricter requirements)
        if not PasswordHandler.validate_password_strength(admin_data.password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password does not meet strength requirements"
            )
        
        # Hash password
        hashed_password = PasswordHandler.hash_password(admin_data.password)
        
        # Create new admin user directly with hashed password
        new_admin = User(
            username=admin_data.username.lower(),
            email=admin_data.email.lower(),
            hashed_password=hashed_password,
            is_active=True,
            is_verified=True,  # Admin users are auto-verified
            is_admin=True
        )

        db.add(new_admin)
        db.commit()
        db.refresh(new_admin)
        
        return AdminUserResponse(
            message="Admin user created successfully",
            user_id=str(new_admin.id),
            username=new_admin.username,
            email=new_admin.email,
            is_admin=True
        )
    
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this username or email already exists."
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {e}"
        )


@router.post("/login", response_model=TokenResponse)
async def login_user(
    user_data: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Authenticate user and return access and refresh tokens.
    
    - **username**: Registered username
    - **password**: Correct password
    """
    user = db.exec(select(User).where(User.username == user_data.username.lower())).first()
    
    if not user or not PasswordHandler.verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
        
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive. Please contact support."
        )
        
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Please check your inbox for a verification link."
        )
        
    # Generate tokens
    access_token = jwt_handler.create_access_token(
        {"sub": str(user.id), "is_admin": user.is_admin}, timedelta(minutes=settings.jwt_access_token_expire_minutes)
    )
    refresh_token = jwt_handler.create_refresh_token(
        {"sub": str(user.id), "is_admin": user.is_admin }
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.jwt_access_token_expire_minutes * 60,  # Convert minutes to seconds
        "user": UserResponse.from_orm(user)
    }


@router.post("/refresh", response_model=TokenRefreshResponse)
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
    
    return {"access_token": new_access_token, "token_type": "bearer"}


async def send_verification_email(user: User, background_tasks: BackgroundTasks):
    """Helper to send verification email."""
    verification_token = jwt_handler.create_email_verification_token(user.email)
    verification_url = f"http://localhost:{settings.port}/auth/verify-email?token={verification_token}"
    
    background_tasks.add_task(
        email_sender.send_verification_email,
        recipient_email=user.email,
        username=user.username,
        verification_url=verification_url
    )


@router.get("/verify-email", response_model=EmailVerificationResponse)
async def verify_user_email(token: str, db: Session = Depends(get_db)):
    """
    Verify user's email address using the token from email.
    """
    try:
        payload = await jwt_handler.verify_token(token, "email_verification")
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(status_code=400, detail="Invalid verification token payload.")
            
        user = db.exec(select(User).where(User.id == user_id)).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")
            
        if user.is_verified:
            return {"message": "Email already verified."}
            
        user.is_verified = True
        db.add(user)
        db.commit()
        
        return {"message": "Email verified successfully. You can now log in."}
        
    except HTTPException as e:
        # Re-raise HTTP exceptions to be handled by FastAPI
        raise e
    except Exception:
        # Catch any other exceptions (e.g., token expiration)
        raise HTTPException(status_code=400, detail="Invalid or expired verification token.")


@router.post("/resend-verification", status_code=status.HTTP_200_OK)
async def resend_verification_email(
    email_data: Dict[str, str],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Resend verification email if the user has not yet verified their account.
    """
    email = email_data.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Email is required.")

    user = db.exec(select(User).where(User.email == email.lower())).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User with this email not found.")
        
    if user.is_verified:
        raise HTTPException(status_code=400, detail="Email is already verified.")
        
    await send_verification_email(user, background_tasks)
    
    return {"message": "Verification email sent. Please check your inbox."}


@router.post("/logout", response_model=LogoutResponse)
async def logout_user(
    current_user: User = Depends(get_current_user)
):
    """
    Logs out the current user. 
    Note: This is a placeholder as JWT is stateless. Client-side should handle token removal.
    """
    # In a real-world scenario with token blacklisting, you would add the token to a blacklist here.
    return {"message": f"User {current_user.username} logged out successfully."}


@router.post("/request-password-reset", status_code=status.HTTP_200_OK)
async def request_password_reset(
    email_data: Dict[str, str],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Request a password reset. Sends a reset link to the user's email.
    """
    email = email_data.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Email is required.")

    user = db.exec(select(User).where(User.email == email.lower())).first()
    
    if user and user.is_active:
        # Generate password reset token
        reset_token = jwt_handler.create_access_token(
            {"sub": str(user.id), "type": "password_reset"}, 
            timedelta(minutes=30)  # 30 minutes for password reset
        )
        reset_url = f"http://localhost:{settings.port}/auth/reset-password?token={reset_token}"
        
        # Send email in the background
        background_tasks.add_task(
            email_sender.send_password_reset_email,
            recipient_email=user.email,
            username=user.username,
            reset_url=reset_url
        )
        
    # Always return a success message to prevent user enumeration
    return {"message": "If an account with that email exists, a password reset link has been sent."}


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(
    reset_data: PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    """
    Reset user's password using the token from the reset link.
    """
    try:
        payload = await jwt_handler.verify_token(reset_data.token, "password_reset")
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(status_code=400, detail="Invalid reset token payload.")
            
        user = db.exec(select(User).where(User.id == user_id)).first()
        
        if not user or not user.is_active:
            raise HTTPException(status_code=404, detail="User not found or inactive.")
            
        # Validate new password
        if not PasswordHandler.validate_password_strength(reset_data.new_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password does not meet strength requirements."
            )
            
        # Update password
        user.hashed_password = PasswordHandler.hash_password(reset_data.new_password)
        db.add(user)
        db.commit()
        
        return {"message": "Password has been reset successfully."}
        
    except HTTPException as e:
        raise e
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid or expired password reset token.")


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Get the profile of the currently authenticated user.
    """
    return UserResponse.from_orm(current_user)


@router.put("/me", response_model=UserResponse)
async def update_current_user_profile(
    user_update: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update the profile of the currently authenticated user.
    
    Allowed fields for update: `username`, `email`.
    """
    update_data = user_update.copy()
    
    # Prevent updating protected fields
    for field in ["is_active", "is_verified", "is_admin", "id", "hashed_password"]:
        if field in update_data:
            del update_data[field]
            
    if not update_data:
        raise HTTPException(status_code=400, detail="No valid fields to update.")

    # Check for username/email conflicts if they are being changed
    if "username" in update_data and update_data["username"].lower() != current_user.username:
        existing_user = db.exec(select(User).where(User.username == update_data["username"].lower())).first()
        if existing_user:
            raise HTTPException(status_code=409, detail="Username already taken.")
        current_user.username = update_data["username"].lower()

    if "email" in update_data and update_data["email"].lower() != current_user.email:
        existing_email = db.exec(select(User).where(User.email == update_data["email"].lower())).first()
        if existing_email:
            raise HTTPException(status_code=409, detail="Email already registered.")
        current_user.email = update_data["email"].lower()
        current_user.is_verified = False # Require re-verification for new email
        # Consider sending a new verification email here
        
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    
    return UserResponse.from_orm(current_user)

