# Configuration Examples for Different Environments

This document provides example configuration files for different deployment environments (development, testing, staging, production) for the SoulSense application.

## Overview

The SoulSense application supports multiple configuration methods:

1. **Environment Variables** (`.env` files) - Primary configuration method for the FastAPI backend
2. **JSON Configuration** (`config.json`) - Used by the main application for UI and feature settings
3. **Docker Compose** (`docker-compose.yml`) - Container orchestration configuration

## Environment Variables (.env files)

### Development Environment (.env.development)

```bash
# Application Environment
APP_ENV=development
DEBUG=true

# Server Configuration
HOST=127.0.0.1
PORT=8000

# Database Configuration (SQLite for development)
DATABASE_TYPE=sqlite
DATABASE_URL=sqlite:///./data/soulsense.db

# JWT Configuration (Development keys - NOT secure for production)
JWT_SECRET_KEY=dev_jwt_secret_key_for_development_only_not_secure_change_this_in_production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# CORS Configuration
ALLOWED_ORIGINS=["http://localhost:3000", "http://localhost:8000", "http://127.0.0.1:8000", "http://localhost:5173"]

# Logging
LOG_LEVEL=DEBUG

# Feature Flags
ENABLE_JOURNAL=true
ENABLE_ANALYTICS=true

# UI Settings (via config.json, but can be overridden)
SOULSENSE_THEME=light
SOULSENSE_DEBUG=true
SOULSENSE_LOG_LEVEL=DEBUG
```

### Testing Environment (.env.testing)

```bash
# Application Environment
APP_ENV=development
DEBUG=true

# Server Configuration
HOST=127.0.0.1
PORT=8001

# Database Configuration (Separate test database)
DATABASE_TYPE=sqlite
DATABASE_URL=sqlite:///./data/soulsense_test.db

# JWT Configuration (Test keys)
JWT_SECRET_KEY=test_jwt_secret_key_for_testing_only_not_secure_change_this_in_production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# CORS Configuration (Allow test domains)
ALLOWED_ORIGINS=["http://localhost:3000", "http://localhost:8001", "http://127.0.0.1:8001"]

# Logging (More verbose for testing)
LOG_LEVEL=DEBUG

# Feature Flags (All enabled for testing)
ENABLE_JOURNAL=true
ENABLE_ANALYTICS=true

# Test-specific settings
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
TEST_FULL_IMPORTS=false
```

### Staging Environment (.env.staging)

```bash
# Application Environment
APP_ENV=staging
DEBUG=false

# Server Configuration
HOST=0.0.0.0
PORT=8000

# Database Configuration (PostgreSQL)
DATABASE_TYPE=postgresql
DATABASE_HOST=staging-db.example.com
DATABASE_PORT=5432
DATABASE_NAME=soulsense_staging
DATABASE_USER=soulsense_staging
DATABASE_PASSWORD=your_secure_staging_password_here

# JWT Configuration (Secure keys from secrets management)
JWT_SECRET_KEY=your_secure_staging_jwt_secret_key_here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=12

# CORS Configuration (Staging domains)
ALLOWED_ORIGINS=["https://staging.soulsense.app", "https://api-staging.soulsense.app"]

# Logging
LOG_LEVEL=INFO

# Feature Flags
ENABLE_JOURNAL=true
ENABLE_ANALYTICS=true

# Redis Configuration (for caching)
REDIS_HOST=staging-redis.example.com
REDIS_PORT=6379

# Monitoring and Observability
SENTRY_DSN=https://your-sentry-dsn-for-staging@sentry.io/project-id
METRICS_ENABLED=true
```

### Production Environment (.env.production)

```bash
# Application Environment
APP_ENV=production
DEBUG=false

# Server Configuration
HOST=0.0.0.0
PORT=8000

# Database Configuration (PostgreSQL with connection pooling)
DATABASE_TYPE=postgresql
DATABASE_HOST=prod-db.example.com
DATABASE_PORT=5432
DATABASE_NAME=soulsense_prod
DATABASE_USER=soulsense_prod
DATABASE_PASSWORD=your_secure_production_password_here

# JWT Configuration (Secure keys from secrets management)
JWT_SECRET_KEY=your_secure_production_jwt_secret_key_here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=8

# CORS Configuration (Production domains only)
ALLOWED_ORIGINS=["https://soulsense.app", "https://api.soulsense.app"]

# Logging
LOG_LEVEL=WARNING

# Feature Flags (Production-safe settings)
ENABLE_JOURNAL=true
ENABLE_ANALYTICS=true

# Redis Configuration (Clustered for production)
REDIS_HOST=prod-redis-cluster.example.com
REDIS_PORT=6379

# Security Headers
SECURE_HEADERS=true
HSTS_MAX_AGE=31536000

# Monitoring and Observability
SENTRY_DSN=https://your-sentry-dsn-for-production@sentry.io/project-id
METRICS_ENABLED=true
HEALTH_CHECK_ENABLED=true

# Rate Limiting
RATE_LIMIT_REQUESTS_PER_MINUTE=100
RATE_LIMIT_BURST_SIZE=20

# SSL/TLS
SSL_CERT_PATH=/path/to/ssl/cert.pem
SSL_KEY_PATH=/path/to/ssl/private.key
```

