import os
import time
import hashlib
import logging
from functools import wraps
from typing import Optional, Dict, Set
from flask import request, jsonify, current_app

logger = logging.getLogger(__name__)

class AuthenticationError(Exception):
    """Exception raised for authentication failures"""
    pass

class RateLimitError(Exception):
    """Exception raised for rate limit violations"""
    pass

# Simple in-memory rate limiting (for production, use Redis)
class RateLimiter:
    def __init__(self):
        self.requests: Dict[str, list] = {}
        self.cleanup_interval = 60  # seconds
        self.last_cleanup = time.time()
    
    def is_allowed(self, key: str, limit: int, window: int) -> bool:
        """Check if request is within rate limit"""
        current_time = time.time()
        
        # Cleanup old entries periodically
        if current_time - self.last_cleanup > self.cleanup_interval:
            self._cleanup_old_entries(current_time, window)
            self.last_cleanup = current_time
        
        # Get or create request list for this key
        if key not in self.requests:
            self.requests[key] = []
        
        # Remove old requests outside the window
        self.requests[key] = [
            req_time for req_time in self.requests[key]
            if current_time - req_time < window
        ]
        
        # Check if under limit
        if len(self.requests[key]) >= limit:
            return False
        
        # Add current request
        self.requests[key].append(current_time)
        return True
    
    def _cleanup_old_entries(self, current_time: float, window: int):
        """Remove old entries to prevent memory growth"""
        for key in list(self.requests.keys()):
            self.requests[key] = [
                req_time for req_time in self.requests[key]
                if current_time - req_time < window
            ]
            # Remove empty lists
            if not self.requests[key]:
                del self.requests[key]

# Global rate limiter instance
rate_limiter = RateLimiter()

# API Keys configuration
class APIKeyManager:
    def __init__(self):
        self.api_keys = self._load_api_keys()
    
    def _load_api_keys(self) -> Dict[str, Dict]:
        """Load API keys from environment or configuration"""
        # Default admin key from environment
        admin_key = os.getenv('ANALYTICS_ADMIN_KEY', 'dev-key-analytics-2024')
        
        # In production, these would come from a database
        return {
            admin_key: {
                'name': 'Admin Key',
                'permissions': ['read', 'write', 'admin'],
                'rate_limit': 1000,  # requests per hour
                'created_at': time.time()
            },
            # Demo read-only key
            'demo-readonly-key': {
                'name': 'Demo Read Only',
                'permissions': ['read'],
                'rate_limit': 100,  # requests per hour
                'created_at': time.time()
            }
        }
    
    def validate_key(self, api_key: str) -> Optional[Dict]:
        """Validate API key and return key info"""
        if not api_key:
            return None
        
        # Simple validation (in production, use hashed keys)
        return self.api_keys.get(api_key)
    
    def has_permission(self, key_info: Dict, permission: str) -> bool:
        """Check if API key has specific permission"""
        return permission in key_info.get('permissions', [])

# Global API key manager
api_key_manager = APIKeyManager()

def extract_api_key() -> Optional[str]:
    """Extract API key from request headers or query params"""
    # Try Authorization header (Bearer token)
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        return auth_header.split(' ')[1]
    
    # Try X-API-Key header
    api_key = request.headers.get('X-API-Key')
    if api_key:
        return api_key
    
    # Try query parameter (less secure, only for demo)
    return request.args.get('api_key')

def require_auth(permission: str = 'read'):
    """Decorator to require authentication and specific permission"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # Skip authentication in development mode
                if os.getenv('FLASK_ENV') == 'development' and os.getenv('SKIP_AUTH', 'false').lower() == 'true':
                    logger.debug("Skipping authentication in development mode")
                    return f(*args, **kwargs)
                
                # Extract API key
                api_key = extract_api_key()
                if not api_key:
                    logger.warning(f"Missing API key for {request.endpoint}")
                    return jsonify({
                        'error': 'Authentication required',
                        'message': 'API key must be provided in Authorization header or X-API-Key header'
                    }), 401
                
                # Validate API key
                key_info = api_key_manager.validate_key(api_key)
                if not key_info:
                    logger.warning(f"Invalid API key attempted: {api_key[:8]}...")
                    return jsonify({
                        'error': 'Invalid API key',
                        'message': 'The provided API key is not valid'
                    }), 401
                
                # Check permissions
                if not api_key_manager.has_permission(key_info, permission):
                    logger.warning(f"Insufficient permissions for key {key_info['name']}: required {permission}")
                    return jsonify({
                        'error': 'Insufficient permissions',
                        'message': f'This API key does not have {permission} permission'
                    }), 403
                
                # Rate limiting
                client_id = f"key_{hashlib.md5(api_key.encode()).hexdigest()[:8]}"
                rate_limit = key_info.get('rate_limit', 100)
                
                if not rate_limiter.is_allowed(client_id, rate_limit, 3600):  # 1 hour window
                    logger.warning(f"Rate limit exceeded for {client_id}")
                    return jsonify({
                        'error': 'Rate limit exceeded',
                        'message': f'Rate limit of {rate_limit} requests per hour exceeded'
                    }), 429
                
                # Add key info to request context
                request.api_key_info = key_info
                
                logger.debug(f"Authenticated request for {key_info['name']} with {permission} permission")
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"Authentication error: {e}")
                return jsonify({
                    'error': 'Authentication error',
                    'message': 'An error occurred during authentication'
                }), 500
        
        return decorated_function
    return decorator

def require_admin():
    """Decorator to require admin permissions"""
    return require_auth('admin')

def rate_limit(requests_per_hour: int = 100):
    """Decorator to apply custom rate limiting"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get client identifier
            client_id = request.remote_addr
            if hasattr(request, 'api_key_info'):
                client_id = f"key_{hashlib.md5(extract_api_key().encode()).hexdigest()[:8]}"
            
            if not rate_limiter.is_allowed(client_id, requests_per_hour, 3600):
                logger.warning(f"Rate limit exceeded for {client_id}")
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'message': f'Rate limit of {requests_per_hour} requests per hour exceeded'
                }), 429
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def get_client_info() -> Dict:
    """Get information about the current authenticated client"""
    if hasattr(request, 'api_key_info'):
        return {
            'authenticated': True,
            'key_name': request.api_key_info['name'],
            'permissions': request.api_key_info['permissions'],
            'rate_limit': request.api_key_info['rate_limit']
        }
    return {
        'authenticated': False,
        'client_ip': request.remote_addr
    } 