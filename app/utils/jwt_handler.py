"""
JWT token handling utilities with blacklist management.
"""
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Set
from jose import JWTError, jwt
from fastapi import HTTPException, status

from app.core.config import settings
from app.db.redis_client import redis_manager


class JWTHandler:
    """Enhanced JWT token creation and validation with Redis blacklist support."""
    
    def __init__(self):
        self.redis_manager = redis_manager
    
    async def _get_redis(self):
        """Get Redis client for blacklist operations."""
        return self.redis_manager.client
    
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token with unique identifier."""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.jwt_access_token_expire_minutes)
        
        # Add token metadata
        to_encode.update({
            "exp": expire,
            "type": "access",
            "iat": datetime.utcnow(),
            "jti": secrets.token_urlsafe(32)  # Unique token ID for blacklisting
        })
        
        encoded_jwt = jwt.encode(
            to_encode, 
            settings.jwt_secret_key, 
            algorithm=settings.jwt_algorithm
        )
        return encoded_jwt
    
    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """Create JWT refresh token with extended expiry."""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=settings.jwt_refresh_token_expire_days)
        
        to_encode.update({
            "exp": expire,
            "type": "refresh",
            "iat": datetime.utcnow(),
            "jti": secrets.token_urlsafe(32)
        })
        
        encoded_jwt = jwt.encode(
            to_encode,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm
        )
        return encoded_jwt
    
    def create_email_verification_token(self, email: str) -> str:
        """Create token for email verification with 24-hour expiry."""
        data = {
            "email": email,
            "type": "email_verification",
            "exp": datetime.utcnow() + timedelta(hours=24),
            "iat": datetime.utcnow(),
            "jti": secrets.token_urlsafe(32)
        }
        
        return jwt.encode(
            data,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm
        )
    
    async def verify_token(self, token: str, token_type: str = "access") -> Dict[str, Any]:
        """Verify and decode JWT token with blacklist check."""
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm]
            )
            
            # Check token type
            if payload.get("type") != token_type:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Invalid token type. Expected {token_type}"
                )
            
            # Check if token is blacklisted
            token_id = payload.get("jti")
            if token_id and await self._is_token_blacklisted(token_id):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked"
                )
            
            return payload
            
        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )
    
    def verify_email_token(self, token: str) -> str:
        """Verify email verification token and return email."""
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm]
            )
            
            if payload.get("type") != "email_verification":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid token type"
                )
            
            email = payload.get("email")
            if not email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid token payload"
                )
            
            return email
            
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired token"
            )
    
    async def blacklist_token(self, token: str) -> None:
        """Add token to Redis blacklist with expiry."""
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
                options={"verify_exp": False}  # Don't verify expiry for blacklisting
            )
            
            token_id = payload.get("jti")
            if token_id:
                redis = await self._get_redis()
                
                # Calculate TTL based on token expiry
                exp_timestamp = payload.get("exp")
                if exp_timestamp:
                    exp_datetime = datetime.fromtimestamp(exp_timestamp)
                    ttl = int((exp_datetime - datetime.utcnow()).total_seconds())
                    if ttl > 0:
                        await redis.setex(f"blacklist:{token_id}", ttl, "1")
                
        except JWTError:
            # Token is invalid anyway, no need to blacklist
            pass
    
    async def _is_token_blacklisted(self, token_id: str) -> bool:
        """Check if token ID is in Redis blacklist."""
        try:
            redis = await self._get_redis()
            result = await redis.get(f"blacklist:{token_id}")
            return result is not None
        except Exception:
            # If Redis is unavailable, allow token (fail open)
            return False
    
    def decode_token_payload(self, token: str) -> Dict[str, Any]:
        """Decode token without verification (for extracting payload info)."""
        try:
            return jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
                options={"verify_signature": False, "verify_exp": False}
            )
        except JWTError:
            return {}


# Global JWT handler instance
jwt_handler = JWTHandler()


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Simple synchronous token verification for WebSocket authentication.
    Returns payload if valid, None if invalid.
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        
        # Check token type
        if payload.get("type") != "access":
            return None
        
        return payload
        
    except JWTError:
        return None