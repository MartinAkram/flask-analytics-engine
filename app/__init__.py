import os
import atexit
from flask import Flask
from rq import Queue

from . import routes
from .redis_client import analytics_redis
from .logging_config import setup_logging

# Configure logging before importing other modules
logger = setup_logging()

# Create the RQ queue for analytics background processing
analytics_queue = Queue('analytics-processing-queue', connection=analytics_redis._redis)

# Create the Flask application for the Event Analytics Platform
def create_app() -> Flask:
    app = Flask(__name__)
    
    # Configure Flask app
    app.config['JSON_SORT_KEYS'] = False
    app.config['JSONIFY_PRETTYPRINT_REGULAR'] = os.getenv('FLASK_ENV') == 'development'
    
    # Register blueprint
    app.register_blueprint(routes.analytics_bp)
    
    # Attach Redis and RQ to app context
    app.analytics_redis = analytics_redis 
    app.analytics_queue = analytics_queue
    
    # Register shutdown handler
    def cleanup_on_shutdown():
        """Clean up resources on application shutdown"""
        try:
            logger.info("Shutting down Analytics Platform...")
            analytics_redis.close()
            logger.info("Redis connections closed")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    atexit.register(cleanup_on_shutdown)
    
    # Log successful startup
    logger.info("Event Analytics Platform initialized successfully")
    logger.info(f"Environment: {os.getenv('FLASK_ENV', 'development')}")
    logger.info(f"Redis connection: {'healthy' if analytics_redis.is_healthy() else 'unhealthy'}")
    
    return app