from typing import Tuple
from flask import Blueprint, request, jsonify, current_app, Response
from .utils import (
    store_event_data, 
    generate_analytics_dashboard, 
    enrich_event_data,
    retrieve_event_by_id,
    generate_sample_analytics_events,
    get_user_analytics,
    AnalyticsPlatformError,
    RedisConnectionError
)
from .auth import require_auth, require_admin, get_client_info
from .redis_client import analytics_redis

# Create the Blueprint for the Analytics Platform API
analytics_bp = Blueprint('analytics_bp', __name__)

@analytics_bp.route('/health', methods=['GET'])
def health_check_endpoint() -> Tuple[Response, int]:
    """Health check endpoint to verify the analytics platform and Redis are operational."""
    try:
        # Check Redis connectivity
        redis_healthy = analytics_redis.is_healthy()
        
        health_status = {
            "status": "healthy" if redis_healthy else "degraded",
            "service": "Event Analytics Platform",
            "redis_connection": "healthy" if redis_healthy else "unhealthy",
            "message": "Analytics platform is operational" if redis_healthy else "Redis connection issues detected"
        }
        
        status_code = 200 if redis_healthy else 503
        return jsonify(health_status), status_code
        
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "service": "Event Analytics Platform",
            "error": str(e),
            "message": "Health check failed"
        }), 503

@analytics_bp.route('/events/', methods=['POST'])
@require_auth('write')
def submit_event_endpoint() -> Tuple[Response, int]:
    """
    Submit a new analytics event to the platform.
    Accepts event data with type, user info, and custom properties.
    Requires write permission.
    """
    try:
        # Validate request contains JSON data
        if not request.is_json:
            return jsonify({"error": "Request must contain JSON data"}), 400
        
        event_data = request.get_json()
        
        # Validate required fields
        required_fields = ['event_type', 'user_id']
        missing_fields = [field for field in required_fields if field not in event_data]
        if missing_fields:
            return jsonify({
                "error": f"Missing required fields: {', '.join(missing_fields)}"
            }), 400
        
        # Basic input validation
        event_type = event_data['event_type']
        user_id = event_data['user_id']
        
        if not isinstance(event_type, str) or len(event_type.strip()) == 0:
            return jsonify({"error": "event_type must be a non-empty string"}), 400
        
        if not isinstance(user_id, str) or len(user_id.strip()) == 0:
            return jsonify({"error": "user_id must be a non-empty string"}), 400
        
        session_id = event_data.get('session_id', f"sess_{user_id}")
        properties = event_data.get('properties', {})
        
        if not isinstance(properties, dict):
            return jsonify({"error": "properties must be a dictionary"}), 400
        
        # Store the event in Redis
        event_id = store_event_data(event_type, user_id, session_id, properties)
        
        return jsonify({
            "message": "Event successfully recorded",
            "event_id": event_id,
            "event_type": event_type,
            "user_id": user_id,
            "status": "processed"
        }), 201
        
    except RedisConnectionError as e:
        return jsonify({
            "error": "Database connection failed",
            "message": "Unable to connect to analytics database"
        }), 503
    except AnalyticsPlatformError as e:
        return jsonify({
            "error": "Platform error",
            "details": str(e)
        }), 500
    except Exception as e:
        return jsonify({
            "error": "Failed to process event",
            "details": str(e)
        }), 500

@analytics_bp.route('/analytics/', methods=['GET'])
@require_auth('read')
def analytics_dashboard_endpoint() -> Tuple[Response, int]:
    """
    Return comprehensive analytics dashboard data.
    Provides event summaries, trends, user metrics, and insights.
    Requires read permission.
    """
    try:
        # Check for optional user-specific analytics
        user_id = request.args.get('user_id')
        
        if user_id:
            # Validate user_id parameter
            if not isinstance(user_id, str) or len(user_id.strip()) == 0:
                return jsonify({"error": "user_id must be a non-empty string"}), 400
            
            # Return user-specific analytics
            user_analytics = get_user_analytics(user_id)
            return jsonify({
                "analytics_type": "user_specific",
                "data": user_analytics,
                "client_info": get_client_info()
            }), 200
        else:
            # Return platform-wide analytics dashboard
            dashboard_data = generate_analytics_dashboard()
            return jsonify({
                "analytics_type": "platform_dashboard",
                "data": dashboard_data,
                "client_info": get_client_info()
            }), 200
            
    except RedisConnectionError as e:
        return jsonify({
            "error": "Database connection failed",
            "message": "Unable to connect to analytics database"
        }), 503
    except AnalyticsPlatformError as e:
        return jsonify({
            "error": "Analytics error",
            "details": str(e)
        }), 500
    except Exception as e:
        return jsonify({
            "error": "Failed to generate analytics",
            "details": str(e)
        }), 500

