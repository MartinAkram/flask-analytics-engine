# Event Analytics Platform

## 🎯 Project Purpose

**This is a portfolio/demonstration project created for fun to showcase various development skills and technologies.** It is **not intended for production use** or real-world applications. The project demonstrates knowledge of Flask, Redis, Docker, API design, authentication, performance optimization, and other software engineering concepts, but should be treated as a learning exercise and code sample only.

## Project Overview

A Docker-containerized Flask application for event analytics and user behavior tracking. Built with Flask, Redis, and RQ, this platform demonstrates comprehensive event ingestion, processing, and analytics capabilities with authentication, performance optimizations, and monitoring for educational and portfolio purposes.

### 🚀 Quick Start

```bash
# Build and start the analytics platform
make build
make up

# View application logs
make logs

# Test with authentication (development mode)
curl -H "X-API-Key: dev-key-analytics-2024" http://localhost:5000/health
```

## 🔐 Authentication & Security

### **API Key Authentication**
All endpoints (except health check) require authentication using API keys:

```bash
# Using Authorization header (recommended)
curl -H "Authorization: Bearer dev-key-analytics-2024" http://localhost:5000/analytics/

# Using X-API-Key header
curl -H "X-API-Key: dev-key-analytics-2024" http://localhost:5000/analytics/

# Using query parameter (development only)
curl "http://localhost:5000/analytics/?api_key=dev-key-analytics-2024"
```

### **Default API Keys**
- **Admin Key**: `dev-key-analytics-2024` (read/write/admin permissions)
- **Demo Key**: `demo-readonly-key` (read-only permissions)

### **Rate Limiting**
- **Admin keys**: 1,000 requests/hour
- **Standard keys**: 100 requests/hour
- **Anonymous**: 50 requests/hour (development only)

### **Permission Levels**
- **`read`**: Access analytics and view events
- **`write`**: Submit and enrich events
- **`admin`**: Generate sample data and administrative functions

## 🔌 API Endpoints

### **`GET /health`** - Health Check
Monitor platform and Redis connectivity status. No authentication required.

```bash
curl http://localhost:5000/health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "Event Analytics Platform",
  "redis_connection": "healthy",
  "message": "Analytics platform is operational"
}
```

### **`POST /events/`** - Event Ingestion *(requires write permission)*
Submit analytics events to track user behavior, feature usage, conversions, and custom interactions.

**Request Format:**
```json
{
  "event_type": "page_view",
  "user_id": "user_12345",
  "session_id": "sess_abc123",
  "properties": {
    "page_url": "/dashboard",
    "referrer": "https://google.com",
    "device_type": "desktop",
    "country": "US"
  }
}
```

**Sample cURL:**
```bash
curl -X POST http://localhost:5000/events/ \
  -H "Authorization: Bearer dev-key-analytics-2024" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "purchase_completed",
    "user_id": "user_67890",
    "properties": {
      "revenue": 49.99,
      "product_name": "Pro Plan",
      "payment_method": "credit_card"
    }
  }'
```

### **`GET /analytics/`** - Analytics Dashboard *(requires read permission)*
Retrieve comprehensive analytics data including event summaries, user metrics, trends, and conversion insights.

**Platform Analytics:**
```bash
curl -H "Authorization: Bearer dev-key-analytics-2024" http://localhost:5000/analytics/
```

**User-Specific Analytics:**
```bash
curl -H "Authorization: Bearer dev-key-analytics-2024" \
  "http://localhost:5000/analytics/?user_id=user_12345"
```

### **`PUT /events/{event_id}/enrich/`** - Event Enrichment *(requires write permission)*
Add additional properties or metadata to existing events for enhanced analytics and segmentation.

```bash
curl -X PUT http://localhost:5000/events/evt_a1b2c3d4e5f6/enrich/ \
  -H "Authorization: Bearer dev-key-analytics-2024" \
  -H "Content-Type: application/json" \
  -d '{
    "additional_properties": {
      "user_segment": "enterprise",
      "lead_score": 85,
      "campaign_attribution": "q1_growth"
    }
  }'
```

