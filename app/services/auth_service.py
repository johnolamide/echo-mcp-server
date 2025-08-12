"""
Authentication service for user management.
"""
from typing import Optional
from sqlmodel import Session, select
from app.models.user import User
from app.schemas.auth import UserRegistration
from app.core.security import PasswordHandler

class AuthService:
    """Service for authentication operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        statement = select(User).where(User.email == email)
        return self.db.exec(statement).first()
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        statement = select(User).where(User.username == username)
        return self.db.exec(statement).first()
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        statement = select(User).where(User.id == user_id)
        return self.db.exec(statement).first()
    
    def create_user(self, user_data: UserRegistration) -> User:
        """Create a new user."""
        hashed_password = PasswordHandler.hash_password(user_data.password)
        
        new_user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password,
            is_active=True,
            is_verified=True,  # For MCP integration, skip email verification
            is_admin=False
        )
        
        self.db.add(new_user)
        self.db.commit()
        self.db.refresh(new_user)
        
        return new_user
    
    def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password."""
        user = self.get_user_by_email(email)
        if not user:
            return None
        
        if not PasswordHandler.verify_password(password, user.hashed_password):
            return None
        
        return user
    
    def get_all_users(self, active_only: bool = False, limit: int = 50, offset: int = 0):
        """Get all users with filtering."""
        statement = select(User)
        
        if active_only:
            statement = statement.where(User.is_active == True)
        
        statement = statement.offset(offset).limit(limit)
        return self.db.exec(statement).all()