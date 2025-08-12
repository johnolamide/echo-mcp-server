"""
Redis connection and Pub/Sub management for caching and real-time messaging.
"""
import json
import logging
import asyncio
from typing import Optional, Dict, Any, List, Callable
from contextlib import asynccontextmanager

import redis.asyncio as redis
from redis.asyncio import ConnectionPool, Redis
from redis.exceptions import ConnectionError, TimeoutError, RedisError

from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisManager:
    """Redis connection manager with connection pooling and health monitoring."""
    
    def __init__(self):
        self._pool: Optional[ConnectionPool] = None
        self._client: Optional[Redis] = None
        self._pubsub_client: Optional[Redis] = None
        self._is_connected = False
    
    async def connect(self):
        """Initialize Redis connection pool and clients."""
        try:
            # Create connection pool
            self._pool = ConnectionPool.from_url(
                settings.redis_url,
                max_connections=20,
                retry_on_timeout=True,
                socket_keepalive=True,
                socket_keepalive_options={},
                health_check_interval=30
            )
            
            # Create main Redis client
            self._client = Redis(connection_pool=self._pool, decode_responses=True)
            
            # Create separate client for Pub/Sub (recommended by Redis)
            self._pubsub_client = Redis(connection_pool=self._pool, decode_responses=True)
            
            # Test connection
            await self._client.ping()
            self._is_connected = True
            
            logger.info("Redis connection established successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._is_connected = False
            raise
    
    async def disconnect(self):
        """Close Redis connections and cleanup resources."""
        try:
            if self._client:
                await self._client.close()
            if self._pubsub_client:
                await self._pubsub_client.close()
            if self._pool:
                await self._pool.disconnect()
            
            self._is_connected = False
            logger.info("Redis connections closed successfully")
            
        except Exception as e:
            logger.error(f"Error closing Redis connections: {e}")
    
    @property
    def client(self) -> Redis:
        """Get the main Redis client."""
        if not self._is_connected or not self._client:
            raise ConnectionError("Redis client not connected")
        return self._client
    
    @property
    def pubsub_client(self) -> Redis:
        """Get the Pub/Sub Redis client."""
        if not self._is_connected or not self._pubsub_client:
            raise ConnectionError("Redis Pub/Sub client not connected")
        return self._pubsub_client
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform Redis health check.
        
        Returns:
            dict: Health check results
        """
        health_status = {
            "redis": "unknown",
            "connection_pool": "unknown",
            "details": {}
        }
        
        try:
            if self._client:
                # Test basic connection
                pong = await self._client.ping()
                if pong:
                    health_status["redis"] = "healthy"
                    
                    # Get Redis info
                    info = await self._client.info()
                    health_status["details"] = {
                        "redis_version": info.get("redis_version"),
                        "connected_clients": info.get("connected_clients"),
                        "used_memory_human": info.get("used_memory_human"),
                        "total_commands_processed": info.get("total_commands_processed"),
                        "keyspace_hits": info.get("keyspace_hits"),
                        "keyspace_misses": info.get("keyspace_misses")
                    }
                    
                    # Check connection pool
                    if self._pool:
                        try:
                            pool_info = {
                                "max_connections": getattr(self._pool, 'max_connections', 'unknown'),
                                "connection_class": str(getattr(self._pool, 'connection_class', 'unknown'))
                            }
                            health_status["connection_pool"] = "healthy"
                            health_status["details"]["pool_info"] = pool_info
                        except Exception as pool_error:
                            health_status["connection_pool"] = "unknown"
                            health_status["details"]["pool_error"] = str(pool_error)
                else:
                    health_status["redis"] = "unhealthy"
            else:
                health_status["redis"] = "disconnected"
                
        except Exception as e:
            health_status["redis"] = "unhealthy"
            health_status["details"]["error"] = str(e)
            logger.error(f"Redis health check failed: {e}")
        
        return health_status


class RedisCache:
    """Redis caching utilities."""
    
    def __init__(self, redis_manager: RedisManager):
        self.redis_manager = redis_manager
    
    async def get(self, key: str) -> Optional[str]:
        """Get value from cache."""
        try:
            return await self.redis_manager.client.get(key)
        except RedisError as e:
            logger.error(f"Redis GET error for key {key}: {e}")
            return None
    
    async def set(self, key: str, value: str, expire: Optional[int] = None) -> bool:
        """Set value in cache with optional expiration."""
        try:
            return await self.redis_manager.client.set(key, value, ex=expire)
        except RedisError as e:
            logger.error(f"Redis SET error for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        try:
            result = await self.redis_manager.client.delete(key)
            return result > 0
        except RedisError as e:
            logger.error(f"Redis DELETE error for key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        try:
            return await self.redis_manager.client.exists(key) > 0
        except RedisError as e:
            logger.error(f"Redis EXISTS error for key {key}: {e}")
            return False
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration for a key."""
        try:
            return await self.redis_manager.client.expire(key, seconds)
        except RedisError as e:
            logger.error(f"Redis EXPIRE error for key {key}: {e}")
            return False
    
    async def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        """Get JSON value from cache."""
        try:
            value = await self.get(key)
            return json.loads(value) if value else None
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"JSON decode error for key {key}: {e}")
            return None
    
    async def set_json(self, key: str, value: Dict[str, Any], expire: Optional[int] = None) -> bool:
        """Set JSON value in cache."""
        try:
            json_value = json.dumps(value)
            return await self.set(key, json_value, expire)
        except (json.JSONEncodeError, TypeError) as e:
            logger.error(f"JSON encode error for key {key}: {e}")
            return False


