import os
import logging
import time
from redis import Redis, ConnectionPool, ConnectionError, TimeoutError
from contextlib import contextmanager
from typing import Optional

# Configure logging for Redis operations
logger = logging.getLogger(__name__)

class AnalyticsRedisClient:
    """
    Enhanced Redis client for the Analytics Platform with connection pooling,
    health checks, and error handling.
    """
    
    def __init__(self):
        # Connection pool configuration
        self.pool = ConnectionPool(
            host=os.getenv('REDIS_HOST', 'redis'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            db=int(os.getenv('REDIS_DB', 0)),
            max_connections=int(os.getenv('REDIS_MAX_CONNECTIONS', 20)),
            retry_on_timeout=True,
            health_check_interval=30,
            socket_connect_timeout=5,
            socket_timeout=5
        )
        
        # Create Redis connection with pool
        self._redis = Redis(connection_pool=self.pool)
        
        # Connection health status
        self._is_healthy = True
        self._last_health_check = 0
        
        # Perform initial health check
        self._check_health()
    
    def _check_health(self) -> bool:
        """Check Redis connection health"""
        try:
            self._redis.ping()
            self._is_healthy = True
            self._last_health_check = time.time()
            logger.debug("Redis health check passed")
            return True
        except (ConnectionError, TimeoutError) as e:
            self._is_healthy = False
            logger.error(f"Redis health check failed: {e}")
            return False
    
    def is_healthy(self) -> bool:
        """Return current health status with periodic checks"""
        current_time = time.time()
        # Check health every 30 seconds
        if current_time - self._last_health_check > 30:
            self._check_health()
        return self._is_healthy
    
    @contextmanager
    def get_connection(self):
        """Context manager for Redis operations with error handling"""
        if not self.is_healthy():
            # Attempt to reconnect
            if not self._check_health():
                raise ConnectionError("Redis is not available")
        
        try:
            yield self._redis
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Redis operation failed: {e}")
            self._is_healthy = False
            raise
        except Exception as e:
            logger.error(f"Unexpected Redis error: {e}")
            raise
    
    # Wrapper methods for common Redis operations
    def hset(self, name: str, key: str, value: str, ex: Optional[int] = None) -> int:
        """Set hash field with optional expiration"""
        with self.get_connection() as conn:
            result = conn.hset(name, key, value)
            if ex:
                conn.expire(name, ex)
            return result
    
    def hget(self, name: str, key: str) -> Optional[bytes]:
        """Get hash field"""
        with self.get_connection() as conn:
            return conn.hget(name, key)
    
    def hgetall(self, name: str) -> dict:
        """Get all hash fields"""
        with self.get_connection() as conn:
            return conn.hgetall(name)
    
    def hvals(self, name: str) -> list:
        """Get all hash values"""
        with self.get_connection() as conn:
            return conn.hvals(name)
    
    def hincrby(self, name: str, key: str, amount: int = 1, ex: Optional[int] = None) -> int:
        """Increment hash field with optional expiration"""
        with self.get_connection() as conn:
            result = conn.hincrby(name, key, amount)
            if ex:
                conn.expire(name, ex)
            return result
    
    def sadd(self, name: str, *values, ex: Optional[int] = None) -> int:
        """Add to set with optional expiration"""
        with self.get_connection() as conn:
            result = conn.sadd(name, *values)
            if ex:
                conn.expire(name, ex)
            return result
    
    def scard(self, name: str) -> int:
        """Get set cardinality"""
        with self.get_connection() as conn:
            return conn.scard(name)
    
    def smembers(self, name: str) -> set:
        """Get set members"""
        with self.get_connection() as conn:
            return conn.smembers(name)
    
    def zadd(self, name: str, mapping: dict, ex: Optional[int] = None) -> int:
        """Add to sorted set with optional expiration"""
        with self.get_connection() as conn:
            result = conn.zadd(name, mapping)
            if ex:
                conn.expire(name, ex)
            return result
    
    def zrevrange(self, name: str, start: int, end: int, withscores: bool = False) -> list:
        """Get sorted set range (reverse order)"""
        with self.get_connection() as conn:
            return conn.zrevrange(name, start, end, withscores=withscores)
    
    def expire(self, name: str, time: int) -> bool:
        """Set key expiration"""
        with self.get_connection() as conn:
            return conn.expire(name, time)
    
    def ping(self) -> bool:
        """Ping Redis server"""
        with self.get_connection() as conn:
            return conn.ping()
    
    def flushdb(self) -> bool:
        """Flush current database (use with caution)"""
        with self.get_connection() as conn:
            return conn.flushdb()
    
    def close(self):
        """Close connection pool"""
        if self.pool:
            self.pool.disconnect()
            logger.info("Redis connection pool closed")

# Create singleton instance
analytics_redis = AnalyticsRedisClient()

# Data retention settings (in seconds)
DATA_RETENTION = {
    'events': int(os.getenv('EVENT_TTL', 86400 * 30)),  # 30 days default
    'daily_counts': int(os.getenv('DAILY_COUNTS_TTL', 86400 * 90)),  # 90 days
    'user_sessions': int(os.getenv('USER_SESSION_TTL', 86400 * 7)),  # 7 days
    'analytics_cache': int(os.getenv('ANALYTICS_CACHE_TTL', 3600)),  # 1 hour
} 