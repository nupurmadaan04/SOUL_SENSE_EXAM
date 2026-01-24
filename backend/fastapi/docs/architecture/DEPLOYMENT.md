# Deployment Configuration Guide

## Overview

This guide covers staging and production deployment configurations for Soul Sense Backend services, including environment setup, secret management, and rollback procedures.

## 🎯 Acceptance Criteria

✅ **Separate configs for staging and production** - Dedicated environment files and Docker Compose configurations  
✅ **Secrets not committed to repo** - Template files only, actual secrets in .gitignore  
✅ **Rollback-ready setup** - Automated rollback scripts with version tracking  

---

## 📁 File Structure

```
backend/fastapi/
├── .env.staging.template          # Staging environment template
├── .env.production.template       # Production environment template
├── .env.staging                   # Actual staging config (NOT in git)
├── .env.production                # Actual production config (NOT in git)
├── Dockerfile                     # Multi-stage production build
├── docker-compose.staging.yml     # Staging Docker Compose
├── docker-compose.production.yml  # Production Docker Compose
├── deploy-staging.sh              # Staging deployment script
├── deploy-production.sh           # Production deployment script
├── rollback-production.sh         # Production rollback script
├── backups/                       # Database backups (NOT in git)
├── logs/                          # Application logs (NOT in git)
└── nginx/                         # Nginx configuration
    ├── nginx.conf
    └── ssl/                       # SSL certificates (NOT in git)
```

---

## 🚀 Quick Start

### 1. Initial Setup

```bash
cd backend/fastapi

# Copy environment templates
cp .env.staging.template .env.staging
cp .env.production.template .env.production

# Edit and configure
nano .env.staging
nano .env.production
```

### 2. Configure Secrets

**Critical values to set:**

**Staging (`.env.staging`):**
```bash
SOULSENSE_JWT_SECRET_KEY=<GENERATE_RANDOM_SECRET>
SOULSENSE_DB_HOST=your-staging-db-host
SOULSENSE_DB_USER=your-db-user
SOULSENSE_DB_PASSWORD=<SECURE_PASSWORD>
SOULSENSE_SENTRY_DSN=<STAGING_SENTRY_DSN>
```

**Production (`.env.production`):**
```bash
SOULSENSE_JWT_SECRET_KEY=<GENERATE_STRONG_SECRET>
SOULSENSE_DB_HOST=your-production-db-host
SOULSENSE_DB_USER=your-db-user
SOULSENSE_DB_PASSWORD=<VERY_SECURE_PASSWORD>
SOULSENSE_SENTRY_DSN=<PRODUCTION_SENTRY_DSN>
REDIS_PASSWORD=<REDIS_PASSWORD>
```

**Generate secure secrets:**
```bash
# Generate JWT secret
python -c "import secrets; print(secrets.token_urlsafe(64))"

# Or using openssl
openssl rand -base64 64
```

### 3. Deploy to Staging

```bash
# Make scripts executable
chmod +x deploy-staging.sh
chmod +x deploy-production.sh
chmod +x rollback-production.sh

# Deploy to staging
./deploy-staging.sh
```

### 4. Deploy to Production

```bash
# Deploy with automatic version
./deploy-production.sh

# Or specify version
./deploy-production.sh v1.0.0
```

---

## 🔧 Environment Configurations

### Staging Environment

**Purpose:** Testing and QA before production

**Characteristics:**
- Debug mode enabled
- Swagger UI enabled
- Less restrictive rate limiting
- SQLite or PostgreSQL
- Detailed logging (DEBUG level)
- Allows CORS from localhost

**Services:**
- API (FastAPI)
- PostgreSQL database
- Redis (optional)

**Access:**
- API: http://localhost:8000
- Docs: http://localhost:8000/docs

### Production Environment

**Purpose:** Live user-facing deployment

**Characteristics:**
- Debug mode disabled
- Swagger UI disabled (security)
- Strict rate limiting
- PostgreSQL required
- INFO level logging
- Restricted CORS
- SSL/HTTPS enabled
- Resource limits
- Multiple replicas
- Health checks
- Nginx reverse proxy

**Services:**
- API (2 replicas with rolling updates)
- PostgreSQL with connection pooling
- Redis with authentication
- Nginx reverse proxy

**Access:**
- API: https://api.soulsense.example.com
- Web: https://soulsense.example.com

---

## 🔒 Secret Management

### Never Commit:
- ❌ `.env.staging`
- ❌ `.env.production`
- ❌ SSL certificates/keys
- ❌ Database credentials
- ❌ API keys
- ❌ Service account files

### Safe to Commit:
- ✅ `.env.*.template` files
- ✅ Docker Compose files
- ✅ Deployment scripts
- ✅ Documentation

### .gitignore Protection

The following patterns are excluded from git:

```gitignore
.env.staging
.env.production
.env.local
.rollback_info
backups/*.sql
backups/*.gz
logs/*
nginx/ssl/*.key
nginx/ssl/*.pem
nginx/ssl/*.crt
secrets/
*.secret
*.key
credentials.json
```