@analytics_bp.route('/events/<event_id>/enrich/', methods=['PUT'])
@require_auth('write')
def enrich_event_endpoint(event_id: str) -> Tuple[Response, int]:
    """
    Enrich an existing event with additional properties or metadata.
    Allows for post-processing enhancement of event data.
    Requires write permission.
    """
    try:
        # Validate event_id parameter
        if not event_id or not isinstance(event_id, str):
            return jsonify({"error": "Invalid event_id"}), 400
        
        # Validate request contains JSON data
        if not request.is_json:
            return jsonify({"error": "Request must contain JSON data"}), 400
        
        enrichment_data = request.get_json()
        
        # Validate enrichment data structure
        if 'additional_properties' not in enrichment_data:
            return jsonify({
                "error": "Request must contain 'additional_properties' field"
            }), 400
        
        additional_properties = enrichment_data['additional_properties']
        
        if not isinstance(additional_properties, dict):
            return jsonify({"error": "additional_properties must be a dictionary"}), 400
        
        # Verify event exists and enrich it
        success = enrich_event_data(event_id, additional_properties)
        
        if not success:
            return jsonify({
                "error": "Event not found",
                "event_id": event_id
            }), 404
        
        # Return the enriched event
        enriched_event = retrieve_event_by_id(event_id)
        
        return jsonify({
            "message": "Event successfully enriched",
            "event_id": event_id,
            "enriched_event": enriched_event,
            "status": "updated"
        }), 200
        
    except RedisConnectionError as e:
        return jsonify({
            "error": "Database connection failed",
            "message": "Unable to connect to analytics database"
        }), 503
    except AnalyticsPlatformError as e:
        return jsonify({
            "error": "Platform error",
            "details": str(e)
        }), 500
    except Exception as e:
        return jsonify({
            "error": "Failed to enrich event",
            "details": str(e)
        }), 500

@analytics_bp.route('/generate-sample-data/<int:num_events>/', methods=['POST'])
@require_admin()
def generate_sample_data_endpoint(num_events: int) -> Tuple[Response, int]:
    """
    Generate sample analytics events for testing and demonstration.
    Creates realistic event data to populate the analytics dashboard.
    Requires admin permission.
    """
    try:
        # Validate the number of events is reasonable
        if num_events <= 0:
            return jsonify({"error": "Number of events must be positive"}), 400
        
        if num_events > 10000:
            return jsonify({
                "error": "Maximum 10,000 events per request for performance reasons"
            }), 400
        
        # Enqueue the sample data generation job
        job = current_app.analytics_queue.enqueue(
            generate_sample_analytics_events, 
            num_events,
            job_timeout='10m'
        )
        
        return jsonify({
            "message": f"Sample data generation started for {num_events} events",
            "job_id": job.id,
            "status": "enqueued",
            "estimated_completion": "1-5 minutes",
            "client_info": get_client_info()
        }), 202
        
    except Exception as e:
        return jsonify({
            "error": "Failed to start sample data generation",
            "details": str(e)
        }), 500

@analytics_bp.route('/events/<event_id>/', methods=['GET'])
@require_auth('read')
def get_event_details_endpoint(event_id: str) -> Tuple[Response, int]:
    """
    Retrieve detailed information about a specific event by its ID.
    Useful for debugging and detailed event inspection.
    Requires read permission.
    """
    try:
        # Validate event_id parameter
        if not event_id or not isinstance(event_id, str):
            return jsonify({"error": "Invalid event_id"}), 400
        
        event_data = retrieve_event_by_id(event_id)
        
        if not event_data:
            return jsonify({
                "error": "Event not found",
                "event_id": event_id
            }), 404
        
        return jsonify({
            "message": "Event details retrieved successfully",
            "event_data": event_data
        }), 200
        
    except RedisConnectionError as e:
        return jsonify({
            "error": "Database connection failed", 
            "message": "Unable to connect to analytics database"
        }), 503
    except AnalyticsPlatformError as e:
        return jsonify({
            "error": "Platform error",
            "details": str(e)
        }), 500
    except Exception as e:
        return jsonify({
            "error": "Failed to retrieve event details",
            "details": str(e)
        }), 500

@analytics_bp.route('/auth/info', methods=['GET'])
@require_auth('read')
def auth_info_endpoint() -> Tuple[Response, int]:
    """
    Get information about the current authentication context.
    Useful for debugging and understanding API key permissions.
    """
    try:
        client_info = get_client_info()
        return jsonify({
            "message": "Authentication information retrieved successfully",
            "client_info": client_info
        }), 200
    except Exception as e:
        return jsonify({
            "error": "Failed to retrieve auth info",
            "details": str(e)
        }), 500