## JSON Configuration (config.json)

### Development Configuration (config.development.json)

```json
{
  "database": {
    "filename": "soulsense.db",
    "path": "data"
  },
  "ui": {
    "theme": "light",
    "window_size": "800x600"
  },
  "features": {
    "enable_journal": true,
    "enable_analytics": true
  },
  "exam": {
    "num_questions": 5
  },
  "experimental": {
    "ai_journal_suggestions": true,
    "advanced_analytics": true,
    "beta_ui_components": true,
    "ml_emotion_detection": true,
    "data_export_v2": true
  }
}
```

### Testing Configuration (config.testing.json)

```json
{
  "database": {
    "filename": "soulsense_test.db",
    "path": "data"
  },
  "ui": {
    "theme": "light",
    "window_size": "800x600"
  },
  "features": {
    "enable_journal": true,
    "enable_analytics": true
  },
  "exam": {
    "num_questions": 3
  },
  "experimental": {
    "ai_journal_suggestions": false,
    "advanced_analytics": false,
    "beta_ui_components": false,
    "ml_emotion_detection": false,
    "data_export_v2": false
  }
}
```

### Staging Configuration (config.staging.json)

```json
{
  "database": {
    "filename": "soulsense_staging.db",
    "path": "db"
  },
  "ui": {
    "theme": "light",
    "window_size": "1024x768"
  },
  "features": {
    "enable_journal": true,
    "enable_analytics": true
  },
  "exam": {
    "num_questions": 10
  },
  "experimental": {
    "ai_journal_suggestions": true,
    "advanced_analytics": true,
    "beta_ui_components": false,
    "ml_emotion_detection": true,
    "data_export_v2": true
  }
}
```

### Production Configuration (config.production.json)

```json
{
  "database": {
    "filename": "soulsense_prod.db",
    "path": "db"
  },
  "ui": {
    "theme": "light",
    "window_size": "1280x720"
  },
  "features": {
    "enable_journal": true,
    "enable_analytics": true
  },
  "exam": {
    "num_questions": 10
  },
  "experimental": {
    "ai_journal_suggestions": false,
    "advanced_analytics": false,
    "beta_ui_components": false,
    "ml_emotion_detection": false,
    "data_export_v2": false
  }
}
```

## Docker Compose Configuration

### Development (docker-compose.dev.yml)

```yaml
version: "3.8"

services:
  api:
    build:
      context: ./backend/fastapi
      dockerfile: Dockerfile.dev
    env_file:
      - .env.development
    environment:
      - APP_ENV=development
      - DEBUG=true
    volumes:
      - ./backend/fastapi:/app
      - ./data:/data
    ports:
      - "8000:8000"
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=soulsense_dev
      - POSTGRES_PASSWORD=dev_password
      - POSTGRES_DB=soulsense_dev
    volumes:
      - dev_db_data:/var/lib/postgresql/data
    ports:
      - "5433:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6380:6379"
```

### Production (docker-compose.prod.yml)

```yaml
version: "3.8"

services:
  api:
    image: soulsense/api:latest
    env_file:
      - .env.production
    environment:
      - APP_ENV=production
      - DEBUG=false
    secrets:
      - jwt_secret
      - db_password
    volumes:
      - ./ssl:/ssl:ro
    ports:
      - "443:8000"
    depends_on:
      - db
      - redis
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER_FILE=/run/secrets/db_user
      - POSTGRES_PASSWORD_FILE=/run/secrets/db_password
      - POSTGRES_DB=soulsense_prod
    secrets:
      - db_user
      - db_password
    volumes:
      - prod_db_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U soulsense_prod"]
      interval: 30s
      timeout: 10s
      retries: 3

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/ssl:ro
    depends_on:
      - api

secrets:
  jwt_secret:
    file: ./secrets/jwt_secret.txt
  db_user:
    file: ./secrets/db_user.txt
  db_password:
    file: ./secrets/db_password.txt

volumes:
  prod_db_data:
  redis_data:
```