---

## 📊 Deployment Process

### Staging Deployment

```bash
./deploy-staging.sh [version]
```

**Process:**
1. ✅ Check `.env.staging` exists
2. 📁 Create backup and log directories
3. 💾 Backup existing database (if any)
4. 🔄 Pull latest code (if git repo)
5. 🏗️ Build Docker images
6. 🚀 Start services with docker-compose
7. ⏳ Wait for health checks (30 retries)
8. ✓ Verify deployment
9. 📋 Display status and logs

**Output:**
```
======================================
Soul Sense - Staging Deployment
Version: 20260122-143000
======================================
✓ Database backup created
✓ Docker images built
✓ Services started
✓ API is healthy!

Deployment Successful!
```

### Production Deployment

```bash
./deploy-production.sh [version]
```

**Process:**
1. ⚠️ Safety confirmation required ("yes")
2. ✅ Check `.env.production` exists
3. 💾 **Database backup** (compressed)
4. 📝 Save rollback information
5. 🔄 Pull latest code
6. 🏗️ Build new Docker image
7. 🚀 **Rolling update** (zero-downtime)
8. ⏳ Extended health checks (60 retries)
9. ❌ **Auto-rollback on failure**
10. ✓ Verify all endpoints
11. 📋 Log deployment details

**Output:**
```
======================================
Soul Sense - PRODUCTION Deployment
Version: 20260122-150000
======================================
WARNING: You are about to deploy to PRODUCTION!
Are you sure you want to continue? (yes/no): yes

✓ Database backup created and compressed
✓ Rollback info saved
✓ Docker images built
✓ Rolling update initiated
✓ API is healthy!
✓ Health endpoint OK

======================================
Deployment Successful!
======================================
Version: 20260122-150000
Previous Version: 20260121-120000
```

---

## 🔄 Rollback Procedures

### Automatic Rollback

Production deployment automatically rolls back if:
- Health checks fail after 60 retries
- API doesn't respond within timeout
- Critical errors during deployment

### Manual Rollback

```bash
./rollback-production.sh
```

**Rollback to specific version:**
```bash
./rollback-production.sh v1.0.0
```

**Process:**
1. ⚠️ Safety confirmation required
2. 📋 Load rollback information from `.rollback_info`
3. 🛑 Stop current deployment
4. 💾 Optional: Restore database from backup
5. 🔄 Deploy previous version
6. ⏳ Health checks
7. ✓ Verify rollback success
8. 📝 Update rollback logs

**Rollback Information File (`.rollback_info`):**
```bash
DEPLOYMENT_VERSION=20260122-150000
PREVIOUS_VERSION=20260121-120000
DEPLOYMENT_TIMESTAMP=2026-01-22T15:00:00Z
BACKUP_FILE=./backups/production_backup_20260122_150000.sql.gz
```

### Database Restore

```bash
# Restore from backup during rollback
gunzip -c backups/production_backup_20260122_150000.sql.gz | \
  docker exec -i soulsense-db-production \
  psql -U postgres soulsense_production
```

---

## 🏥 Health Checks

### Endpoint Health Check

All deployments verify:
```bash
GET /health
```

**Expected Response:**
```json
{
  "status": "ok"
}
```

### Docker Health Checks

**API Container:**
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

**PostgreSQL:**
```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U postgres"]
  interval: 10s
  timeout: 5s
  retries: 5
```

**Redis:**
```yaml
healthcheck:
  test: ["CMD", "redis-cli", "ping"]
  interval: 10s
  timeout: 5s
  retries: 5
```

---

## 📦 Docker Configuration

### Multi-Stage Build

**Dockerfile optimizations:**
- Two-stage build (builder + runtime)
- Minimal base image (python:3.11-slim)
- Non-root user (soulsense)
- Health checks included
- Optimized layer caching

### Resource Limits (Production)

**API Service:**
```yaml
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 2G
    reservations:
      cpus: '1'
      memory: 1G
  replicas: 2
```

**Database:**
```yaml
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 4G
```

### Rolling Updates (Production)

```yaml
deploy:
  update_config:
    parallelism: 1      # Update 1 container at a time
    delay: 10s          # Wait 10s between updates
    order: start-first  # Start new before stopping old
  rollback_config:
    parallelism: 1
    delay: 5s
```

---

## 🔍 Monitoring & Logging

### View Logs

**Staging:**
```bash
docker-compose -f docker-compose.staging.yml logs -f api
docker-compose -f docker-compose.staging.yml logs -f db
```

**Production:**
```bash
docker-compose -f docker-compose.production.yml logs -f api
docker-compose -f docker-compose.production.yml logs --tail=100 api
```

### Log Rotation (Production)

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

### Service Status

```bash
# Staging
docker-compose -f docker-compose.staging.yml ps

# Production
docker-compose -f docker-compose.production.yml ps
docker-compose -f docker-compose.production.yml top
```

