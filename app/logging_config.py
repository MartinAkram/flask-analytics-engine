import os
import logging
import logging.config
from datetime import datetime

def setup_logging():
    """
    Configure logging for the Analytics Platform with appropriate levels,
    formatters, and handlers for both development and production.
    """
    
    # Get logging level from environment
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    flask_env = os.getenv('FLASK_ENV', 'development')
    
    # Create logs directory if it doesn't exist
    log_dir = os.getenv('LOG_DIR', 'logs')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Logging configuration
    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'detailed': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
            'simple': {
                'format': '%(levelname)s - %(name)s - %(message)s'
            },
            'json': {
                'format': '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "file": "%(filename)s", "line": %(lineno)d, "message": "%(message)s"}',
                'datefmt': '%Y-%m-%dT%H:%M:%S'
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': log_level,
                'formatter': 'simple' if flask_env == 'development' else 'json',
                'stream': 'ext://sys.stdout'
            },
            'file_app': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'INFO',
                'formatter': 'detailed',
                'filename': os.path.join(log_dir, 'analytics_app.log'),
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5
            },
            'file_error': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'ERROR',
                'formatter': 'detailed',
                'filename': os.path.join(log_dir, 'analytics_errors.log'),
                'maxBytes': 10485760,  # 10MB
                'backupCount': 3
            },
            'file_access': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'INFO',
                'formatter': 'json',
                'filename': os.path.join(log_dir, 'access.log'),
                'maxBytes': 10485760,  # 10MB
                'backupCount': 10
            }
        },
        'loggers': {
            # Root logger
            '': {
                'level': log_level,
                'handlers': ['console', 'file_app'],
                'propagate': False
            },
            # App-specific loggers
            'app': {
                'level': log_level,
                'handlers': ['console', 'file_app', 'file_error'],
                'propagate': False
            },
            'app.auth': {
                'level': 'INFO',
                'handlers': ['console', 'file_app', 'file_access'],
                'propagate': False
            },
            'app.redis_client': {
                'level': 'INFO',
                'handlers': ['console', 'file_app'],
                'propagate': False
            },
            'app.utils': {
                'level': 'INFO',
                'handlers': ['console', 'file_app'],
                'propagate': False
            },
            'app.routes': {
                'level': 'INFO',
                'handlers': ['console', 'file_app', 'file_access'],
                'propagate': False
            },
            # Third-party loggers
            'werkzeug': {
                'level': 'WARNING',
                'handlers': ['file_access'],
                'propagate': False
            },
            'redis': {
                'level': 'WARNING',
                'handlers': ['console', 'file_app'],
                'propagate': False
            },
            'rq.worker': {
                'level': 'INFO',
                'handlers': ['console', 'file_app'],
                'propagate': False
            }
        }
    }
    
    # Apply the configuration
    logging.config.dictConfig(logging_config)
    
    # Log startup information
    logger = logging.getLogger('app')
    logger.info(f"Logging configured for {flask_env} environment with level {log_level}")
    logger.info(f"Log files will be stored in: {os.path.abspath(log_dir)}")
    
    return logger

def get_request_logger():
    """Get a logger specifically for request logging"""
    return logging.getLogger('app.routes')

def get_auth_logger():
    """Get a logger specifically for authentication events"""
    return logging.getLogger('app.auth')

def log_request_info(request, response_status, processing_time=None):
    """
    Log request information in a structured format for access logs
    """
    logger = get_request_logger()
    
    # Extract request information
    request_info = {
        'method': request.method,
        'path': request.path,
        'query_string': request.query_string.decode('utf-8') if request.query_string else '',
        'remote_addr': request.remote_addr,
        'user_agent': request.headers.get('User-Agent', ''),
        'status_code': response_status,
        'timestamp': datetime.utcnow().isoformat(),
    }
    
    if processing_time:
        request_info['processing_time_ms'] = processing_time
    
    # Check if authenticated
    if hasattr(request, 'api_key_info'):
        request_info['authenticated'] = True
        request_info['api_key_name'] = request.api_key_info.get('name', 'Unknown')
    else:
        request_info['authenticated'] = False
    
    # Log as structured data
    logger.info(f"Request processed", extra=request_info)

def log_auth_event(event_type, user_info=None, success=True, details=None):
    """
    Log authentication events with structured data
    """
    logger = get_auth_logger()
    
    auth_event = {
        'event_type': event_type,
        'success': success,
        'timestamp': datetime.utcnow().isoformat(),
    }
    
    if user_info:
        auth_event.update(user_info)
    
    if details:
        auth_event['details'] = details
    
    level = logging.INFO if success else logging.WARNING
    logger.log(level, f"Auth event: {event_type}", extra=auth_event) 