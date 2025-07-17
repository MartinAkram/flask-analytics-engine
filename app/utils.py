import json
import uuid
import random
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from collections import defaultdict
from redis import ConnectionError, TimeoutError

from .redis_client import analytics_redis, DATA_RETENTION

# Configure logging
logger = logging.getLogger(__name__)

# ───────────────────────────────────────
# Analytics Platform Core Configuration
# ───────────────────────────────────────

ANALYTICS_WORKER_URL = 'http://backend-service:5000'

class AnalyticsPlatformError(Exception):
    """Custom exception for Analytics Platform operations"""
    pass

class EventNotFoundError(AnalyticsPlatformError):
    """Exception raised when an event is not found"""
    pass

class RedisConnectionError(AnalyticsPlatformError):
    """Exception raised when Redis connection fails"""
    pass

# ───────────────────────────────────────
# Event Storage and Retrieval Functions
# ───────────────────────────────────────

def store_event_data(event_type: str, user_id: str, session_id: str, properties: Dict[str, Any]) -> str:
    """
    Store a new analytics event in Redis with a unique event ID and user indexing.
    Returns the generated event ID for the stored event.
    """
    try:
        # Generate unique event ID
        event_id = f"evt_{uuid.uuid4().hex[:12]}"
        
        # Create event data structure
        event_data = {
            'event_id': event_id,
            'event_type': event_type,
            'user_id': user_id,
            'session_id': session_id,
            'timestamp': datetime.utcnow().isoformat(),
            'properties': properties
        }
        
        # Store the complete event data with TTL
        analytics_redis.hset(
            name='analytics_events',
            key=event_id,
            value=json.dumps(event_data),
            ex=DATA_RETENTION['events']
        )
        
        # Create user-specific index for fast user queries
        timestamp = datetime.utcnow().timestamp()
        analytics_redis.zadd(
            name=f'user_events:{user_id}',
            mapping={event_id: timestamp},
            ex=DATA_RETENTION['user_sessions']
        )
        
        # Create session-specific index
        analytics_redis.zadd(
            name=f'session_events:{session_id}',
            mapping={event_id: timestamp},
            ex=DATA_RETENTION['user_sessions']
        )
        
        # Update event type counters for quick analytics
        analytics_redis.hincrby(
            name='event_type_metrics',
            key=event_type,
            amount=1,
            ex=DATA_RETENTION['daily_counts']
        )
        
        # Track unique users and sessions with TTL
        analytics_redis.sadd(
            'unique_users', 
            user_id,
            ex=DATA_RETENTION['user_sessions']
        )
        analytics_redis.sadd(
            'unique_sessions', 
            session_id,
            ex=DATA_RETENTION['user_sessions']
        )
        
        # Store daily event counts for trending
        date_key = datetime.utcnow().strftime('%Y-%m-%d')
        analytics_redis.hincrby(
            name='daily_event_counts',
            key=date_key,
            amount=1,
            ex=DATA_RETENTION['daily_counts']
        )
        
        logger.info(f"Event {event_id} stored successfully for user {user_id}")
        return event_id
        
    except (ConnectionError, TimeoutError) as e:
        logger.error(f"Redis connection failed while storing event: {e}")
        raise RedisConnectionError(f"Failed to connect to Redis: {e}")
    except Exception as e:
        logger.error(f"Failed to store event data: {e}")
        raise AnalyticsPlatformError(f"Event storage failed: {e}")

