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
        
        # Create new user
        user_create = UserCreate(
            username=user_data.username.lower(),
            email=user_data.email.lower(),
            password=user_data.password  # Password will be hashed by the model event
        )
        
        new_user = User.from_orm(user_create)
        new_user.hashed_password = hashed_password

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
    access_token = await jwt_handler.create_token(
        user.id, "access", timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    refresh_token = await jwt_handler.create_token(
        user.id, "refresh", timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
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
    new_access_token = await jwt_handler.create_token(
        user.id, "access", timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return {"access_token": new_access_token, "token_type": "bearer"}


async def send_verification_email(user: User, background_tasks: BackgroundTasks):
    """Helper to send verification email."""
    verification_token = await jwt_handler.create_token(
        user.id, "email_verification", timedelta(hours=settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS)
    )
    verification_url = f"{settings.SERVER_HOST}/auth/verify-email?token={verification_token}"
    
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
        reset_token = await jwt_handler.create_token(
            user.id, "password_reset", timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)
        )
        reset_url = f"{settings.CLIENT_URL}/reset-password?token={reset_token}" # Assumes a client-side URL
        
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

from datetime import timedelta
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.security import PasswordHandler
from app.db.database import get_db
from app.models.user import User
from app.schemas.auth import (
    UserRegistration, UserLogin, UserResponse, TokenResponse, 
    TokenRefresh, TokenRefreshResponse, EmailVerificationResponse,
    LogoutResponse, PasswordReset, PasswordResetConfirm
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
    
    user_stmt = select(User).where(User.id == user_id)
    user = db.exec(user_stmt).first()
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
        existing_user_stmt = select(User).where(User.username == user_data.username.lower())
        existing_user = db.exec(existing_user_stmt).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already registered"
            )
        
        # Check if email already exists
        existing_email_stmt = select(User).where(User.email == user_data.email.lower())
        existing_email = db.exec(existing_email_stmt).first()
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
        
        # Create new user
        new_user = User(
            username=user_data.username.lower(),
            email=user_data.email.lower(),
            hashed_password=hashed_password,
            is_active=True,
            is_verified=True,  # Email verification disabled for now
            is_admin=False
        )
        
        db.add(new_user)
        db.flush()  # This will assign the ID without committing
        
        # Get the user data after flush but before commit
        user_id = new_user.id
        username = new_user.username
        email = new_user.email
        
        # Commit the transaction
        db.commit()
        
        # Refresh the object to ensure it's still valid after commit
        db.refresh(new_user)
        
        return {
            "message": "User registered successfully. Email verification disabled.",
            "user_id": str(user_id),
            "username": username,
            "email": email
        }
        
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already exists"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. Please try again."
        )


@router.post("/login", response_model=TokenResponse)
async def login_user(
    user_credentials: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Authenticate user and return JWT tokens.
    
    - **email**: User's email address
    - **password**: User's password
    
    Returns access token, refresh token, and user information.
    """
    # Find user by email
    user_stmt = select(User).where(User.email == user_credentials.email.lower())
    user = db.exec(user_stmt).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Verify password
    if not PasswordHandler.verify_password(user_credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Check if user account is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive"
        )
    
    # Check if email is verified (commented out for now)
    # if not user.is_verified:
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail="Email not verified. Please check your email for verification instructions."
    #     )
    
    # Create token payload
    token_data = {
        "sub": str(user.id),
        "username": user.username,
        "email": user.email,
        "is_admin": user.is_admin
    }
    
    # Generate tokens
    access_token = jwt_handler.create_access_token(token_data)
    refresh_token = jwt_handler.create_refresh_token({"sub": str(user.id)})
    
    # Convert user to response model
    user_response = UserResponse.model_validate(user)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60,
        user=user_response
    )


@router.post("/refresh", response_model=TokenRefreshResponse)
async def refresh_token(
    token_data: TokenRefresh,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token.
    
    - **refresh_token**: Valid refresh token
    
    Returns new access token.
    """
    try:
        # Verify refresh token
        payload = await jwt_handler.verify_token(token_data.refresh_token, "refresh")
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Get user from database
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active or not user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Create new access token
        token_payload = {
            "sub": str(user.id),
            "username": user.username,
            "email": user.email,
            "is_admin": user.is_admin
        }
        
        new_access_token = jwt_handler.create_access_token(token_payload)
        
        return TokenRefreshResponse(
            access_token=new_access_token,
            token_type="bearer",
            expires_in=settings.jwt_access_token_expire_minutes * 60
        )
        
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


@router.post("/logout", response_model=LogoutResponse)
async def logout_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: User = Depends(get_current_user)
):
    """
    Logout user by blacklisting their current token.
    
    Requires valid access token in Authorization header.
    """
    try:
        # Blacklist the current access token
        await jwt_handler.blacklist_token(credentials.credentials)
        
        return LogoutResponse(
            message="Successfully logged out"
        )
        
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


@router.get("/verify/{token}", response_model=EmailVerificationResponse)
async def verify_email(
    token: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Verify user email address using verification token.
    
    - **token**: Email verification token from email
    
    Activates user account and sends welcome email.
    """
    try:
        # Verify email token and extract email
        email = jwt_handler.verify_email_token(token)
        
        # Find user by email
        user = db.query(User).filter(User.email == email.lower()).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check if already verified
        if user.is_verified:
            return EmailVerificationResponse(
                message="Email already verified",
                verified=True
            )
        
        # Update user verification status
        user.is_verified = True
        db.commit()
        
        # Send welcome email in background
        background_tasks.add_task(
            email_sender.send_welcome_email,
            user.email,
            user.username
        )
        
        return EmailVerificationResponse(
            message="Email verified successfully. Welcome to the platform!",
            verified=True
        )
        
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )


@router.post("/resend-verification")
async def resend_verification_email(
    email_data: Dict[str, str],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Resend verification email to user.
    
    - **email**: User's email address
    """
    email = email_data.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address is required"
        )
    
    # Find user by email
    user = db.query(User).filter(User.email == email.lower()).first()
    if not user:
        # Don't reveal if email exists or not for security
        return {"message": "If the email exists, a verification email has been sent."}
    
    # Check if already verified
    if user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already verified"
        )
    
    # Send verification email in background
    background_tasks.add_task(
        email_sender.send_verification_email,
        user.email,
        user.username
    )
    
    return {"message": "Verification email sent successfully."}