class RedisPubSub:
    """Redis Pub/Sub manager for real-time messaging."""
    
    def __init__(self, redis_manager: RedisManager):
        self.redis_manager = redis_manager
        self._subscribers: Dict[str, List[Callable]] = {}
        self._pubsub = None
        self._listening_task = None
    
    async def publish(self, channel: str, message: Dict[str, Any]) -> int:
        """
        Publish message to a channel.
        
        Args:
            channel: Channel name
            message: Message data as dictionary
            
        Returns:
            int: Number of subscribers that received the message
        """
        try:
            json_message = json.dumps(message)
            return await self.redis_manager.pubsub_client.publish(channel, json_message)
        except (RedisError, json.JSONEncodeError) as e:
            logger.error(f"Failed to publish to channel {channel}: {e}")
            return 0
    
    async def subscribe(self, channel: str, callback: Callable[[str, Dict[str, Any]], None]):
        """
        Subscribe to a channel with callback function.
        
        Args:
            channel: Channel name to subscribe to
            callback: Async function to call when message received
        """
        if channel not in self._subscribers:
            self._subscribers[channel] = []
        
        self._subscribers[channel].append(callback)
        
        # Initialize pubsub if not already done
        if not self._pubsub:
            self._pubsub = self.redis_manager.pubsub_client.pubsub()
            self._listening_task = asyncio.create_task(self._listen_for_messages())
        
        # Subscribe to the channel
        await self._pubsub.subscribe(channel)
        logger.info(f"Subscribed to channel: {channel}")
    
    async def unsubscribe(self, channel: str, callback: Optional[Callable] = None):
        """
        Unsubscribe from a channel.
        
        Args:
            channel: Channel name to unsubscribe from
            callback: Specific callback to remove (if None, removes all)
        """
        if channel in self._subscribers:
            if callback:
                # Remove specific callback
                if callback in self._subscribers[channel]:
                    self._subscribers[channel].remove(callback)
            else:
                # Remove all callbacks for this channel
                self._subscribers[channel].clear()
            
            # If no more callbacks for this channel, unsubscribe
            if not self._subscribers[channel]:
                del self._subscribers[channel]
                if self._pubsub:
                    await self._pubsub.unsubscribe(channel)
                logger.info(f"Unsubscribed from channel: {channel}")
    
    async def _listen_for_messages(self):
        """Internal method to listen for Pub/Sub messages."""
        try:
            async for message in self._pubsub.listen():
                if message["type"] == "message":
                    channel = message["channel"]
                    data = message["data"]
                    
                    try:
                        # Parse JSON message
                        parsed_data = json.loads(data)
                        
                        # Call all callbacks for this channel
                        if channel in self._subscribers:
                            for callback in self._subscribers[channel]:
                                try:
                                    if asyncio.iscoroutinefunction(callback):
                                        await callback(channel, parsed_data)
                                    else:
                                        callback(channel, parsed_data)
                                except Exception as e:
                                    logger.error(f"Error in callback for channel {channel}: {e}")
                    
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse message from channel {channel}: {e}")
                        
        except Exception as e:
            logger.error(f"Error in Pub/Sub listener: {e}")
    
    async def close(self):
        """Close Pub/Sub connections and cleanup."""
        if self._listening_task:
            self._listening_task.cancel()
            try:
                await self._listening_task
            except asyncio.CancelledError:
                pass
        
        if self._pubsub:
            await self._pubsub.close()
        
        self._subscribers.clear()
        logger.info("Pub/Sub connections closed")


class RedisSessionStore:
    """Redis-based session storage for JWT tokens and user sessions."""
    
    def __init__(self, redis_manager: RedisManager):
        self.redis_manager = redis_manager
        self.cache = RedisCache(redis_manager)
    
    async def store_session(self, user_id: int, session_data: Dict[str, Any], expire_seconds: int):
        """Store user session data."""
        key = f"session:{user_id}"
        return await self.cache.set_json(key, session_data, expire_seconds)
    
    async def get_session(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user session data."""
        key = f"session:{user_id}"
        return await self.cache.get_json(key)
    
    async def delete_session(self, user_id: int) -> bool:
        """Delete user session."""
        key = f"session:{user_id}"
        return await self.cache.delete(key)
    
    async def blacklist_token(self, token_jti: str, expire_seconds: int):
        """Add JWT token to blacklist."""
        key = f"blacklist:{token_jti}"
        return await self.cache.set(key, "blacklisted", expire_seconds)
    
    async def is_token_blacklisted(self, token_jti: str) -> bool:
        """Check if JWT token is blacklisted."""
        key = f"blacklist:{token_jti}"
        return await self.cache.exists(key)


# Global Redis manager instance
redis_manager = RedisManager()

# Global utility instances
redis_cache = RedisCache(redis_manager)
redis_pubsub = RedisPubSub(redis_manager)
redis_session = RedisSessionStore(redis_manager)


@asynccontextmanager
async def get_redis_client():
    """Context manager for Redis client operations."""
    try:
        yield redis_manager.client
    except Exception as e:
        logger.error(f"Redis operation error: {e}")
        raise


async def init_redis():
    """Initialize Redis connections."""
    await redis_manager.connect()


async def close_redis():
    """Close Redis connections."""
    await redis_pubsub.close()
    await redis_manager.disconnect()