def retrieve_event_by_id(event_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a specific event by its ID from Redis.
    Returns None if event is not found.
    """
    try:
        event_data = analytics_redis.hget('analytics_events', event_id)
        if event_data:
            return json.loads(event_data.decode('utf-8'))
        return None
    except (ConnectionError, TimeoutError) as e:
        logger.error(f"Redis connection failed while retrieving event {event_id}: {e}")
        raise RedisConnectionError(f"Failed to connect to Redis: {e}")
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode event data for {event_id}: {e}")
        raise AnalyticsPlatformError(f"Event data corruption: {e}")
    except Exception as e:
        logger.error(f"Failed to retrieve event {event_id}: {e}")
        raise AnalyticsPlatformError(f"Event retrieval failed: {e}")

def enrich_event_data(event_id: str, additional_properties: Dict[str, Any]) -> bool:
    """
    Add additional properties to an existing event.
    Returns True if enrichment was successful, False if event not found.
    """
    try:
        # Retrieve existing event
        event_data = retrieve_event_by_id(event_id)
        if not event_data:
            logger.warning(f"Event {event_id} not found for enrichment")
            return False
        
        # Merge additional properties
        event_data['properties'].update(additional_properties)
        event_data['last_enriched'] = datetime.utcnow().isoformat()
        
        # Store updated event with original TTL preserved
        analytics_redis.hset(
            name='analytics_events',
            key=event_id,
            value=json.dumps(event_data),
            ex=DATA_RETENTION['events']
        )
        
        logger.info(f"Event {event_id} enriched successfully")
        return True
        
    except (ConnectionError, TimeoutError) as e:
        logger.error(f"Redis connection failed while enriching event {event_id}: {e}")
        raise RedisConnectionError(f"Failed to connect to Redis: {e}")
    except Exception as e:
        logger.error(f"Failed to enrich event {event_id}: {e}")
        raise AnalyticsPlatformError(f"Event enrichment failed: {e}")

# ───────────────────────────────────────
# Analytics Dashboard Functions
# ───────────────────────────────────────

def generate_analytics_dashboard() -> Dict[str, Any]:
    """
    Generate comprehensive analytics data for the dashboard.
    Returns aggregated metrics, event breakdowns, and insights.
    """
    try:
        # Get basic counts with error handling for empty metrics
        event_counts = analytics_redis.hvals('event_type_metrics')
        total_events = sum(int(count.decode('utf-8')) for count in event_counts) if event_counts else 0
        unique_users = analytics_redis.scard('unique_users')
        unique_sessions = analytics_redis.scard('unique_sessions')
        
        # Get event type breakdown
        event_metrics = analytics_redis.hgetall('event_type_metrics')
        event_breakdown = []
        for event_type_bytes, count_bytes in event_metrics.items():
            event_type = event_type_bytes.decode('utf-8')
            count = int(count_bytes.decode('utf-8'))
            percentage = (count / total_events * 100) if total_events > 0 else 0
            event_breakdown.append({
                'event_type': event_type,
                'count': count,
                'percentage': round(percentage, 2)
            })
        
        # Sort by count descending
        event_breakdown.sort(key=lambda x: x['count'], reverse=True)
        
        # Get daily trends (last 7 days)
        daily_trends = []
        for i in range(7):
            date = (datetime.utcnow() - timedelta(days=i)).strftime('%Y-%m-%d')
            count = analytics_redis.hget('daily_event_counts', date)
            daily_trends.append({
                'date': date,
                'event_count': int(count.decode('utf-8')) if count else 0
            })
        
        # Calculate conversion metrics (simplified) with error handling
        page_views = int(analytics_redis.hget('event_type_metrics', 'page_view') or 0)
        registrations = int(analytics_redis.hget('event_type_metrics', 'user_registered') or 0)
        purchases = int(analytics_redis.hget('event_type_metrics', 'purchase_completed') or 0)
        
        conversion_rate = (registrations / page_views * 100) if page_views > 0 else 0
        purchase_rate = (purchases / registrations * 100) if registrations > 0 else 0
        
        dashboard_data = {
            'summary': {
                'total_events': total_events,
                'unique_users': unique_users,
                'unique_sessions': unique_sessions,
                'conversion_rate': round(conversion_rate, 2),
                'purchase_conversion_rate': round(purchase_rate, 2)
            },
            'event_breakdown': event_breakdown,
            'daily_trends': daily_trends,
            'top_event_types': event_breakdown[:5],
            'generated_at': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Generated analytics dashboard with {total_events} total events")
        return dashboard_data
        
    except (ConnectionError, TimeoutError) as e:
        logger.error(f"Redis connection failed while generating dashboard: {e}")
        raise RedisConnectionError(f"Failed to connect to Redis: {e}")
    except Exception as e:
        logger.error(f"Failed to generate analytics dashboard: {e}")
        raise AnalyticsPlatformError(f"Analytics generation failed: {e}")

def get_user_analytics(user_id: str, limit: int = 100) -> Dict[str, Any]:
    """
    Get analytics data specific to a particular user using indexed lookups.
    Returns user-specific event history and metrics efficiently.
    """
    try:
        # Use user-specific index for fast retrieval
        user_event_ids = analytics_redis.zrevrange(f'user_events:{user_id}', 0, limit - 1)
        
        if not user_event_ids:
            logger.info(f"No events found for user {user_id}")
            return {
                'user_id': user_id,
                'total_events': 0,
                'event_types': {},
                'recent_events': [],
                'first_seen': None,
                'last_seen': None
            }
        
        # Retrieve event details for the user's events
        user_events = []
        for event_id_bytes in user_event_ids:
            event_id = event_id_bytes.decode('utf-8')
            event_data = retrieve_event_by_id(event_id)
            if event_data:
                user_events.append(event_data)
        
        # Sort by timestamp (most recent first)
        user_events.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # Calculate user metrics
        event_types = defaultdict(int)
        for event in user_events:
            event_types[event['event_type']] += 1
        
        result = {
            'user_id': user_id,
            'total_events': len(user_events),
            'event_types': dict(event_types),
            'recent_events': user_events[:10],  # Limit to 10 most recent
            'first_seen': user_events[-1]['timestamp'] if user_events else None,
            'last_seen': user_events[0]['timestamp'] if user_events else None
        }
        
        logger.info(f"Retrieved analytics for user {user_id}: {len(user_events)} events")
        return result
        
    except (ConnectionError, TimeoutError) as e:
        logger.error(f"Redis connection failed while getting user analytics for {user_id}: {e}")
        raise RedisConnectionError(f"Failed to connect to Redis: {e}")
    except Exception as e:
        logger.error(f"Failed to get user analytics for {user_id}: {e}")
        raise AnalyticsPlatformError(f"User analytics failed: {e}")

# ───────────────────────────────────────
# Background Processing Functions
# ───────────────────────────────────────

def generate_sample_analytics_events(num_events: int) -> None:
    """
    Background job function to generate sample analytics events for testing.
    This simulates real user behavior with realistic event patterns.
    """
    try:
        event_types = [
            'page_view', 'button_click', 'form_submit', 'feature_used',
            'user_registered', 'purchase_completed', 'session_start', 'logout'
        ]
        
        pages = ['/dashboard', '/pricing', '/features', '/about', '/contact', '/login', '/signup']
        user_pool = [f"user_{i:05d}" for i in range(1, 501)]  # 500 sample users
        
        events_generated = 0
        for _ in range(num_events):
            try:
                # Generate realistic event data
                event_type = random.choice(event_types)
                user_id = random.choice(user_pool)
                session_id = f"sess_{uuid.uuid4().hex[:8]}"
                
                # Create event-specific properties
                properties = _generate_event_properties(event_type, pages)
                
                # Store the event
                store_event_data(event_type, user_id, session_id, properties)
                events_generated += 1
                
                # Log progress every 100 events
                if events_generated % 100 == 0:
                    logger.info(f"Generated {events_generated}/{num_events} sample events")
                    
            except Exception as e:
                logger.error(f"Failed to generate sample event {events_generated + 1}: {e}")
                continue
        
        logger.info(f"Successfully generated {events_generated} sample events")
        
    except Exception as e:
        logger.error(f"Failed to generate sample events: {e}")
        raise AnalyticsPlatformError(f"Sample event generation failed: {e}")

def _generate_event_properties(event_type: str, pages: List[str]) -> Dict[str, Any]:
    """
    Generate realistic properties for different event types.
    """
    base_properties = {
        'timestamp': datetime.utcnow().isoformat(),
        'user_agent': random.choice([
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)'
        ]),
        'device_type': random.choice(['desktop', 'mobile', 'tablet']),
        'browser': random.choice(['Chrome', 'Safari', 'Firefox', 'Edge']),
        'country': random.choice(['US', 'UK', 'CA', 'DE', 'FR', 'JP', 'AU']),
    }
    
    if event_type == 'page_view':
        base_properties.update({
            'page_url': random.choice(pages),
            'referrer': random.choice(['google.com', 'facebook.com', 'direct', 'twitter.com']),
            'load_time': round(random.uniform(0.5, 3.0), 2)
        })
    elif event_type == 'button_click':
        base_properties.update({
            'button_text': random.choice(['Sign Up', 'Learn More', 'Get Started', 'Contact Us']),
            'page_url': random.choice(pages),
            'element_position': random.choice(['header', 'sidebar', 'footer', 'main'])
        })
    elif event_type == 'purchase_completed':
        base_properties.update({
            'revenue': round(random.uniform(10.0, 500.0), 2),
            'currency': 'USD',
            'product_name': random.choice(['Basic Plan', 'Pro Plan', 'Enterprise Plan']),
            'payment_method': random.choice(['credit_card', 'paypal', 'stripe'])
        })
    elif event_type == 'user_registered':
        base_properties.update({
            'signup_method': random.choice(['email', 'google', 'facebook']),
            'plan_selected': random.choice(['free', 'basic', 'pro']),
            'referral_source': random.choice(['organic', 'paid_ads', 'referral', 'social'])
        })
    
    return base_properties

def process_analytics_aggregations() -> None:
    """
    Background job to process and update analytics aggregations.
    This runs periodically to compute complex metrics and insights.
    """
    try:
        current_hour = datetime.utcnow().strftime('%Y-%m-%d-%H')
        
        # Get hourly event count from daily counts (simplified approach)
        current_date = datetime.utcnow().strftime('%Y-%m-%d')
        daily_count = analytics_redis.hget('daily_event_counts', current_date)
        hourly_count = int(daily_count.decode('utf-8')) if daily_count else 0
        
        # Store hourly aggregation with TTL
        analytics_redis.hset(
            name='hourly_aggregations',
            key=current_hour,
            value=hourly_count,
            ex=DATA_RETENTION['analytics_cache']
        )
        
        logger.info(f"Processed analytics aggregations for hour {current_hour}: {hourly_count} events")
        
    except (ConnectionError, TimeoutError) as e:
        logger.error(f"Redis connection failed during aggregation: {e}")
        raise RedisConnectionError(f"Failed to connect to Redis: {e}")
    except Exception as e:
        logger.error(f"Failed to process analytics aggregations: {e}")
        raise AnalyticsPlatformError(f"Analytics aggregation failed: {e}")

def cleanup_expired_data() -> Dict[str, int]:
    """
    Background job to clean up expired data and maintain Redis performance.
    Returns statistics about cleanup operations.
    """
    try:
        cleanup_stats = {
            'expired_user_indexes': 0,
            'expired_session_indexes': 0,
            'total_operations': 0
        }
        
        # Note: Redis automatically handles TTL expiration, but we can add
        # manual cleanup for specific patterns if needed
        
        logger.info(f"Cleanup completed: {cleanup_stats}")
        return cleanup_stats
        
    except Exception as e:
        logger.error(f"Failed to cleanup expired data: {e}")
        raise AnalyticsPlatformError(f"Data cleanup failed: {e}")  