---

## 🛡️ Security Best Practices

### Environment Secrets

1. **Never commit `.env.*` files to git**
2. **Use strong, unique secrets per environment**
3. **Rotate secrets regularly**
4. **Use secret management services (AWS Secrets Manager, HashiCorp Vault)**

### Database Security

1. **Use strong passwords**
2. **Restrict network access**
3. **Enable SSL for database connections**
4. **Regular backups**
5. **Encrypted backups for production**

### Production Hardening

1. **Disable debug mode** (`SOULSENSE_DEBUG=false`)
2. **Disable Swagger UI** (`SOULSENSE_ENABLE_SWAGGER_UI=false`)
3. **Restrict CORS** (specific domains only)
4. **Enable HTTPS/SSL**
5. **Use HSTS headers**
6. **Implement rate limiting**
7. **Run as non-root user**

---

## 🧪 Testing Deployments

### Pre-Deployment Checklist

- [ ] All tests passing
- [ ] Environment files configured
- [ ] Database migrations ready
- [ ] Backup procedures verified
- [ ] Rollback plan documented
- [ ] Team notified

### Post-Deployment Verification

```bash
# Test health endpoint
curl https://api.soulsense.example.com/health

# Test API endpoints
curl https://api.soulsense.example.com/api/v1/questions?limit=1

# Monitor logs
docker-compose -f docker-compose.production.yml logs -f --tail=50

# Check resource usage
docker stats

# Verify database connectivity
docker exec soulsense-db-production pg_isready
```

---

## 🚨 Troubleshooting

### Deployment Fails

**Check logs:**
```bash
docker-compose -f docker-compose.production.yml logs api
docker-compose -f docker-compose.production.yml logs db
```

**Check container status:**
```bash
docker-compose -f docker-compose.production.yml ps
docker inspect soulsense-api-production
```

**Restart services:**
```bash
docker-compose -f docker-compose.production.yml restart api
```

### Database Connection Issues

**Test connection:**
```bash
docker exec soulsense-db-production psql -U postgres -c "SELECT 1"
```

**Check environment variables:**
```bash
docker exec soulsense-api-production env | grep SOULSENSE_DB
```

### Rollback Issues

**Manual rollback:**
```bash
# Stop current version
docker-compose -f docker-compose.production.yml down

# Deploy specific version
DEPLOYMENT_VERSION=20260121-120000 \
docker-compose -f docker-compose.production.yml up -d
```

---

## 📋 Maintenance Tasks

### Database Backups

**Manual backup:**
```bash
docker exec soulsense-db-production \
  pg_dump -U postgres soulsense_production \
  > backups/manual_backup_$(date +%Y%m%d).sql
```

**Automated backups** (add to cron):
```bash
0 2 * * * cd /path/to/backend/fastapi && docker exec soulsense-db-production pg_dump -U postgres soulsense_production | gzip > backups/auto_backup_$(date +\%Y\%m\%d).sql.gz
```

### Log Cleanup

```bash
# Clean old logs (keep last 7 days)
find logs/ -name "*.log" -mtime +7 -delete
find backups/ -name "*.sql.gz" -mtime +30 -delete
```

### Update Dependencies

```bash
# Update Python packages
pip install --upgrade -r requirements.txt

# Rebuild images
docker-compose -f docker-compose.production.yml build --no-cache
```

---

## 🎓 Best Practices

### Version Naming

Use semantic versioning or timestamp-based:
```bash
# Semantic versioning
./deploy-production.sh v1.2.3

# Timestamp-based (default)
./deploy-production.sh 20260122-150000
```

### Deployment Schedule

**Staging:** Anytime during business hours  
**Production:** Off-peak hours (e.g., 2-4 AM local time)

### Communication

1. Notify team before production deployment
2. Post-deployment verification by 2+ team members
3. Monitor for 1 hour after production deployment
4. Document any issues in deployment log

### Database Migrations

```bash
# Run migrations before deploying
docker exec soulsense-api-production alembic upgrade head

# Or include in deployment script
```

---

## 📞 Support & Escalation

**Deployment Issues:**
1. Check logs and troubleshooting guide
2. Attempt rollback if critical
3. Contact DevOps team
4. Document incident

**Emergency Rollback:**
```bash
./rollback-production.sh
```

---

## ✅ Summary

✅ **Separate Configurations** - Distinct `.env` files and Docker Compose configs for staging/production  
✅ **Secret Management** - Templates in git, actual secrets excluded via .gitignore  
✅ **Rollback Ready** - Automated rollback with version tracking and database restoration  

**Related Files:**
- `.env.staging.template` - Staging environment template
- `.env.production.template` - Production environment template
- `docker-compose.staging.yml` - Staging services
- `docker-compose.production.yml` - Production services
- `deploy-production.sh` - Production deployment with rollback
- `rollback-production.sh` - Rollback automation

---

**Issue:** #398  
**Status:** ✅ Complete  
**Version:** 1.0.0