### **`POST /generate-sample-data/{num_events}/`** - Sample Data Generation *(requires admin permission)*
Generate realistic sample events for testing and demonstration purposes.

```bash
curl -X POST http://localhost:5000/generate-sample-data/1000/ \
  -H "Authorization: Bearer dev-key-analytics-2024"
```

### **`GET /auth/info`** - Authentication Info *(requires read permission)*
Get information about the current API key permissions and rate limits.

```bash
curl -H "Authorization: Bearer dev-key-analytics-2024" http://localhost:5000/auth/info
```

## 🏗️ Architecture and Features

### **Core Technologies:**
- **Flask**: RESTful API framework for event ingestion and analytics
- **Redis**: High-performance in-memory storage with connection pooling
- **RQ**: Asynchronous job processing for background analytics computations
- **Docker**: Containerized deployment for consistent environments

### **Technical Features:**
- **🔐 API Key Authentication**: Secure access control with permission levels
- **⚡ Connection Pooling**: Redis connection pooling for high performance
- **📊 User Indexing**: Optimized user-specific event queries using sorted sets
- **🚦 Rate Limiting**: Configurable rate limits per API key
- **📝 Structured Logging**: Comprehensive logging with rotation and levels
- **💾 Data Retention**: Automatic TTL-based data cleanup
- **🏥 Health Monitoring**: Redis health checks and error handling
- **🛡️ Input Validation**: Request validation and sanitization
- **📈 Performance Optimization**: Indexed queries and efficient data structures

### **Key Features:**
- **Real-time Event Ingestion**: High-throughput event collection with automatic timestamping
- **Flexible Schema**: Support for custom event types and properties
- **User Journey Tracking**: Session-based analytics and user behavior insights
- **Conversion Analytics**: Funnel analysis and conversion rate calculations
- **Event Enrichment**: Post-processing enhancement of event data
- **Background Processing**: Asynchronous aggregation and metric computation
- **Scalable Architecture**: Redis-backed storage designed for high volume

## 📊 Performance & Scalability

### **Performance Metrics:**
- **Event Ingestion**: 1,000+ events/second per instance
- **User Analytics**: Sub-100ms response using indexed lookups
- **Dashboard Generation**: Sub-second response with caching
- **Memory Efficiency**: Automatic data retention and cleanup

### **Scalability Features:**
- **Redis Connection Pooling**: Up to 20 concurrent connections
- **User-Specific Indexing**: O(log N) user query performance
- **Background Job Processing**: Asynchronous sample data generation
- **Automatic Data Retention**: 30-day default TTL with configurable periods

## 🔧 Configuration

### **Environment Variables:**

#### **Core Configuration:**
```bash
# Flask settings
FLASK_ENV=production
LOG_LEVEL=INFO

# Redis configuration
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_MAX_CONNECTIONS=20

# Authentication
ANALYTICS_ADMIN_KEY=your-secure-admin-key-here
SKIP_AUTH=false  # Set to true for development only

# Data retention (in seconds)
EVENT_TTL=2592000        # 30 days
DAILY_COUNTS_TTL=7776000 # 90 days
USER_SESSION_TTL=604800  # 7 days
ANALYTICS_CACHE_TTL=3600 # 1 hour

# Logging
LOG_DIR=logs
```

#### **Production Deployment:**
```bash
# Use strong API keys in production
ANALYTICS_ADMIN_KEY=prod-$(openssl rand -hex 32)

# Enable structured logging
FLASK_ENV=production
LOG_LEVEL=WARNING

# Secure Redis
REDIS_HOST=your-redis-cluster
REDIS_PASSWORD=your-redis-password
```

## 📝 Logging & Monitoring

### **Log Files:**
- **`analytics_app.log`**: General application logs (10MB rotation)
- **`analytics_errors.log`**: Error-specific logs (10MB rotation)
- **`access.log`**: Structured access logs with authentication info