## Environment-Specific Differences

### Database Configuration

| Environment | Database Type | Purpose | Security Level |
|-------------|---------------|---------|----------------|
| Development | SQLite | Local development | Low |
| Testing | SQLite | Isolated test runs | Low |
| Staging | PostgreSQL | Pre-production testing | Medium |
| Production | PostgreSQL | Live application | High |

### Security Settings

| Environment | JWT Expiry | CORS Policy | Debug Mode | Logging Level |
|-------------|-------------|-------------|------------|---------------|
| Development | 24 hours | Permissive | Enabled | DEBUG |
| Testing | 24 hours | Test domains | Enabled | DEBUG |
| Staging | 12 hours | Staging domains | Disabled | INFO |
| Production | 8 hours | Production domains | Disabled | WARNING |

### Feature Flags

| Environment | AI Features | Experimental UI | ML Detection | Advanced Analytics |
|-------------|-------------|-----------------|--------------|-------------------|
| Development | Enabled | Enabled | Enabled | Enabled |
| Testing | Disabled | Disabled | Disabled | Disabled |
| Staging | Partial | Disabled | Enabled | Enabled |
| Production | Disabled | Disabled | Disabled | Disabled |

### Performance Settings

| Environment | Caching | Connection Pooling | Rate Limiting | Monitoring |
|-------------|---------|-------------------|---------------|------------|
| Development | Disabled | Basic | Disabled | Basic |
| Testing | Disabled | Basic | Disabled | Basic |
| Staging | Redis | Enabled | Basic | Full |
| Production | Redis Cluster | Advanced | Strict | Enterprise |

## Setup Instructions

### Development Setup

1. Copy the development configuration:
   ```bash
   cp .env.development .env
   cp config.development.json config.json
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the application:
   ```bash
   python app.py
   ```

### Testing Setup

1. Copy the testing configuration:
   ```bash
   cp .env.testing .env
   cp config.testing.json config.json
   ```

2. Run tests:
   ```bash
   pytest
   ```

### Staging/Production Setup

1. Copy the appropriate configuration:
   ```bash
   cp .env.staging .env  # or .env.production
   cp config.staging.json config.json  # or config.production.json
   ```

2. Set secure environment variables:
   ```bash
   export JWT_SECRET_KEY="your-secure-key-here"
   export DATABASE_PASSWORD="your-secure-db-password"
   ```

3. Use Docker Compose for deployment:
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

## Security Considerations

### Environment Variables
- Never commit `.env` files to version control
- Use different secrets for each environment
- Rotate JWT secrets regularly
- Store production secrets in secure vaults (AWS Secrets Manager, Azure Key Vault, etc.)

### Database Security
- Use strong passwords for production databases
- Enable SSL/TLS for database connections
- Implement connection pooling
- Regular database backups and monitoring

### Network Security
- Restrict CORS origins to trusted domains
- Use HTTPS in production
- Implement rate limiting
- Enable security headers (HSTS, CSP, etc.)

## Monitoring and Observability

### Development
- Basic logging to console
- No external monitoring

### Testing
- Test result reporting
- Basic error logging

### Staging
- Application metrics collection
- Error tracking (Sentry)
- Performance monitoring

### Production
- Comprehensive monitoring stack
- Alerting and incident response
- Log aggregation and analysis
- Performance optimization

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Check DATABASE_URL format
   - Verify database server is running
   - Check network connectivity and firewall rules

2. **JWT Authentication Issues**
   - Verify JWT_SECRET_KEY is set and matches across services
   - Check JWT_EXPIRATION_HOURS setting
   - Validate token format and claims

3. **CORS Errors**
   - Check ALLOWED_ORIGINS configuration
   - Verify request origin matches allowed origins
   - Check for HTTPS vs HTTP mismatches

4. **Performance Issues**
   - Enable Redis caching in staging/production
   - Check database query performance
   - Monitor memory and CPU usage

### Environment Validation

The application includes environment validation on startup. Check the logs for validation errors:

```bash
# Development - should show all validations passed
✅ Environment validation successful!

# Production - will fail if required variables are missing
❌ Environment validation failed!
Missing required variables: DATABASE_HOST, DATABASE_PASSWORD
```

## Migration Between Environments

When promoting from staging to production:

1. Update environment variables
2. Migrate database schema if needed
3. Update DNS and SSL certificates
4. Configure monitoring and alerting
5. Update feature flags as needed
6. Perform load testing
7. Update documentation and runbooks</content>
<parameter name="filePath">c:\Users\Gupta\Downloads\SOUL_SENSE_EXAM\docs\architecture\config_examples.md