@router.post("/forgot-password")
async def forgot_password(
    password_reset: PasswordReset,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Send password reset email to user.
    
    - **email**: User's email address
    """
    # Find user by email
    user = db.query(User).filter(User.email == password_reset.email.lower()).first()
    
    # Don't reveal if email exists or not for security
    if user and user.is_active and user.is_verified:
        # Create password reset token (1 hour expiry)
        reset_token = jwt_handler.create_email_verification_token(user.email)
        
        # Send password reset email in background
        background_tasks.add_task(
            email_sender.send_password_reset_email,
            user.email,
            user.username,
            reset_token
        )
    
    return {"message": "If the email exists, a password reset email has been sent."}


@router.post("/reset-password")
async def reset_password(
    reset_data: PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    """
    Reset user password using reset token.
    
    - **token**: Password reset token from email
    - **new_password**: New password for the account
    """
    try:
        # Verify reset token and extract email
        email = jwt_handler.verify_email_token(reset_data.token)
        
        # Find user by email
        user = db.query(User).filter(User.email == email.lower()).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found or inactive"
            )
        
        # Validate new password strength
        if not PasswordHandler.validate_password_strength(reset_data.new_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password does not meet strength requirements"
            )
        
        # Hash new password
        new_hashed_password = PasswordHandler.hash_password(reset_data.new_password)
        
        # Update user password
        user.hashed_password = new_hashed_password
        db.commit()
        
        return {"message": "Password reset successfully. You can now login with your new password."}
        
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current authenticated user information.
    
    Requires valid access token in Authorization header.
    """
    return UserResponse.from_orm(current_user)


@router.post("/create-admin", response_model=AdminUserResponse, status_code=status.HTTP_201_CREATED)
async def create_admin_user(
    admin_data: AdminUserRegistration,
    db: Session = Depends(get_db)
):
    """
    Create an admin user account.
    
    This endpoint allows creating admin users with elevated privileges.
    Requires a valid admin secret key for security.
    
    - **username**: Unique username for the admin account (3-50 characters)
    - **email**: Valid email address (must be unique)
    - **password**: Strong password (min 8 chars, uppercase, lowercase, digit, special char)
    - **admin_secret**: Secret key required to create admin accounts
    
    Returns the created admin user information.
    """
    try:
        # Verify admin secret key
        if admin_data.admin_secret != settings.admin_secret_key:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid admin secret key"
            )
        
        # Check if username already exists
        existing_user_stmt = select(User).where(User.username == admin_data.username.lower())
        existing_user = db.exec(existing_user_stmt).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already exists"
            )
        
        # Check if email already exists
        existing_email_stmt = select(User).where(User.email == admin_data.email.lower())
        existing_email = db.exec(existing_email_stmt).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )
        
        # Hash password
        hashed_password = PasswordHandler.hash_password(admin_data.password)
        
        # Create new admin user
        new_admin = User(
            username=admin_data.username.lower(),
            email=admin_data.email.lower(),
            hashed_password=hashed_password,
            is_active=True,
            is_verified=True,  # Admin users are automatically verified
            is_admin=True      # Set admin privileges
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
        
    except HTTPException:
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email or username already exists"
        )
    except Exception as e:
        db.rollback()
        logging.getLogger(__name__).error(f"Admin user creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Admin user creation failed. Please try again."
        )