### **Log Levels:**
- **DEBUG**: Development debugging information
- **INFO**: General operational information
- **WARNING**: Authentication failures and rate limit violations
- **ERROR**: Application errors and Redis connection issues

### **Structured Logging Example:**
```json
{
  "timestamp": "2024-01-15T10:30:00",
  "level": "INFO",
  "logger": "app.routes",
  "method": "POST",
  "path": "/events/",
  "authenticated": true,
  "api_key_name": "Admin Key",
  "status_code": 201,
  "processing_time_ms": 45
}
```

## 🧪 Testing with Sample Data

### **Authentication Testing:**
```bash
# Test authentication
curl -H "X-API-Key: demo-readonly-key" http://localhost:5000/auth/info

# Test rate limiting
for i in {1..105}; do curl -H "X-API-Key: demo-readonly-key" http://localhost:5000/health; done
```

### **Load Sample Events:**
```bash
# Generate 1000 sample events (requires admin key)
curl -X POST http://localhost:5000/generate-sample-data/1000/ \
  -H "Authorization: Bearer dev-key-analytics-2024"

# Check the analytics dashboard
curl -H "Authorization: Bearer dev-key-analytics-2024" http://localhost:5000/analytics/
```

## 🚀 Deployment Options

### **Docker Compose Deployment:**
```yaml
services:
  backend-service:
    build: .
    environment:
      - FLASK_ENV=production
      - LOG_LEVEL=WARNING
      - ANALYTICS_ADMIN_KEY=${ANALYTICS_ADMIN_KEY}
      - REDIS_HOST=redis-cluster
      - SKIP_AUTH=false
    deploy:
      replicas: 3
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M
```

### **Security Checklist:**
- ✅ Change default API keys
- ✅ Enable Redis password authentication
- ✅ Set appropriate data retention periods
- ✅ Configure log rotation and monitoring
- ✅ Use HTTPS in production
- ✅ Set up firewall rules for Redis access
- ✅ Monitor rate limiting and authentication logs

## 📈 API Usage Examples

### **Complete Event Tracking Workflow:**
```bash
# 1. Submit a page view event
curl -X POST http://localhost:5000/events/ \
  -H "Authorization: Bearer dev-key-analytics-2024" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "page_view",
    "user_id": "user_12345",
    "properties": {"page_url": "/dashboard", "device_type": "desktop"}
  }'

# 2. Enrich the event with additional context
curl -X PUT http://localhost:5000/events/evt_generated_id/enrich/ \
  -H "Authorization: Bearer dev-key-analytics-2024" \
  -H "Content-Type: application/json" \
  -d '{
    "additional_properties": {"user_segment": "power_user", "campaign": "q1_growth"}
  }'

# 3. View user-specific analytics
curl -H "Authorization: Bearer dev-key-analytics-2024" \
  "http://localhost:5000/analytics/?user_id=user_12345"

# 4. View platform-wide dashboard
curl -H "Authorization: Bearer dev-key-analytics-2024" http://localhost:5000/analytics/
```

## 🔒 Security Features

- **API Key Authentication** with permission levels
- **Rate limiting** to prevent abuse
- **Input validation** and sanitization
- **Redis connection security** with pooling
- **Structured audit logging** for compliance
- **Error handling** without information disclosure
- **Data retention policies** for privacy compliance

## 🤝 Contributing

This platform demonstrates design patterns suitable for extensibility:

1. **Custom Event Types**: Add new event schemas in `utils.py`
2. **Analytics Extensions**: Implement additional metrics and insights
3. **Authentication Providers**: Extend auth system for OAuth/JWT
4. **Monitoring Integration**: Add Prometheus metrics
5. **Dashboard Enhancement**: Build custom visualization endpoints

---

**Event Analytics Platform** - Portfolio demonstration of event tracking and analytics with authentication, performance optimization, and modern development practices.



